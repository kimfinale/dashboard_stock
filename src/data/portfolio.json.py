import json
import random
import datetime

def generate_mock_data():
    today = datetime.date.today()
    mock_data = {
        "summary": {},
        "history": [],
        "holdings": [],
        "accounts": []
    }

    # 1. Accounts
    accounts = ["Account #1", "Account #2", "Account #3"]
    account_values = {acc: 0 for acc in accounts}

    # 2. Holdings (Randomly generated)
    stocks = [
        {"name": "Samsung Electronics", "symbol": "005930", "price": 72000, "sector": "Tech"},
        {"name": "SK Hynix", "symbol": "000660", "price": 135000, "sector": "Tech"},
        {"name": "Naver", "symbol": "035420", "price": 210000, "sector": "Tech"},
        {"name": "Kakao", "symbol": "035720", "price": 55000, "sector": "Tech"},
        {"name": "Hyundai Motor", "symbol": "005380", "price": 190000, "sector": "Auto"},
        {"name": "LG Energy Solution", "symbol": "373220", "price": 410000, "sector": "Battery"},
        {"name": "POSCO Holdings", "symbol": "005490", "price": 450000, "sector": "Materials"},
        {"name": "KB Financial", "symbol": "105560", "price": 52000, "sector": "Finance"},
        {"name": "Shinhan Financial", "symbol": "055550", "price": 38000, "sector": "Finance"},
        {"name": "Celltrion", "symbol": "068270", "price": 160000, "sector": "Bio"}
    ]

    total_holdings_value = 0
    
    for stock in stocks:
        # Randomly assign holdings
        if random.random() > 0.3: # 70% chance to hold
            quantity = random.randint(10, 500)
            avg_price = int(stock["price"] * random.uniform(0.8, 1.2))
            current_value = quantity * stock["price"]
            pnl = current_value - (quantity * avg_price)
            pnl_percent = (pnl / (quantity * avg_price)) * 100
            
            # Randomly assign to an account
            account = random.choice(accounts)
            account_values[account] += current_value

            mock_data["holdings"].append({
                "name": stock["name"],
                "symbol": stock["symbol"],
                "sector": stock["sector"],
                "quantity": quantity,
                "avg_price": avg_price,
                "current_price": stock["price"],
                "value": current_value,
                "pnl": pnl,
                "pnl_percent": round(pnl_percent, 2),
                "account": account
            })
            total_holdings_value += current_value

    # 3. Cash
    total_cash = random.randint(5000000, 50000000)
    # Distribute cash among accounts
    for acc in accounts:
        cash_share = int(total_cash * random.random() / len(accounts)) # Roughly distribute
        account_values[acc] += cash_share
        # Creating a specific accounts breakdown list
        mock_data["accounts"].append({
            "name": acc,
            "total_value": account_values[acc],
            "cash": cash_share,
            "equity": account_values[acc] - cash_share # approximate
        })
        # Re-adjust total cash to match sum of parts if we wanted to be precise, but this is mock.
    
    # 4. History (Past 1 year)
    current_portfolio_value = total_holdings_value + total_cash
    history = []
    value = current_portfolio_value
    
    # Trace back 365 days
    for i in range(365):
        date = today - datetime.timedelta(days=i)
        # Random daily fluctuation
        daily_return = random.normalvariate(0.0005, 0.01) # Mean 0.05%, Std 1%
        value = value / (1 + daily_return)
        
        history.append({
            "date": date.strftime("%Y-%m-%d"),
            "value": int(value)
        })
    
    mock_data["history"] = history[::-1] # Reverse to be chronological

    # 5. Summary Metrics
    prev_day_value = mock_data["history"][-2]["value"]
    daily_pnl = current_portfolio_value - prev_day_value
    daily_return = (daily_pnl / prev_day_value) * 100
    
    initial_investment = mock_data["history"][0]["value"] # Simplified assumption
    total_pnl = current_portfolio_value - initial_investment
    total_return = (total_pnl / initial_investment) * 100

    mock_data["summary"] = {
        "total_value": int(current_portfolio_value),
        "daily_pnl": int(daily_pnl),
        "daily_return": round(daily_return, 2),
        "total_pnl": int(total_pnl),
        "total_return": round(total_return, 2),
        "cash": int(total_cash),
        "cash_percent": round((total_cash / current_portfolio_value) * 100, 2)
    }

    print(json.dumps(mock_data, indent=2))

if __name__ == "__main__":
    generate_mock_data()
