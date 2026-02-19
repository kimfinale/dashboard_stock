# Stock Investment Dashboard

<style>
.table-scroll {
  overflow-x: auto;
  overflow-y: auto;
  max-height: 500px;
}
.table-scroll table {
  min-width: 700px;
}
</style>

```js
import * as Plot from "npm:@observablehq/plot";
import * as Inputs from "npm:@observablehq/inputs";
import * as d3 from "npm:d3";

// Load data directly from GitHub (fetches fresh data on every page load)
const DATA_URL = "https://raw.githubusercontent.com/kimfinale/kiwoom_stock_trading/refs/heads/master/outputs/portfolio.json";
const response = await fetch(DATA_URL);
const data = await response.json();
const summary = data.summary;
const history = data.history.map(d => ({date: new Date(d.date), value: d.value}));
const holdings = data.holdings;
const accounts = data.accounts;
const virtualAccounts = data.virtual_accounts || [];

// Aggregate virtual accounts by strategy (e.g., Samsung_1..5 → Samsung)
const strategyMap = new Map();
for (const va of virtualAccounts) {
  const strategy = va.name.replace(/_\d+$/, "");
  if (!strategyMap.has(strategy)) {
    strategyMap.set(strategy, {name: strategy, sector: va.sector, total_value: 0, cash: 0, equity: 0, unrealized_pnl: 0, realized_pnl: 0, count: 0});
  }
  const s = strategyMap.get(strategy);
  s.total_value += va.total_value;
  s.cash += va.cash;
  s.equity += va.equity;
  s.unrealized_pnl += (va.unrealized_pnl || 0);
  s.realized_pnl += (va.realized_pnl || 0);
  s.count += 1;
}
const strategies = Array.from(strategyMap.values()).sort((a, b) => b.total_value - a.total_value);

// Formatters
const formatCurrency = d3.format(",.0f");
const formatPercent = d3.format("+.2f");
const formatNumber = d3.format(",.2f");

// Helper to calculate risk metrics
function calculateRisk(hist) {
  const returns = [];
  let maxVal = 0;
  let maxDD = 0;
  
  for (let i = 1; i < hist.length; i++) {
    const r = (hist[i].value - hist[i-1].value) / hist[i-1].value;
    returns.push(r);
    
    if (hist[i].value > maxVal) maxVal = hist[i].value;
    const dd = (maxVal - hist[i].value) / maxVal;
    if (dd > maxDD) maxDD = dd;
  }
  
  const meanReturn = d3.mean(returns);
  const stdDev = d3.deviation(returns);
  const annualizedVol = stdDev * Math.sqrt(252);
  const sharpe = (meanReturn / stdDev) * Math.sqrt(252); // Assuming 0 risk-free
  
  return {
    volatility: annualizedVol * 100,
    maxDrawdown: maxDD * 100,
    sharpe: sharpe
  };
}

const riskMetrics = calculateRisk(history);
const topHoldings = holdings.slice().sort((a, b) => b.value - a.value).slice(0, 3);
const concentration = d3.sum(topHoldings, d => d.value) / summary.total_value * 100;
```

<div class="grid grid-cols-4">
  <div class="card">
    <h2>Total Portfolio Value</h2>
    <div class="big">₩${formatCurrency(summary.total_value)}</div>
    <div class="muted">
      Cash: ₩${formatCurrency(summary.cash)} (${summary.cash_percent}%)
    </div>
  </div>
  <div class="card">
    <h2>Total Return</h2>
    <div class="big">₩${formatCurrency(summary.total_pnl)}</div>
    <div class="muted">
      ${formatPercent(summary.total_return)}% since inception
    </div>
  </div>
  <div class="card">
    <h2>평가손익 (Unrealized)</h2>
    <div class="big">₩${formatCurrency(summary.unrealized_pnl || 0)}</div>
    <div class="muted">
      Paper gains on current holdings
    </div>
  </div>
  <div class="card">
    <h2>실현손익 (Realized)</h2>
    <div class="big">₩${formatCurrency(summary.realized_pnl || 0)}</div>
    <div class="muted">
      Profit from completed trades
    </div>
  </div>
</div>

<div class="grid grid-cols-1">
  <div class="card">
    <h2>Portfolio Value Over Time</h2>
    <div style="display: flex; justify-content: flex-end;">${timeRangeInput}</div>
    ${
      Plot.plot({
        y: {grid: true, label: "Value (KRW)", tickFormat: "s"},
        x: {label: "Date"},
        marks: [
          Plot.lineY(history.filter(d => {
             const now = new Date();
             if (timeRange === "1M") return d.date > d3.timeMonth.offset(now, -1);
             if (timeRange === "3M") return d.date > d3.timeMonth.offset(now, -3);
             if (timeRange === "6M") return d.date > d3.timeMonth.offset(now, -6);
             if (timeRange === "1Y") return d.date > d3.timeYear.offset(now, -1);
             return true; 
          }), {x: "date", y: "value", tip: true, stroke: "steelblue"}),
          Plot.ruleY([0])
        ]
      })
    }
  </div>
</div>

```js
const timeRangeInput = Inputs.radio(["1M", "3M", "6M", "1Y", "All"], {label: "Time Range", value: "All"});
const timeRange = Generators.input(timeRangeInput);

// Text search for holdings
const searchInput = Inputs.search(holdings, {placeholder: "Search stocks..."});
const filteredHoldings = Generators.input(searchInput);

// Text search for virtual accounts
const vaSearchInput = Inputs.search(virtualAccounts, {placeholder: "Search virtual accounts..."});
const filteredVA = Generators.input(vaSearchInput);
```

<div class="grid grid-cols-2">
  <div class="card">
    <h2>Asset Allocation</h2>
    ${
      Plot.plot({
        marginBottom: 40,
        x: {axis: null},
        y: {label: "Value (KRW)", tickFormat: "s", grid: true},
        color: {legend: true},
        marks: [
            Plot.barY(holdings, {x: "name", y: "value", fill: "sector", sort: {x: "y", reverse: true}, tip: true}),
            Plot.ruleY([0])
        ]
      })
    }
  </div>
  <div class="card">
    <h2>Risk & Stats</h2>
    <table style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #333;">Volatility (Ann.)</td>
            <td style="padding: 8px; border-bottom: 1px solid #333; text-align: right; font-weight: bold;">${formatNumber(riskMetrics.volatility)}%</td>
        </tr>
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #333;">Max Drawdown</td>
            <td style="padding: 8px; border-bottom: 1px solid #333; text-align: right; font-weight: bold; color: #ff6b6b;">-${formatNumber(riskMetrics.maxDrawdown)}%</td>
        </tr>
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #333;">Sharpe Ratio</td>
            <td style="padding: 8px; border-bottom: 1px solid #333; text-align: right; font-weight: bold;">${formatNumber(riskMetrics.sharpe)}</td>
        </tr>
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #333;">Positions</td>
            <td style="padding: 8px; border-bottom: 1px solid #333; text-align: right; font-weight: bold;">${holdings.length}</td>
        </tr>
        <tr>
            <td style="padding: 8px;">Top 3 Concentration</td>
            <td style="padding: 8px; text-align: right; font-weight: bold;">${formatNumber(concentration)}%</td>
        </tr>
    </table>
  </div>
</div>

<div class="grid grid-cols-1">
    <div class="card">
        <h2>Holdings</h2>
        <div style="margin-bottom: 10px;">${searchInput}</div>
        <div class="table-scroll">${
            Inputs.table(filteredHoldings, {
                columns: ["name", "sector", "quantity", "avg_price", "current_price", "value", "pnl", "pnl_percent"],
                header: {
                    name: "Name",
                    sector: "Sector",
                    quantity: "Qty",
                    avg_price: "Avg Price",
                    current_price: "Cur Price",
                    value: "Value",
                    pnl: "P&L",
                    pnl_percent: "Return %"
                },
                width: {
                    name: 100,
                    sector: 90,
                    quantity: 50,
                    avg_price: 100,
                    current_price: 100,
                    value: 110,
                    pnl: 100,
                    pnl_percent: 80
                },
                sort: "value",
                reverse: true,
                format: {
                    value: x => `₩${formatCurrency(x)}`,
                    pnl: x => `₩${formatCurrency(x)}`,
                    avg_price: x => `₩${formatCurrency(x)}`,
                    current_price: x => `₩${formatCurrency(x)}`,
                    pnl_percent: x => `${formatPercent(x)}%`
                }
            })
        }</div>
    </div>
</div>

<div class="grid grid-cols-1">
    <div class="card">
        <h2>Account Breakdown</h2>
        <div class="table-scroll">${
            Inputs.table(accounts, {
                columns: ["name", "total_value", "cash", "equity"],
                header: {name: "Account", total_value: "Total Value", cash: "Cash", equity: "Equity"},
                format: {
                    total_value: x => `₩${formatCurrency(x)}`,
                    cash: x => `₩${formatCurrency(x)}`,
                    equity: x => `₩${formatCurrency(x)}`
                }
            })
        }</div>
    </div>
</div>

<div class="grid grid-cols-1">
    <div class="card">
        <h2>Virtual Accounts</h2>
        <div style="margin-bottom: 10px;">${vaSearchInput}</div>
        <div class="table-scroll">${
            Inputs.table(filteredVA, {
                columns: ["name", "sector", "strategy_type", "rise_pct", "dip_pct", "allocation_ratio", "total_value", "cash", "equity", "unrealized_pnl", "realized_pnl", "buy_count", "sell_count"],
                header: {
                    name: "Account",
                    sector: "Sector",
                    strategy_type: "Strategy",
                    rise_pct: "Rise %",
                    dip_pct: "Dip %",
                    allocation_ratio: "Alloc",
                    total_value: "Total Value",
                    cash: "Cash",
                    equity: "Equity",
                    unrealized_pnl: "평가손익",
                    realized_pnl: "실현손익",
                    buy_count: "Buys",
                    sell_count: "Sells"
                },
                width: {
                    name: 150,
                    sector: 90,
                    strategy_type: 80,
                    rise_pct: 55,
                    dip_pct: 55,
                    allocation_ratio: 55,
                    total_value: 100,
                    cash: 100,
                    equity: 90,
                    unrealized_pnl: 85,
                    realized_pnl: 85,
                    buy_count: 50,
                    sell_count: 50
                },
                sort: "name",
                format: {
                    total_value: x => `₩${formatCurrency(x)}`,
                    cash: x => `₩${formatCurrency(x)}`,
                    equity: x => `₩${formatCurrency(x)}`,
                    unrealized_pnl: x => `₩${formatCurrency(x)}`,
                    realized_pnl: x => `₩${formatCurrency(x)}`,
                    allocation_ratio: x => `${(x * 100).toFixed(1)}%`,
                    rise_pct: x => `${x}%`,
                    dip_pct: x => x ? `${x}%` : "—"
                }
            })
        }</div>
    </div>
</div>
