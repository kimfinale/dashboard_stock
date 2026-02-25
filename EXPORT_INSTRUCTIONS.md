# Export Instructions for Trading Bot → Dashboard

This guide explains how to export your trading account data to the dashboard.

## 📁 File Location

**Copy `export_to_dashboard.py` to your `kiwoom_stock_trading` project directory.**

The file structure should be:
```
kiwoom_stock_trading/
├── trade_state.json          ← Your account data (saved by trading bot)
├── export_to_dashboard.py    ← Copy this file here
└── outputs/
    └── portfolio.json         ← Generated output (dashboard reads this)
```

## 🚀 How to Use

### 1. Run the Export Script

In your `kiwoom_stock_trading` directory:

```bash
python export_to_dashboard.py
```

### 2. What It Does

The script:
- ✅ Reads `trade_state.json` (all Account objects)
- ✅ Aggregates 5-minute `performance_log` snapshots to daily values
- ✅ Calculates summary metrics (total value, P&L, returns)
- ✅ Extracts current holdings with prices and performance
- ✅ Creates account breakdown
- ✅ Exports everything to `outputs/portfolio.json`

### 3. Output Format

Creates `outputs/portfolio.json`:

```json
{
  "summary": {
    "total_value": 100224377,
    "daily_pnl": 255242,
    "daily_return": 0.26,
    "total_pnl": -45185,
    "total_return": -0.04,
    "cash": 95964080,
    "cash_percent": 95.75
  },
  "history": [
    {"date": "2025-12-13", "value": 99500000},
    {"date": "2025-12-14", "value": 99750000},
    ...
    {"date": "2026-02-12", "value": 100224377}
  ],
  "holdings": [
    {
      "name": "005930",
      "sector": "Technology",
      "quantity": 24,
      "avg_price": 167577,
      "current_price": 167200,
      "value": 4012800,
      "pnl": -9048,
      "pnl_percent": -0.23,
      "account": "Account_1"
    }
  ],
  "accounts": [
    {
      "name": "Account_1",
      "total_value": 50000000,
      "cash": 45000000,
      "equity": 5000000
    }
  ]
}
```

## 🔄 Automate the Export

### Option A: Run Manually (Testing)
```bash
python export_to_dashboard.py
```

### Option B: Add to Your Trading Bot (Recommended)

In your main trading script, after `save_accounts()`:

```python
from export_to_dashboard import export_portfolio_json

# Save account state
save_accounts(accounts, "trade_state.json")

# Export to dashboard
export_portfolio_json([acc.to_dict() for acc in accounts])
```

### Option C: Scheduled Task (Advanced)

**Windows (Task Scheduler):**
- Run `export_to_dashboard.py` every 5 minutes or at market close

**Linux/Mac (cron):**
```bash
# Add to crontab -e
*/5 * * * * cd /path/to/kiwoom_stock_trading && python export_to_dashboard.py
```

## 🎨 Enhancements (Optional)

### Add Stock Name Mapping

Create `stock_names.json`:
```json
{
  "005930": "Samsung Electronics",
  "000660": "SK Hynix",
  "035420": "Naver"
}
```

Update `export_to_dashboard.py`:
```python
# Load stock names
with open("stock_names.json") as f:
    STOCK_NAMES = json.load(f)

# In get_current_holdings():
holdings_list.append({
    "name": STOCK_NAMES.get(code, code),  # Use name if available
    ...
})
```

### Add Real-Time Prices

If you have a price API:

```python
def fetch_current_prices(codes):
    """Fetch current market prices for stock codes."""
    prices = {}
    for code in codes:
        # Call your API here
        prices[code] = get_market_price(code)
    return prices

# In main():
codes = [acc.get("stock_code") for acc in accounts if acc.get("stock_code")]
current_prices = fetch_current_prices(codes)
export_portfolio_json(accounts, current_prices=current_prices)
```

### Add Sector Classification

Create sector mapping:
```python
SECTOR_MAP = {
    "005930": "Technology",
    "000660": "Semiconductors",
    "035420": "Internet",
    "005380": "Automotive",
    # etc.
}
```

## 📊 Dashboard Updates

After running the export:
1. **Commit and push** `outputs/portfolio.json` to GitHub
2. **Dashboard automatically updates** (fetches on page load)
3. **Time series chart** now shows 60 days of history!

## ❓ Troubleshooting

**Q: Script can't find trade_state.json**
- Ensure you're running from `kiwoom_stock_trading` directory
- Check that `trade_state.json` exists

**Q: Empty or minimal history**
- Your `performance_log` may not have 60 days yet
- Script will export whatever data is available

**Q: Holdings show wrong prices**
- Pass `current_prices` dictionary to get accurate valuations
- Otherwise uses average purchase price

**Q: Want to test without real data**
- Create a sample `trade_state.json` with mock Account data
- Run the script to verify output format

## 🎯 Next Steps

1. Copy `export_to_dashboard.py` to `kiwoom_stock_trading/`
2. Run it: `python export_to_dashboard.py`
3. Check `outputs/portfolio.json` was created
4. Commit and push to GitHub
5. Visit your dashboard: **www.jonghoonk.com/dashboard_stock/**
6. See the beautiful time series chart! 📈

---

**Questions?** Let me know if you need help integrating this into your trading bot!
