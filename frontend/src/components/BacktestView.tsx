import React, { useState } from "react";
import {
  api,
  BacktestResponse,
  StrategyComparisonResponse,
  BacktestMetrics,
} from "../lib/api";

type Mode = "synthetic" | "csv" | "compare";

const STRATEGIES = [
  { id: "trend_continuation", label: "Trend Continuation / BOS Pullback" },
  { id: "liquidity_sweep", label: "Liquidity Sweep Continuation" },
  { id: "ict_silver_bullet", label: "ICT Silver Bullet" },
  { id: "london_breakout", label: "London Breakout" },
  { id: "mean_reversion", label: "Mean Reversion (RSI/Range)" },
];

export function BacktestView() {
  const [mode, setMode] = useState<Mode>("synthetic");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BacktestResponse | null>(null);
  const [comparison, setComparison] = useState<StrategyComparisonResponse | null>(null);
  const [csvFile, setCsvFile] = useState<File | null>(null);

  // Parameters
  const [symbol, setSymbol] = useState("EUR/USD");
  const [timeframe, setTimeframe] = useState("1h");
  const [strategy, setStrategy] = useState("trend_continuation");
  const [capital, setCapital] = useState(10000);
  const [riskPct, setRiskPct] = useState(1.0);
  const [slippage, setSlippage] = useState(0.5);
  const [commission, setCommission] = useState(7.0);
  const [seed, setSeed] = useState<number | "">("");
  const [compareStrats, setCompareStrats] = useState<string[]>([
    "trend_continuation",
    "mean_reversion",
  ]);

  const handleSyntheticRun = async () => {
    setLoading(true);
    setError(null);
    setComparison(null);
    try {
      const res = await api.runBacktest({
        symbol,
        timeframe,
        strategy,
        initial_capital: capital,
        risk_per_trade: riskPct,
        slippage_pips: slippage,
        commission_per_lot: commission,
        random_seed: seed !== "" ? Number(seed) : null,
      });
      setResult(res);
    } catch (err: any) {
      setError(err.message || "Backtest execution failed");
    } finally {
      setLoading(false);
    }
  };

  const handleCsvRun = async () => {
    if (!csvFile) {
      setError("Please select a historical CSV file first.");
      return;
    }
    setLoading(true);
    setError(null);
    setComparison(null);
    try {
      const formData = new FormData();
      formData.append("file", csvFile);
      formData.append("symbol", symbol);
      formData.append("timeframe", timeframe);
      formData.append("strategy", strategy);
      formData.append("initial_capital", capital.toString());
      formData.append("risk_per_trade", riskPct.toString());
      formData.append("slippage_pips", slippage.toString());
      formData.append("commission_per_lot", commission.toString());

      const res = await api.runBacktestWithCsv(formData);
      setResult(res);
    } catch (err: any) {
      setError(err.message || "CSV Backtest execution failed");
    } finally {
      setLoading(false);
    }
  };

  const handleCompareRun = async () => {
    if (compareStrats.length < 2) {
      setError("Select at least 2 strategies to compare.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.compareStrategies({
        symbol,
        timeframe,
        compare_strategies: compareStrats,
        initial_capital: capital,
        risk_per_trade: riskPct,
        slippage_pips: slippage,
        commission_per_lot: commission,
        random_seed: seed !== "" ? Number(seed) : 42,
      });
      setComparison(res);
    } catch (err: any) {
      setError(err.message || "Comparison failed");
    } finally {
      setLoading(false);
    }
  };

  const toggleCompareStrat = (id: string) => {
    setCompareStrats((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            📊 Institutional Backtest Engine
          </h2>
          <p className="text-xs text-gray-400 mt-1">
            Zero look-ahead bias · Slippage & Commission friction · IS/OOS validation
          </p>
        </div>

        {/* Mode Selector */}
        <div className="flex bg-gray-900 p-1 rounded-lg border border-gray-800">
          <button
            onClick={() => { setMode("synthetic"); setResult(null); setComparison(null); setError(null); }}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition ${
              mode === "synthetic" ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
            }`}
          >
            🎲 Synthetic
          </button>
          <button
            onClick={() => { setMode("csv"); setResult(null); setComparison(null); setError(null); }}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition ${
              mode === "csv" ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
            }`}
          >
            📁 Historical CSV
          </button>
          <button
            onClick={() => { setMode("compare"); setResult(null); setComparison(null); setError(null); }}
            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition ${
              mode === "compare" ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
            }`}
          >
            ⚔️ Compare Strategies
          </button>
        </div>
      </div>

      {/* Control Panel */}
      <div className="bg-gray-900/90 border border-gray-800 rounded-xl p-4 space-y-4">
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          <div>
            <label className="text-[10px] text-gray-400 uppercase font-semibold">Symbol</label>
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded px-2.5 py-1 text-xs text-white mt-1"
            />
          </div>

          <div>
            <label className="text-[10px] text-gray-400 uppercase font-semibold">Timeframe</label>
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white mt-1"
            >
              {["1m", "5m", "15m", "1h", "4h", "1d"].map((tf) => (
                <option key={tf} value={tf}>{tf}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-[10px] text-gray-400 uppercase font-semibold">Capital ($)</label>
            <input
              type="number"
              value={capital}
              onChange={(e) => setCapital(Number(e.target.value))}
              className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white mt-1"
            />
          </div>

          <div>
            <label className="text-[10px] text-gray-400 uppercase font-semibold">Risk %</label>
            <input
              type="number"
              step="0.1"
              value={riskPct}
              onChange={(e) => setRiskPct(Number(e.target.value))}
              className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white mt-1"
            />
          </div>

          <div>
            <label className="text-[10px] text-gray-400 uppercase font-semibold">Slippage (Pips)</label>
            <input
              type="number"
              step="0.1"
              value={slippage}
              onChange={(e) => setSlippage(Number(e.target.value))}
              className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white mt-1"
            />
          </div>

          <div>
            <label className="text-[10px] text-gray-400 uppercase font-semibold">Commission ($/Lot)</label>
            <input
              type="number"
              step="0.5"
              value={commission}
              onChange={(e) => setCommission(Number(e.target.value))}
              className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white mt-1"
            />
          </div>

          <div>
            <label className="text-[10px] text-gray-400 uppercase font-semibold">Seed (Opt)</label>
            <input
              type="number"
              placeholder="Random"
              value={seed}
              onChange={(e) => setSeed(e.target.value === "" ? "" : Number(e.target.value))}
              className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-white mt-1"
            />
          </div>
        </div>

        {/* Strategy Selector or Multi-selector */}
        {mode !== "compare" ? (
          <div>
            <label className="text-[10px] text-gray-400 uppercase font-semibold">Target Strategy</label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-xs text-white mt-1"
            >
              {STRATEGIES.map((s) => (
                <option key={s.id} value={s.id}>{s.label}</option>
              ))}
            </select>
          </div>
        ) : (
          <div>
            <label className="text-[10px] text-gray-400 uppercase font-semibold block mb-1">
              Select Strategies to Benchmark Compare:
            </label>
            <div className="flex flex-wrap gap-2">
              {STRATEGIES.map((s) => {
                const active = compareStrats.includes(s.id);
                return (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => toggleCompareStrat(s.id)}
                    className={`px-3 py-1 text-xs rounded-md border transition ${
                      active
                        ? "bg-blue-600/30 border-blue-500 text-blue-300 font-semibold"
                        : "bg-gray-800/60 border-gray-700 text-gray-400 hover:text-white"
                    }`}
                  >
                    {active ? "✓ " : "+ "} {s.label}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* CSV File Input */}
        {mode === "csv" && (
          <div className="border border-dashed border-gray-700 rounded-lg p-3 bg-gray-950/40">
            <input
              type="file"
              accept=".csv"
              onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
              className="text-xs text-gray-300 file:mr-3 file:py-1 file:px-3 file:rounded file:border-0 file:text-xs file:bg-blue-600 file:text-white hover:file:bg-blue-500 cursor-pointer"
            />
            {csvFile && (
              <span className="text-[11px] text-emerald-400 ml-2">
                ✓ Ready: {csvFile.name} ({(csvFile.size / 1024).toFixed(1)} KB)
              </span>
            )}
          </div>
        )}

        {/* Action Button */}
        <button
          onClick={
            mode === "synthetic"
              ? handleSyntheticRun
              : mode === "csv"
              ? handleCsvRun
              : handleCompareRun
          }
          disabled={loading}
          className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-white font-bold text-xs rounded-lg transition tracking-wide shadow-lg shadow-blue-900/20"
        >
          {loading
            ? "⏳ Simulating Zero-Lookahead Backtest..."
            : mode === "compare"
            ? "⚔️ Run Multi-Strategy Comparison"
            : "▶ Execute Backtest Simulation"}
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-950/40 border border-red-800/80 rounded-xl p-3 text-red-300 text-xs">
          ❌ {error}
        </div>
      )}

      {/* Single Strategy Results */}
      {result && (
        <div className="space-y-6">
          {/* Key Metrics Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
            <MetricCard
              label="Net Profit"
              value={`$${result.metrics.net_profit.toFixed(2)}`}
              sub={`${result.metrics.net_profit_pct.toFixed(1)}%`}
              positive={result.metrics.net_profit >= 0}
            />
            <MetricCard
              label="Win Rate"
              value={`${result.metrics.win_rate.toFixed(1)}%`}
              sub={`${result.metrics.winning_trades}W / ${result.metrics.losing_trades}L`}
              positive={result.metrics.win_rate >= 50}
            />
            <MetricCard
              label="Profit Factor"
              value={result.metrics.profit_factor >= 999 ? "∞" : result.metrics.profit_factor.toFixed(2)}
              sub="Gross W/L"
              positive={result.metrics.profit_factor >= 1.5}
            />
            <MetricCard
              label="Max Drawdown"
              value={`${result.metrics.max_drawdown_pct.toFixed(1)}%`}
              sub={`$${result.metrics.max_drawdown.toFixed(2)}`}
              positive={result.metrics.max_drawdown_pct < 10}
            />
            <MetricCard
              label="Sharpe Ratio"
              value={result.metrics.sharpe_ratio.toFixed(2)}
              sub="Annualized"
              positive={result.metrics.sharpe_ratio >= 1.0}
            />
            <MetricCard
              label="Expectancy (R)"
              value={`${result.metrics.expectancy_r > 0 ? "+" : ""}${result.metrics.expectancy_r.toFixed(2)}R`}
              sub={`$${result.metrics.expectancy_usd.toFixed(1)} / trade`}
              positive={result.metrics.expectancy_r > 0}
            />
          </div>

          {/* In-Sample vs Out-of-Sample Split Comparison */}
          {result.is_metrics && result.oos_metrics && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <SplitCard title="In-Sample Split (70% Training)" metrics={result.is_metrics} />
              <SplitCard title="Out-of-Sample Split (30% Validation)" metrics={result.oos_metrics} isOOS />
            </div>
          )}

          {/* Visual SVG Equity Curve */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-xs font-bold text-gray-300 uppercase tracking-wider">
                📈 Equity Curve Progression ($)
              </h3>
              <span className="text-[11px] text-gray-500">
                {result.equity_curve.length} bars · Start: ${capital} · Final: ${result.equity_curve[result.equity_curve.length - 1]}
              </span>
            </div>
            <SvgEquityChart
              data={result.equity_curve}
              baseValue={capital}
              lineColor="#3b82f6"
            />
          </div>

          {/* Visual SVG Drawdown Curve */}
          {result.drawdown_curve && result.drawdown_curve.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-xs font-bold text-gray-300 uppercase tracking-wider">
                  📉 Underwater Drawdown Curve (%)
                </h3>
                <span className="text-[11px] text-red-400">
                  Peak DD: {result.metrics.max_drawdown_pct.toFixed(2)}%
                </span>
              </div>
              <SvgDrawdownChart data={result.drawdown_curve} />
            </div>
          )}

          {/* Trade Log Table */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <h3 className="text-xs font-bold text-gray-300 uppercase tracking-wider mb-3">
              📋 Trade Execution Journal ({result.trade_log.length} trades)
            </h3>
            {result.trade_log.length === 0 ? (
              <p className="text-xs text-gray-500">No trades executed with this strategy filter.</p>
            ) : (
              <div className="overflow-x-auto max-h-60 overflow-y-auto">
                <table className="w-full text-[11px] text-gray-300">
                  <thead className="sticky top-0 bg-gray-950 text-gray-400 uppercase font-semibold">
                    <tr className="border-b border-gray-800">
                      <th className="text-left py-2 px-2">#</th>
                      <th className="text-left py-2 px-2">Side</th>
                      <th className="text-right py-2 px-2">Entry</th>
                      <th className="text-right py-2 px-2">Exit</th>
                      <th className="text-right py-2 px-2">P/L ($)</th>
                      <th className="text-right py-2 px-2">R-Mult</th>
                      <th className="text-left py-2 px-2">Exit Trigger</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.trade_log.map((t, idx) => (
                      <tr
                        key={idx}
                        className={`border-b border-gray-800/40 hover:bg-gray-800/30 ${
                          t.pnl >= 0 ? "text-emerald-400" : "text-rose-400"
                        }`}
                      >
                        <td className="py-1.5 px-2 text-gray-500">{idx + 1}</td>
                        <td className="py-1.5 px-2 font-bold">{t.direction}</td>
                        <td className="py-1.5 px-2 text-right">{t.entry_price.toFixed(5)}</td>
                        <td className="py-1.5 px-2 text-right">{t.exit_price.toFixed(5)}</td>
                        <td className="py-1.5 px-2 text-right font-bold">
                          {t.pnl >= 0 ? "+" : ""}${t.pnl.toFixed(2)}
                        </td>
                        <td className="py-1.5 px-2 text-right">{t.r_multiple.toFixed(2)}R</td>
                        <td className="py-1.5 px-2 text-gray-400">{t.exit_reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Strategy Comparison Results */}
      {comparison && (
        <div className="space-y-6">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 overflow-x-auto">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-4">
              ⚔️ Multi-Strategy Comparative Matrix
            </h3>
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-gray-800 text-gray-400">
                  <th className="py-2 px-3">Strategy</th>
                  <th className="py-2 px-3 text-right">Net Profit</th>
                  <th className="py-2 px-3 text-right">Win Rate</th>
                  <th className="py-2 px-3 text-right">Profit Factor</th>
                  <th className="py-2 px-3 text-right">Max DD</th>
                  <th className="py-2 px-3 text-right">Sharpe</th>
                  <th className="py-2 px-3 text-right">Trades</th>
                </tr>
              </thead>
              <tbody>
                {comparison.comparisons.map((c) => (
                  <tr key={c.strategy} className="border-b border-gray-800/40 hover:bg-gray-800/30">
                    <td className="py-2.5 px-3 font-semibold text-white">{c.strategy}</td>
                    <td className={`py-2.5 px-3 text-right font-bold ${c.metrics.net_profit >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                      ${c.metrics.net_profit.toFixed(2)}
                    </td>
                    <td className="py-2.5 px-3 text-right text-gray-300">{c.metrics.win_rate.toFixed(1)}%</td>
                    <td className="py-2.5 px-3 text-right text-gray-300">{c.metrics.profit_factor.toFixed(2)}</td>
                    <td className="py-2.5 px-3 text-right text-rose-400">{c.metrics.max_drawdown_pct.toFixed(1)}%</td>
                    <td className="py-2.5 px-3 text-right text-blue-300">{c.metrics.sharpe_ratio.toFixed(2)}</td>
                    <td className="py-2.5 px-3 text-right text-gray-400">{c.metrics.total_trades}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------- Helper Components ----------------

function MetricCard({
  label,
  value,
  sub,
  positive,
}: {
  label: string;
  value: string;
  sub: string;
  positive: boolean;
}) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-3">
      <p className="text-[10px] text-gray-400 uppercase font-semibold">{label}</p>
      <p className={`text-base font-bold mt-0.5 ${positive ? "text-emerald-400" : "text-rose-400"}`}>
        {value}
      </p>
      <p className="text-[10px] text-gray-500 mt-0.5">{sub}</p>
    </div>
  );
}

function SplitCard({
  title,
  metrics,
  isOOS,
}: {
  title: string;
  metrics: BacktestMetrics;
  isOOS?: boolean;
}) {
  return (
    <div className={`border rounded-xl p-3.5 ${isOOS ? "bg-purple-950/20 border-purple-800/40" : "bg-blue-950/20 border-blue-800/40"}`}>
      <h4 className="text-xs font-bold text-gray-200 mb-2">{title}</h4>
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div>
          <span className="text-[10px] text-gray-500 block">P/L ($)</span>
          <span className={`font-bold ${metrics.net_profit >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
            ${metrics.net_profit.toFixed(2)}
          </span>
        </div>
        <div>
          <span className="text-[10px] text-gray-500 block">Win Rate</span>
          <span className="font-bold text-gray-200">{metrics.win_rate.toFixed(1)}%</span>
        </div>
        <div>
          <span className="text-[10px] text-gray-500 block">Profit Factor</span>
          <span className="font-bold text-gray-200">{metrics.profit_factor.toFixed(2)}</span>
        </div>
      </div>
    </div>
  );
}

function SvgEquityChart({
  data,
  baseValue,
  lineColor,
}: {
  data: number[];
  baseValue: number;
  lineColor: string;
}) {
  if (!data || data.length < 2) return null;
  const minVal = Math.min(...data, baseValue);
  const maxVal = Math.max(...data, baseValue);
  const range = maxVal - minVal || 1;
  const width = 800;
  const height = 180;
  const padding = 20;

  const points = data
    .map((val, idx) => {
      const x = padding + (idx / (data.length - 1)) * (width - 2 * padding);
      const y = height - padding - ((val - minVal) / range) * (height - 2 * padding);
      return `${x},${y}`;
    })
    .join(" ");

  const baseY = height - padding - ((baseValue - minVal) / range) * (height - 2 * padding);

  return (
    <div className="w-full overflow-hidden">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-44">
        <line
          x1={padding}
          y1={baseY}
          x2={width - padding}
          y2={baseY}
          stroke="#4b5563"
          strokeDasharray="4 4"
          strokeWidth="1"
        />
        <polyline
          fill="none"
          stroke={lineColor}
          strokeWidth="2.5"
          points={points}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

function SvgDrawdownChart({ data }: { data: number[] }) {
  if (!data || data.length < 2) return null;
  const maxDD = Math.max(...data, 5);
  const width = 800;
  const height = 120;
  const padding = 15;

  const points = data
    .map((val, idx) => {
      const x = padding + (idx / (data.length - 1)) * (width - 2 * padding);
      const y = padding + (val / maxDD) * (height - 2 * padding);
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div className="w-full overflow-hidden">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-28">
        <polyline
          fill="none"
          stroke="#f43f5e"
          strokeWidth="2"
          points={points}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

export default BacktestView;
