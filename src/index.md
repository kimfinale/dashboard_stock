# Stock Investment Dashboard

```js
import * as Plot from "npm:@observablehq/plot";
import * as Inputs from "npm:@observablehq/inputs";
import * as d3 from "npm:d3";

// Load data
const data = await FileAttachment("portfolio.json").json();
const summary = data.summary;
const history = data.history.map(d => ({date: new Date(d.date), value: d.value}));
const holdings = data.holdings;
const accounts = data.accounts;

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
      ${formatCurrency(summary.daily_pnl)} (${formatPercent(summary.daily_return)}%)
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
    <h2>Today's Performance</h2>
    <div class="big">₩${formatCurrency(summary.daily_pnl)}</div>
    <div class="muted">
      ${formatPercent(summary.daily_return)}%
    </div>
  </div>
  <div class="card">
    <h2>Cash Position</h2>
    <div class="big">₩${formatCurrency(summary.cash)}</div>
    <div class="muted">
      ${summary.cash_percent}% of portfolio
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
        ${
            Inputs.table(filteredHoldings, {
                columns: ["name", "sector", "quantity", "avg_price", "current_price", "value", "pnl", "pnl_percent", "account"],
                header: {
                    name: "Name", 
                    sector: "Sector",
                    quantity: "Qty", 
                    avg_price: "Avg Price", 
                    current_price: "Cur Price", 
                    value: "Value", 
                    pnl: "P&L", 
                    pnl_percent: "Return %",
                    account: "Account"
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
        }
    </div>
</div>

<div class="grid grid-cols-1">
    <div class="card">
        <h2>Account Breakdown</h2>
         ${
            Inputs.table(accounts, {
                columns: ["name", "total_value", "cash", "equity"],
                header: {name: "Account", total_value: "Total Value", cash: "Cash", equity: "Equity"},
                format: {
                    total_value: x => `₩${formatCurrency(x)}`,
                    cash: x => `₩${formatCurrency(x)}`,
                    equity: x => `₩${formatCurrency(x)}`
                }
            })
        }
    </div>
</div>
