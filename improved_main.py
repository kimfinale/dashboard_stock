"""
Improved main() function for the trading bot.

Key improvements:
1. Prevents duplicate Kiwoom logins
2. Updates Account.performance_log with current prices every iteration
3. Portfolio generation once per iteration (not per transaction)
4. GitHub sync once per iteration (reduces commits)
5. Better error handling and logging

INSTALLATION:
Replace the main() function in your existing file with this version.
"""

import sys
import time
import json
import traceback
import os
from datetime import datetime, time as dtime
from PyQt5.QtWidgets import QApplication
from kiwoom_api import Kiwoom
from account_manager import Account, save_accounts, load_accounts
from strategy_executor import StrategyExecutor
from github_sync import GitHubSync
from generate_portfolio_json import fetch_and_generate_portfolio


def check_market_open():
    """
    Check if KOSPI/KOSDAQ market is open (09:00 - 15:30 KST).
    Returns True if open, False otherwise.
    Also returns False on weekends.
    """
    now = datetime.now()

    # Weekday check (0=Mon, 6=Sun)
    if now.weekday() >= 5:
        return False

    current_time = now.time()
    start_time = dtime(9, 0)
    end_time = dtime(15, 30)

    return start_time <= current_time <= end_time


def initialize_accounts(config):
    """
    Initialize accounts from state file or create new ones from config.
    Returns a dictionary of {account_id: Account object}.
    """
    if isinstance(config, str):
        with open(config, 'r', encoding='utf-8') as f:
            config = json.load(f)

    state_file = "trade_state.json"
    loaded_accounts = load_accounts(state_file)

    accounts_map = {}

    if loaded_accounts:
        print(f"Loaded {len(loaded_accounts)} accounts from {state_file}")
        for acc in loaded_accounts:
            accounts_map[acc.account_id] = acc

    # Merge with config (handles new stocks/accounts added to config.json)
    total_capital = config.get("total_capital", 0)
    newly_created = 0

    if "strategies" in config:
        for strategy in config["strategies"]:
            s_id = strategy["id"]
            alloc_percent = strategy.get("total_allocation_percent", 0)
            strategy_capital = total_capital * alloc_percent

            sub_accounts = strategy.get("accounts", [])
            ratios = [acc["ratio"] for acc in sub_accounts]

            for i, acc_cfg in enumerate(sub_accounts):
                acc_id = f"{s_id}_{acc_cfg['suffix']}"

                if acc_id not in accounts_map:
                    allocated_capital = int(strategy_capital * ratios[i])
                    cfg = acc_cfg.copy()
                    cfg["account_id"] = acc_id
                    cfg["strategy_id"] = s_id
                    cfg["stock_code"] = strategy["stock_code"]

                    new_acc = Account(
                        account_id=acc_id,
                        principal=allocated_capital,
                        stock_code=strategy["stock_code"],
                        strategy_config=cfg
                    )
                    accounts_map[acc_id] = new_acc
                    newly_created += 1
                    print(f"  Created New Account {acc_id}: Principal {new_acc.principal:,} KRW")

    if newly_created > 0 or not loaded_accounts:
        save_accounts(list(accounts_map.values()), state_file)
        if newly_created > 0:
            print(f"Added {newly_created} new accounts from config to state.")

    return accounts_map


def update_account_snapshots(kiwoom, accounts_map):
    """
    Update all accounts with current price snapshots.
    This populates the performance_log for historical data.

    Args:
        kiwoom: Kiwoom API instance
        accounts_map: Dictionary of {account_id: Account}

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Collect all unique stock codes from holdings
        all_codes = set()
        for acc in accounts_map.values():
            all_codes.update(acc.holdings.keys())

        if not all_codes:
            # No holdings, just record snapshots with current balance
            for acc in accounts_map.values():
                acc.update_snapshot({})
            return True

        # Fetch current prices for all stocks
        current_prices = {}
        for code in all_codes:
            try:
                price = kiwoom.get_current_price(code)
                if price and price > 0:
                    current_prices[code] = price
                else:
                    print(f"  Warning: Invalid price for {code}: {price}")
            except Exception as e:
                print(f"  Warning: Failed to get price for {code}: {e}")

        # Update each account's snapshot
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for acc in accounts_map.values():
            try:
                acc.update_snapshot(current_prices, timestamp=timestamp)
            except Exception as e:
                print(f"  Warning: Failed to update snapshot for {acc.account_id}: {e}")

        return True

    except Exception as e:
        print(f"Error updating account snapshots: {e}")
        traceback.print_exc()
        return False


def main():
    """
    Real-time trading bot with integrated dashboard updates.

    Improvements:
    - Single Kiwoom instance (prevents duplicate login errors)
    - Performance log updates every iteration (builds historical data)
    - Portfolio generation once per iteration (efficient)
    - GitHub sync once per iteration (cleaner commit history)
    """
    # Load configuration
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Initialize Qt Application (required for Kiwoom API)
    app = QApplication(sys.argv)

    # Connect to Kiwoom API (SINGLE CONNECTION)
    print("=" * 60)
    print("Real-Time Trading Bot - Starting")
    print("=" * 60)
    kiwoom = Kiwoom()

    print("\nConnecting to Kiwoom API...")

    try:
        kiwoom.comm_connect()
        print("✅ Connected to Kiwoom API")
    except Exception as e:
        print(f"\n❌ Connection Failed: {e}")
        print("Please close any other applications using Kiwoom API and try again.")
        sys.exit(1)

    # Get account information
    accounts_list = kiwoom.get_login_info("ACCNO")
    if not accounts_list:
        print("ERROR: No accounts found. Exiting.")
        sys.exit(1)

    print(f"\nAvailable accounts: {accounts_list}")

    # Select the account to use
    real_account_no = config.get("real_account_id", accounts_list[0])
    print(f"Using Real Account: {real_account_no}")

    # Initialize Virtual Accounts
    print("\n" + "=" * 60)
    print("Initializing Accounts")
    print("=" * 60)
    accounts_map = initialize_accounts(config)

    # Initialize GitHub Sync
    github_sync = GitHubSync()

    # Simplified transaction callback (just logs, no sync)
    def on_transaction_complete(action, account_alias, code, price, qty):
        """
        Called after each successful transaction.
        Logs the transaction - full update happens at iteration end.
        """
        print(f"\n{'─'*60}")
        print(f"✅ Transaction: {action} {qty} {code} @ {price:,} KRW ({account_alias})")
        print(f"{'─'*60}\n")

        # Immediate lightweight state save
        try:
            save_accounts(list(accounts_map.values()), "trade_state.json")
        except Exception as e:
            print(f"Warning: Failed to save state after transaction: {e}")

    # Display configuration
    print("\n" + "=" * 60)
    print("Configuration")
    print("=" * 60)
    print(f"Total Capital  : {config.get('total_capital', 0):,} KRW")
    print(f"Real Account   : {config.get('real_account_id', 'N/A')}")
    print(f"Active Accounts: {len(accounts_map)} virtual accounts")
    print(f"Dry Run Mode   : {config.get('dry_run', False)}")
    print("-" * 60)

    # Initialize StrategyExecutor (receives the Kiwoom instance)
    executor = StrategyExecutor(
        kiwoom,
        accounts_map,
        config,
        on_transaction_complete=on_transaction_complete
    )

    # Display current account status
    print("\n" + "=" * 60)
    print("Current Account Status")
    print("=" * 60)
    try:
        account_data = kiwoom.get_account_evaluation(real_account_no)
        if account_data:
            summary = account_data['summary']
            print(f"Total Assets: {summary['estimated_assets']:,} KRW")
            print(f"Total Buy Amount: {summary['total_buy']:,} KRW")
            print(f"Total Evaluation: {summary['total_eval']:,} KRW")
            print(f"Total P/L: {summary['total_profit_loss']:,} KRW ({summary['total_rate']}%)")
            print(f"\nCurrent Holdings: {len(account_data['holdings'])} positions")
            for h in account_data['holdings']:
                print(f"  {h['name']}({h['code']}): {h['qty']} shares @ {h['current_price']:,} KRW")
    except Exception as e:
        print(f"Warning: Could not fetch initial account status: {e}")

    # Confirm before starting
    if not config.get('dry_run', False):
        print("\n" + "!" * 60)
        print("WARNING: DRY RUN MODE IS OFF - REAL TRADES WILL BE EXECUTED")
        print("!" * 60)
        response = input("\nType 'START' to begin real trading: ")
        if response.strip().upper() != 'START':
            print("Aborted by user.")
            sys.exit(0)

    # Main execution loop
    print("\n" + "=" * 60)
    print("Starting Trading Loop")
    print("=" * 60)
    print("Press Ctrl+C to stop safely\n")

    # Get check interval from config
    check_interval = 5
    if "strategies" in config and config["strategies"]:
        check_interval = config["strategies"][0].get("check_interval_minutes", 5)

    interval_seconds = check_interval * 60
    iteration = 0

    # Initialize config monitoring
    config_path = 'config.json'
    try:
        last_mtime = os.path.getmtime(config_path)
    except OSError:
        last_mtime = 0

    try:
        while True:
            # Check Market Hours
            if not check_market_open() and not config.get("ignore_market_hours", False):
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Market Closed (09:00-15:30). Waiting...", end='\r')
                time.sleep(60)
                continue

            iteration += 1
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            print(f"\n{'='*60}")
            print(f"Iteration #{iteration} - {current_time}")
            print(f"{'='*60}")

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 1. EXECUTE STRATEGY (may trigger trades)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            try:
                print("\n📊 Executing strategy...")
                executor.execute_step()
                print("✅ Strategy execution complete")
            except Exception as e:
                print(f"⚠️  ERROR during strategy execution: {e}")
                traceback.print_exc()
                print("Continuing to next iteration...")

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 2. UPDATE PERFORMANCE SNAPSHOTS (builds historical data)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            print("\n📈 Updating account snapshots...")
            if update_account_snapshots(kiwoom, accounts_map):
                print("✅ Snapshots updated")
            else:
                print("⚠️  Snapshot update had errors")

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 3. SAVE ACCOUNT STATE
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            try:
                save_accounts(list(accounts_map.values()), "trade_state.json")
                print("✅ Account state saved")
            except Exception as e:
                print(f"⚠️  Failed to save state: {e}")

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 4. GENERATE PORTFOLIO.JSON (once per iteration)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            print("\n📄 Generating portfolio.json...")
            try:
                if fetch_and_generate_portfolio(kiwoom):
                    print("✅ portfolio.json generated")
                else:
                    print("⚠️  portfolio.json generation failed")
            except Exception as e:
                print(f"⚠️  Portfolio generation error: {e}")
                traceback.print_exc()

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 5. SYNC TO GITHUB (once per iteration)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            print("\n🔄 Syncing to GitHub...")
            try:
                commit_msg = f"Auto-update: {current_time} (Iteration #{iteration})"
                if github_sync.sync_portfolio(commit_message=commit_msg):
                    print("✅ Synced to GitHub")
                else:
                    print("⚠️  GitHub sync failed (check git status manually)")
            except Exception as e:
                print(f"⚠️  GitHub sync error: {e}")

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 6. DISPLAY SUMMARY
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            print(f"\n{'─'*60}")
            print(f"Virtual Account Summary:")
            print(f"{'─'*60}")

            for acc_id, acc in accounts_map.items():
                holdings_count = len(acc.holdings)
                if holdings_count > 0:
                    total_invested = sum([h['total_cost'] for h in acc.holdings.values()])
                    print(f"  {acc_id}:")
                    print(f"    Holdings: {holdings_count} positions")
                    print(f"    Invested: {total_invested:,.0f} KRW")
                    print(f"    Cash:     {acc.balance:,.0f} KRW")
                else:
                    print(f"  {acc_id}: No positions, Cash: {acc.balance:,.0f} KRW")

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 7. WAIT FOR NEXT ITERATION (with config monitoring)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            print(f"\n⏳ Waiting {check_interval} minutes until next check...")
            next_check_time = time.time() + interval_seconds
            next_check_str = datetime.fromtimestamp(next_check_time).strftime('%Y-%m-%d %H:%M:%S')
            print(f"   Next check at: {next_check_str}")

            # Wait with config monitoring
            while time.time() < next_check_time:
                try:
                    current_mtime = os.path.getmtime(config_path)
                    if current_mtime > last_mtime:
                        print(f"\n🔄 Configuration file changed! Reloading...")
                        try:
                            time.sleep(1)  # Wait for write to complete
                            with open(config_path, 'r', encoding='utf-8') as f:
                                new_config = json.load(f)

                            config = new_config
                            last_mtime = current_mtime

                            # Update executor config
                            executor.update_config(config)

                            # Update check interval if changed
                            if "strategies" in config and config["strategies"]:
                                new_interval = config["strategies"][0].get("check_interval_minutes", 5)
                                if new_interval != check_interval:
                                    print(f"   Check interval updated: {check_interval} → {new_interval} minutes")
                                    check_interval = new_interval
                                    interval_seconds = check_interval * 60

                            print("✅ Configuration reloaded successfully")

                        except Exception as e:
                            print(f"❌ Failed to reload configuration: {e}")
                except OSError:
                    pass

                time.sleep(1)  # Check every second

    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("Trading Bot Stopped by User")
        print("=" * 60)
        print(f"Total iterations completed: {iteration}")
        print("\n📊 Final State Summary:")
        print("─" * 60)

        for acc_id, acc in accounts_map.items():
            holdings_count = len(acc.holdings)
            snapshots_count = len(acc.performance_log)
            print(f"{acc_id}:")
            print(f"  Holdings: {holdings_count} positions")
            print(f"  Balance:  {acc.balance:,.0f} KRW")
            print(f"  Snapshots: {snapshots_count} recorded")

        print("\n💾 Saving final state...")
        save_accounts(list(accounts_map.values()), "trade_state.json")
        print("✅ State saved to trade_state.json")

        print("\n📄 Generating final portfolio.json...")
        try:
            if fetch_and_generate_portfolio(kiwoom):
                print("✅ Final portfolio.json generated")
        except Exception as e:
            print(f"⚠️  Final portfolio generation failed: {e}")

        print("\n🔄 Final GitHub sync...")
        try:
            if github_sync.sync_portfolio(commit_message=f"Final update: Bot stopped at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"):
                print("✅ Final sync to GitHub complete")
        except Exception as e:
            print(f"⚠️  Final GitHub sync failed: {e}")

        print("\n👋 Goodbye!")


if __name__ == "__main__":
    main()
