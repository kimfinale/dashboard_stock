"""
Export trading account data to dashboard-compatible JSON format.

This script reads Account objects from trade_state.json and exports:
- Current summary metrics
- 60-day historical performance (aggregated from 5-min snapshots)
- Current holdings details
- Account breakdown

Usage:
    python export_to_dashboard.py

Output:
    outputs/portfolio.json (compatible with Observable dashboard)
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

def load_accounts_from_json(filename="trade_state.json"):
    """Load Account objects from JSON file."""
    if not os.path.exists(filename):
        raise FileNotFoundError(f"{filename} not found")

    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data  # List of account dicts

def aggregate_daily_performance(accounts):
    """
    Aggregate 5-minute performance_log snapshots to daily end-of-day values.

    Args:
        accounts: List of account dictionaries

    Returns:
        List of {"date": "YYYY-MM-DD", "value": total_portfolio_value}
    """
    # Collect all timestamps and values across all accounts
    daily_values = defaultdict(lambda: {"total_value": 0, "timestamp": None})

    for account in accounts:
        performance_log = account.get("performance_log", [])

        for snapshot in performance_log:
            timestamp_str = snapshot["time"]
            total_value = snapshot["total_value"]

            # Parse timestamp
            try:
                dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # Try alternative format if needed
                continue

            date_key = dt.strftime("%Y-%m-%d")

            # Accumulate total value across all accounts
            daily_values[date_key]["total_value"] += total_value

            # Keep the latest timestamp for each day (for sorting)
            if daily_values[date_key]["timestamp"] is None or dt > daily_values[date_key]["timestamp"]:
                daily_values[date_key]["timestamp"] = dt

    # Convert to sorted list
    history = []
    for date_str in sorted(daily_values.keys()):
        history.append({
            "date": date_str,
            "value": int(daily_values[date_str]["total_value"])
        })

    # Limit to last 60 days
    if len(history) > 60:
        history = history[-60:]

    return history

def get_current_summary(accounts, history):
    """
    Calculate current portfolio summary metrics.

    Args:
        accounts: List of account dictionaries
        history: List of daily values

    Returns:
        Dictionary with summary metrics
    """
    total_value = 0
    total_principal = 0
    total_cash = 0

    for account in accounts:
        total_principal += account.get("principal", 0)
        total_cash += account.get("balance", 0)

        # Get latest total value from performance_log
        perf_log = account.get("performance_log", [])
        if perf_log:
            total_value += perf_log[-1]["total_value"]

    # Calculate returns
    total_pnl = total_value - total_principal
    total_return = (total_pnl / total_principal * 100) if total_principal > 0 else 0

    # Calculate daily return (today vs yesterday)
    daily_pnl = 0
    daily_return = 0

    if len(history) >= 2:
        today_value = history[-1]["value"]
        yesterday_value = history[-2]["value"]
        daily_pnl = today_value - yesterday_value
        daily_return = (daily_pnl / yesterday_value * 100) if yesterday_value > 0 else 0

    cash_percent = (total_cash / total_value * 100) if total_value > 0 else 0

    return {
        "total_value": int(total_value),
        "daily_pnl": int(daily_pnl),
        "daily_return": round(daily_return, 2),
        "total_pnl": int(total_pnl),
        "total_return": round(total_return, 2),
        "cash": int(total_cash),
        "cash_percent": round(cash_percent, 2)
    }

def get_current_holdings(accounts, current_prices=None):
    """
    Get detailed holdings from all accounts.

    Args:
        accounts: List of account dictionaries
        current_prices: Optional dict of {code: current_price}

    Returns:
        List of holding dictionaries
    """
    # Aggregate holdings across all accounts
    aggregated_holdings = defaultdict(lambda: {
        "qty": 0,
        "total_cost": 0,
        "accounts": []
    })

    for account in accounts:
        account_id = account.get("account_id", "Unknown")
        holdings = account.get("holdings", {})

        for code, holding in holdings.items():
            aggregated_holdings[code]["qty"] += holding["qty"]
            aggregated_holdings[code]["total_cost"] += holding["total_cost"]
            aggregated_holdings[code]["accounts"].append(account_id)

    # Convert to list format for dashboard
    holdings_list = []

    for code, data in aggregated_holdings.items():
        qty = data["qty"]
        total_cost = data["total_cost"]
        avg_price = total_cost / qty if qty > 0 else 0

        # Use current price if provided, otherwise use avg_price
        current_price = current_prices.get(code, avg_price) if current_prices else avg_price

        value = current_price * qty
        pnl = value - total_cost
        pnl_percent = (pnl / total_cost * 100) if total_cost > 0 else 0

        # Determine sector (you can enhance this with a lookup table)
        sector = "Technology"  # Default, can be mapped based on code

        holdings_list.append({
            "name": code,  # You can map code to name later
            "sector": sector,
            "quantity": qty,
            "avg_price": int(avg_price),
            "current_price": int(current_price),
            "value": int(value),
            "pnl": int(pnl),
            "pnl_percent": round(pnl_percent, 2),
            "account": ", ".join(data["accounts"][:2])  # Show first 2 accounts
        })

    # Sort by value descending
    holdings_list.sort(key=lambda x: x["value"], reverse=True)

    return holdings_list

def get_account_breakdown(accounts):
    """
    Get breakdown by individual accounts.

    Args:
        accounts: List of account dictionaries

    Returns:
        List of account summary dictionaries
    """
    account_list = []

    for account in accounts:
        account_id = account.get("account_id", "Unknown")
        balance = account.get("balance", 0)

        # Calculate equity (total holdings value)
        equity = 0
        holdings = account.get("holdings", {})
        for code, holding in holdings.items():
            equity += holding["avg_price"] * holding["qty"]

        total_value = balance + equity

        account_list.append({
            "name": account_id,
            "total_value": int(total_value),
            "cash": int(balance),
            "equity": int(equity)
        })

    return account_list

def export_portfolio_json(accounts, output_path="outputs/portfolio.json", current_prices=None):
    """
    Main export function to create dashboard-compatible JSON.

    Args:
        accounts: List of account dictionaries
        output_path: Path to output JSON file
        current_prices: Optional dict of {code: current_price}
    """
    # 1. Aggregate daily performance history
    print("Aggregating performance history...")
    history = aggregate_daily_performance(accounts)
    print(f"  Found {len(history)} days of history")

    # 2. Calculate current summary
    print("Calculating summary metrics...")
    summary = get_current_summary(accounts, history)

    # 3. Get current holdings
    print("Processing holdings...")
    holdings = get_current_holdings(accounts, current_prices)
    print(f"  Found {len(holdings)} holdings")

    # 4. Get account breakdown
    print("Creating account breakdown...")
    account_breakdown = get_account_breakdown(accounts)

    # 5. Combine into final structure
    portfolio_data = {
        "summary": summary,
        "history": history,
        "holdings": holdings,
        "accounts": account_breakdown
    }

    # 6. Export to JSON
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(portfolio_data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Portfolio data exported to {output_path}")
    print(f"  Total Value: ₩{summary['total_value']:,}")
    print(f"  Total Return: {summary['total_return']:+.2f}%")
    print(f"  Holdings: {len(holdings)} positions")
    print(f"  History: {len(history)} days")

    return portfolio_data

def main():
    """Main execution function."""
    print("=== Portfolio Data Export ===\n")

    # Load accounts from trade_state.json
    try:
        accounts = load_accounts_from_json("trade_state.json")
        print(f"Loaded {len(accounts)} account(s) from trade_state.json\n")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please ensure trade_state.json exists in the current directory")
        return

    # Optional: Provide current market prices for accurate valuation
    # You can enhance this to fetch real-time prices
    current_prices = {
        # "005930": 72000,  # Samsung Electronics
        # Add more as needed
    }

    # Export to portfolio.json
    export_portfolio_json(accounts, "outputs/portfolio.json", current_prices)

if __name__ == "__main__":
    main()
