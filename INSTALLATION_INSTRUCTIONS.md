# Installation Instructions - Improved main() Function

## 📋 What This Improves

✅ **Prevents duplicate Kiwoom login errors** - Single connection reused throughout
✅ **Builds historical data automatically** - Updates `performance_log` every iteration
✅ **More efficient** - Portfolio generation once per iteration, not per transaction
✅ **Cleaner GitHub history** - One commit per iteration instead of per transaction
✅ **Better error handling** - Graceful failures with detailed logging
✅ **Proper shutdown** - Saves final state and syncs to GitHub on Ctrl+C

---

## 🔧 Installation Steps

### Step 1: Backup Your Current File

```bash
# In your kiwoom_stock_trading directory
cp your_main_trading_file.py your_main_trading_file.py.backup
```

### Step 2: Copy the New Function

**Option A: Replace Entire main() Function**

1. Open your main trading file (e.g., `real_time_bot.py` or `main.py`)
2. Find the `def main():` function (starts around line 50-100)
3. Delete everything from `def main():` to the end of that function
4. Copy the entire `main()` function from `improved_main.py`
5. Paste it in place of the old function

**Option B: Create New File (Recommended for Testing)**

1. Copy `improved_main.py` to your `kiwoom_stock_trading` directory
2. Rename imports at the top if needed to match your file names
3. Test run: `python improved_main.py`
4. Once verified, replace the original

### Step 3: Add the Helper Function

The new version includes a helper function `update_account_snapshots()`. Add this **before** the `main()` function:

```python
def update_account_snapshots(kiwoom, accounts_map):
    """
    Update all accounts with current price snapshots.
    This populates the performance_log for historical data.
    """
    # ... (copy from improved_main.py lines 90-145)
```

### Step 4: Verify Your Imports

Make sure these imports are at the top of your file:

```python
import sys
import time
import json
import traceback  # ← ADD THIS if missing
import os
from datetime import datetime, time as dtime
from PyQt5.QtWidgets import QApplication
from kiwoom_api import Kiwoom
from account_manager import Account, save_accounts, load_accounts
from strategy_executor import StrategyExecutor
from github_sync import GitHubSync
from generate_portfolio_json import fetch_and_generate_portfolio
```

---

## ✅ Verification Checklist

After installation, verify:

### 1. **Check StrategyExecutor Receives Kiwoom Instance**

Open `strategy_executor.py` and verify:

```python
class StrategyExecutor:
    def __init__(self, kiwoom, accounts_map, config, on_transaction_complete=None):
        self.kiwoom = kiwoom  # ← Must store the instance!
        self.accounts_map = accounts_map
        self.config = config
        # ...

    def execute_step(self):
        # Use self.kiwoom (NOT creating new Kiwoom())
        price = self.kiwoom.get_current_price(stock_code)
        # ...
```

**If `self.kiwoom` is missing**, add it to the `__init__` method.

### 2. **Test Run (Dry Run Mode)**

```bash
# Set dry_run to true in config.json
python your_main_trading_file.py
```

**Expected output:**
```
Real-Time Trading Bot - Starting
✅ Connected to Kiwoom API
...
Iteration #1 - 2026-02-12 10:00:00
📊 Executing strategy...
✅ Strategy execution complete
📈 Updating account snapshots...
✅ Snapshots updated
✅ Account state saved
📄 Generating portfolio.json...
✅ portfolio.json generated
🔄 Syncing to GitHub...
✅ Synced to GitHub
```

### 3. **Verify Performance Log is Growing**

After a few iterations, check `trade_state.json`:

```bash
# Should see performance_log entries
grep -A 5 "performance_log" trade_state.json
```

**Expected:**
```json
"performance_log": [
  {
    "time": "2026-02-12 10:00:00",
    "total_value": 100000000,
    "balance": 95000000,
    "pnl": -50000,
    "pnl_rate": -0.05,
    "holdings_count": 1
  },
  {
    "time": "2026-02-12 10:05:00",
    ...
  }
]
```

### 4. **Check GitHub Commits**

```bash
cd /path/to/kiwoom_stock_trading
git log --oneline -5
```

**Expected:** One commit per iteration (not per transaction)
```
abc1234 Auto-update: 2026-02-12 10:15:00 (Iteration #3)
def5678 Auto-update: 2026-02-12 10:10:00 (Iteration #2)
```

---

## 🐛 Troubleshooting

### Issue: "StrategyExecutor object has no attribute 'update_config'"

**Fix:** Add this method to `strategy_executor.py`:

```python
def update_config(self, new_config):
    """Update configuration dynamically."""
    self.config = new_config
    print("  StrategyExecutor config updated")
```

### Issue: "Duplicate login error"

**Cause:** StrategyExecutor is creating its own Kiwoom instance

**Fix:** In `strategy_executor.py`, remove any `Kiwoom()` instantiation and use `self.kiwoom`

### Issue: "performance_log not growing"

**Possible causes:**
1. `Account.update_snapshot()` not being called (verify in code)
2. No price data available (check if holdings exist)
3. Error in `update_account_snapshots()` (check console output)

**Debug:** Add print statement in `Account.update_snapshot()`:
```python
def update_snapshot(self, current_prices, timestamp=None):
    # ...
    print(f"DEBUG: Snapshot added to {self.account_id}")  # ADD THIS
    self.performance_log.append(snapshot)
```

### Issue: "portfolio.json not updating"

**Check:**
1. Does `outputs/portfolio.json` exist?
2. Run manually: `python generate_portfolio_json.py`
3. Check for errors in console

---

## 📊 Monitoring Dashboard Data

### Check Current Data

```bash
# View latest portfolio.json
cat outputs/portfolio.json | jq '.history | length'
# Should show number of days (grows daily)

# View latest snapshot count
cat trade_state.json | jq '.[0].performance_log | length'
# Should show number of 5-min snapshots
```

### Expected Growth Pattern

**First Day:**
- `history`: 1 entry
- `performance_log`: ~12-72 entries (depending on how many hours traded)

**After 10 Days:**
- `history`: 10 entries
- `performance_log`: ~120-720 entries

**After 60 Days:**
- `history`: 60 entries (max)
- `performance_log`: ~720-4320 entries (trimmed if needed)

---

## 🎯 Next Steps After Installation

1. **Run in dry mode** for 1-2 hours to verify everything works
2. **Check dashboard** at www.jonghoonk.com/dashboard_stock/
3. **Verify time series chart** populates with data over days
4. **Monitor GitHub commits** - should be clean and regular
5. **Switch to live mode** when confident

---

## 📞 Need Help?

If you encounter issues:

1. Check the console output for specific error messages
2. Verify `StrategyExecutor` properly uses the Kiwoom instance
3. Make sure all imports are correct
4. Test components individually (e.g., run `generate_portfolio_json.py` standalone)

**Common fix:** If something doesn't work, the most likely issue is `StrategyExecutor` not receiving/using the shared `kiwoom` instance. Check that file first!
