# Add this to your existing script (in the history update section)

# After this line:
# history.sort(key=lambda x: x['date'])

# Add history limit to prevent unlimited growth
MAX_HISTORY_DAYS = 60
if len(history) > MAX_HISTORY_DAYS:
    history = history[-MAX_HISTORY_DAYS:]
    print(f"History limited to last {MAX_HISTORY_DAYS} days")

# Optional: Also add a cleanup for old entries
from datetime import datetime, timedelta

# Remove entries older than 60 days
cutoff_date = (datetime.now() - timedelta(days=MAX_HISTORY_DAYS)).strftime("%Y-%m-%d")
history = [h for h in history if h["date"] >= cutoff_date]
history.sort(key=lambda x: x['date'])
