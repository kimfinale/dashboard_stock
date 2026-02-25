import sys
import json
import time
import datetime
import os
from PyQt5.QtWidgets import QApplication
from kiwoom_api import Kiwoom

# Default Portfolio Structure
DEFAULT_PORTFOLIO = {
    "summary": {
        "total_value": 0,
        "daily_pnl": 0,
        "daily_return": 0.0,
        "total_pnl": 0,
        "total_return": 0.0,
        "cash": 0,
        "cash_percent": 0.0
    },
    "history": [],
    "holdings": [],
    "accounts": []
}

OUTPUT_DIR = "outputs"
PORTFOLIO_FILE = os.path.join(OUTPUT_DIR, "portfolio.json")
MAX_HISTORY_DAYS = 60

def load_portfolio(filepath=PORTFOLIO_FILE):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading existing portfolio: {e}")
    return DEFAULT_PORTFOLIO

def fetch_and_generate_portfolio(kiwoom):
    """
    Fetches data using an existing Kiwoom instance and generates portfolio.json.
    """
    # Ensure output directory exists
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created directory: {OUTPUT_DIR}")

    print("Fetching account info...")
    accounts_list = kiwoom.get_login_info("ACCNO")
    if not accounts_list:
        print("No accounts found.")
        return False

    # Load Config for Sector Map & Virtual Accounts
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    print(f"Loading config from: {config_path}")
    sector_map = {}
    config = {}

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Build Sector Map
            if "strategies" in config:
                for strategy in config["strategies"]:
                    if "stock_code" in strategy and "sector" in strategy:
                        sector_map[strategy["stock_code"]] = strategy["sector"]
        except Exception as e:
            print(f"Error loading config: {e}")

    # Data Aggregators
    total_value = 0
    total_cash_all = 0
    total_equity_all = 0
    total_pnl_all = 0 # Total Inception PnL
    daily_pnl_all = 0

    holdings_list = []
    accounts_data = []

    # Iterate accounts
    for acc in accounts_list:
        if not acc: continue
        if acc == '7032756831': continue # Skip unused account
        print(f"Processing Account: {acc}")

        # 1. Get Cash (Deposit)
        # opw00001
        kiwoom.get_deposit(acc)
        cash = kiwoom.tr_data
        if cash is None: cash = 0

        # 2. Get Evaluation & Holdings
        # opw00018
        data = kiwoom.get_account_evaluation(acc)
        if not data or not isinstance(data, dict):
            print(f"Failed to get evaluation for {acc} (Data: {data})")
            # Add partial data if possible or skip
            accounts_data.append({
                "name": f"Account {acc}",
                "total_value": cash,
                "cash": cash,
                "equity": 0
            })
            total_value += cash
            total_cash_all += cash
            continue

        summary = data['summary']
        acc_holdings = data['holdings']

        # Extract Summary Data
        equity = summary['total_eval']
        acc_total_value = summary['estimated_assets']

        acc_equity = equity
        acc_cash = cash
        acc_total_val = summary['estimated_assets']

        # Update Global Totals
        total_value += acc_total_val
        total_cash_all += acc_cash
        total_equity_all += acc_equity
        total_pnl_all += summary['total_profit_loss']
        daily_pnl_all += summary.get('daily_pnl', 0)

        accounts_data.append({
            "name": f"Account {acc}",
            "total_value": acc_total_val,
            "cash": acc_cash,
            "equity": acc_equity
        })

        # Process Holdings
        for h in acc_holdings:
            code = h['code']
            sector = sector_map.get(code, "Unknown")

            holding_entry = {
                "name": h['name'],
                "symbol": code,
                "sector": sector,
                "quantity": h['qty'],
                "avg_price": h['buy_price'],
                "current_price": h['current_price'],
                "value": h['current_price'] * h['qty'],
                "pnl": h['eval_profit'],
                "pnl_percent": h['yield_rate'],
                "account": f"Account {acc}"
            }
            holdings_list.append(holding_entry)

        time.sleep(0.3)

    # Calculate Global Summaries
    if total_value > 0:
        cash_percent = round((total_cash_all / total_value) * 100, 2)
        total_rate = round((total_pnl_all / (total_value - total_pnl_all)) * 100, 2)

        start_value_day = total_value - daily_pnl_all
        daily_return = 0.0
        if start_value_day > 0:
            daily_return = round((daily_pnl_all / start_value_day) * 100, 2)
    else:
        cash_percent = 0.0
        total_rate = 0.0
        daily_return = 0.0

    summary_obj = {
        "total_value": total_value,
        "daily_pnl": daily_pnl_all,
        "daily_return": daily_return,
        "total_pnl": total_pnl_all,
        "total_return": total_rate,
        "cash": total_cash_all,
        "cash_percent": cash_percent
    }

    # Load and Update History
    portfolio = load_portfolio()
    history = portfolio.get("history", [])

    today_str = datetime.date.today().strftime("%Y-%m-%d")

    # Check if today exists, update it if so, else append
    todays_entry = next((item for item in history if item["date"] == today_str), None)

    if todays_entry:
        todays_entry["value"] = total_value
    else:
        history.append({
            "date": today_str,
            "value": total_value
        })

    # Sort history by date and limit to last 60 days
    history.sort(key=lambda x: x['date'])
    if len(history) > MAX_HISTORY_DAYS:
        history = history[-MAX_HISTORY_DAYS:]

    # --- Virtual Accounts Logic ---
    virtual_accounts_data = []

    if config:
        try:
            target_acc_data = None
            target_id = "8119599511"

            # Find the account data to split
            for ad in accounts_data:
                if target_id in ad['name']:
                    target_acc_data = ad
                    break

            if not target_acc_data and accounts_data:
                target_acc_data = accounts_data[0] # Fallback

            if target_acc_data and "strategies" in config:
                # Build lookups: stock_code -> holding details
                stock_value_map = {}
                stock_cost_map = {}
                stock_pnl_map = {}
                for h in holdings_list:
                    code = h.get('symbol', '')
                    stock_value_map[code] = h['value']
                    stock_cost_map[code] = h['avg_price'] * h['quantity']
                    stock_pnl_map[code] = h['pnl']

                total_capital = config.get("total_capital", target_acc_data.get('total_value', 0))

                for strategy in config["strategies"]:
                    s_id = strategy["id"]
                    s_alloc = strategy["total_allocation_percent"]
                    stock_code = strategy.get("stock_code", "")

                    # Strategy's initial capital allocation
                    strategy_capital = total_capital * s_alloc

                    # Actual stock value and cost for this strategy
                    actual_stock_value = stock_value_map.get(stock_code, 0)
                    actual_stock_cost = stock_cost_map.get(stock_code, 0)
                    actual_stock_pnl = stock_pnl_map.get(stock_code, 0)

                    # Cash = initial allocation - cost of stocks purchased
                    strategy_cash = strategy_capital - actual_stock_cost

                    for acc in strategy["accounts"]:
                        ratio = acc["ratio"]
                        suffix = acc["suffix"]
                        v_name = f"{s_id}_{suffix}"

                        # Split by sub-account ratio
                        v_equity = int(actual_stock_value * ratio)
                        v_cash = int(strategy_cash * ratio)
                        v_pnl = int(actual_stock_pnl * ratio)
                        v_val = v_cash + v_equity

                        virtual_accounts_data.append({
                            "name": v_name,
                            "real_account_ref": target_acc_data['name'],
                            "allocation_ratio": ratio * s_alloc,
                            "total_value": v_val,
                            "cash": v_cash,
                            "equity": v_equity,
                            "total_pnl": v_pnl,
                            "sector": strategy.get("sector", "Unknown")
                        })

            elif target_acc_data and "strategy" in config:
                ratios = config["strategy"].get("allocation_ratio", {})
                base_total_value = target_acc_data.get('total_value', 0)
                base_cash = target_acc_data.get('cash', 0)
                base_equity = target_acc_data.get('equity', 0)
                base_pnl = total_pnl_all

                for account_name, ratio in ratios.items():
                    v_val = int(base_total_value * ratio)
                    v_cash = int(base_cash * ratio)
                    v_equity = int(base_equity * ratio)
                    v_pnl = int(base_pnl * ratio)

                    virtual_accounts_data.append({
                        "name": account_name,
                        "real_account_ref": target_acc_data['name'],
                        "allocation_ratio": ratio,
                        "total_value": v_val,
                        "cash": v_cash,
                        "equity": v_equity,
                        "total_pnl": v_pnl
                    })

        except Exception as e:
            print(f"Error processing virtual accounts: {e}")

    # Final Structure
    final_json = {
        "summary": summary_obj,
        "history": history,
        "holdings": holdings_list,
        "accounts": accounts_data,
        "virtual_accounts": virtual_accounts_data
    }

    # Save
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(final_json, f, ensure_ascii=False, indent=2)

    print(f"Successfully generated {PORTFOLIO_FILE}")
    print(json.dumps(final_json, indent=2, ensure_ascii=False))
    return True

def main():
    app = QApplication(sys.argv)
    kiwoom = Kiwoom()
    print("Connecting to Kiwoom API...")
    kiwoom.comm_connect()
    time.sleep(1)

    fetch_and_generate_portfolio(kiwoom)

if __name__ == "__main__":
    main()
