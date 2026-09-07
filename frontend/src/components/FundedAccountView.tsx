import React, { useState, useEffect } from "react";
import { api, PropFirmPreset } from "../lib/api";

export function FundedAccountView() {
  const [presets, setPresets] = useState<PropFirmPreset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string>("ftmo_normal");
  const [balance, setBalance] = useState<number>(100000);
  const [dailyLoss, setDailyLoss] = useState<number>(850);
  const [totalLoss, setTotalLoss] = useState<number>(1800);

  // Pre-trade test state
  const [pair, setPair] = useState("EUR/USD");
  const [lots, setLots] = useState(1.0);
  const [slPips, setSlPips] = useState(20);
  const [complianceResult, setComplianceResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadPresets = async () => {
      try {
        const data = await api.getPropPresets();
        setPresets(data);
      } catch { /* silent */ }
    };
    loadPresets();
  }, []);

  const activeProfile = presets.find((p) => p.id === selectedPreset) || {
    id: "ftmo_normal",
    name: "FTMO Standard 2-Step",
    daily_drawdown_pct: 5.0,
    max_drawdown_pct: 10.0,
    allow_news_trading: false,
    news_blackout_minutes: 2,
    allow_weekend_holding: false,
  };

  const dailyLimitUsd = (balance * activeProfile.daily_drawdown_pct) / 100;
  const maxLimitUsd = (balance * activeProfile.max_drawdown_pct) / 100;
  const dailyRemaining = Math.max(0, dailyLimitUsd - dailyLoss);
  const totalRemaining = Math.max(0, maxLimitUsd - totalLoss);

  const handleCheckTrade = async () => {
    setLoading(true);
    setComplianceResult(null);
    try {
      const res = await api.checkPropCompliance({
        pair,
        order_type: "BUY",
        lot_size: lots,
        stop_loss_pips: slPips,
        entry_price: 1.0850,
      });
      setComplianceResult(res);
    } catch {
      // Fallback local calculation
      const riskUsd = lots * 10 * slPips;
      const allowed = riskUsd <= dailyRemaining && riskUsd <= totalRemaining;
      setComplianceResult({
        allowed,
        risk_amount_usd: riskUsd,
        risk_pct: Number(((riskUsd / balance) * 100).toFixed(2)),
        violations: allowed ? [] : ["EXCEEDS_DAILY_LOSS_LIMIT"],
        warnings: riskUsd > 2000 ? ["HIGH_TRADE_RISK_PERCENTAGE"] : [],
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with Preset Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-800 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            🛡️ Funded Account Protection Gate
          </h2>
          <p className="text-xs text-gray-400 mt-1">
            Real-time compliance checks · Daily loss guard · News blackout gate
          </p>
        </div>

        {/* Preset Selector */}
        <div className="flex items-center gap-2 bg-gray-900 border border-gray-800 rounded-lg p-1.5">
          <span className="text-[10px] text-gray-400 font-semibold uppercase px-2">Firm Preset:</span>
          <select
            value={selectedPreset}
            onChange={(e) => setSelectedPreset(e.target.value)}
            className="bg-gray-800 text-xs text-white rounded px-3 py-1 border border-gray-700 font-semibold"
          >
            {presets.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Rules & Status Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-3.5">
          <span className="text-[10px] text-gray-400 uppercase font-semibold">Daily Loss Limit</span>
          <p className="text-base font-bold text-rose-400 mt-0.5">
            ${dailyRemaining.toFixed(0)} <span className="text-xs text-gray-500 font-normal">/ ${dailyLimitUsd.toFixed(0)}</span>
          </p>
          <span className="text-[10px] text-gray-500">{activeProfile.daily_drawdown_pct}% Max Daily</span>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-3.5">
          <span className="text-[10px] text-gray-400 uppercase font-semibold">Total Max Drawdown</span>
          <p className="text-base font-bold text-rose-400 mt-0.5">
            ${totalRemaining.toFixed(0)} <span className="text-xs text-gray-500 font-normal">/ ${maxLimitUsd.toFixed(0)}</span>
          </p>
          <span className="text-[10px] text-gray-500">{activeProfile.max_drawdown_pct}% Max Total</span>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-3.5">
          <span className="text-[10px] text-gray-400 uppercase font-semibold">News Trading</span>
          <p className={`text-base font-bold mt-0.5 ${activeProfile.allow_news_trading ? "text-emerald-400" : "text-amber-400"}`}>
            {activeProfile.allow_news_trading ? "Allowed" : `±${activeProfile.news_blackout_minutes}m Blackout`}
          </p>
          <span className="text-[10px] text-gray-500">{activeProfile.allow_news_trading ? "No Restrictions" : "Red-Folder Guard Active"}</span>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-3.5">
          <span className="text-[10px] text-gray-400 uppercase font-semibold">Weekend Holding</span>
          <p className={`text-base font-bold mt-0.5 ${activeProfile.allow_weekend_holding ? "text-emerald-400" : "text-rose-400"}`}>
            {activeProfile.allow_weekend_holding ? "Permitted" : "Prohibited"}
          </p>
          <span className="text-[10px] text-gray-500">{activeProfile.allow_weekend_holding ? "Swing Approved" : "Close Friday <20:00 UTC"}</span>
        </div>
      </div>

      {/* Pre-Trade Compliance Simulation Form */}
      <div className="bg-gray-900/90 border border-gray-800 rounded-xl p-4 space-y-4">
        <h3 className="text-xs font-bold text-gray-200 uppercase tracking-wider">
          🔍 Pre-Trade Rule Compliance Simulator
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div>
            <label className="text-[10px] text-gray-400 uppercase font-semibold">Pair</label>
            <input
              type="text"
              value={pair}
              onChange={(e) => setPair(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded px-2.5 py-1 text-xs text-white mt-1"
            />
          </div>
          <div>
            <label className="text-[10px] text-gray-400 uppercase font-semibold">Position Size (Lots)</label>
            <input
              type="number"
              step="0.1"
              value={lots}
              onChange={(e) => setLots(Number(e.target.value))}
              className="w-full bg-gray-800 border border-gray-700 rounded px-2.5 py-1 text-xs text-white mt-1"
            />
          </div>
          <div>
            <label className="text-[10px] text-gray-400 uppercase font-semibold">Stop Loss (Pips)</label>
            <input
              type="number"
              value={slPips}
              onChange={(e) => setSlPips(Number(e.target.value))}
              className="w-full bg-gray-800 border border-gray-700 rounded px-2.5 py-1 text-xs text-white mt-1"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={handleCheckTrade}
              disabled={loading}
              className="w-full py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-white font-bold text-xs rounded transition"
            >
              {loading ? "Evaluating..." : "Check Compliance"}
            </button>
          </div>
        </div>

        {/* Compliance Result Banner */}
        {complianceResult && (
          <div
            className={`border rounded-xl p-3.5 ${
              complianceResult.allowed
                ? "bg-emerald-950/30 border-emerald-800/60 text-emerald-300"
                : "bg-rose-950/30 border-rose-800/60 text-rose-300"
            }`}
          >
            <div className="flex items-center gap-2 font-bold text-sm">
              <span>{complianceResult.allowed ? "✅ TRADE APPROVED (COMPLIANT)" : "🚫 TRADE REJECTED (RULE BREACH)"}</span>
            </div>
            <p className="text-xs mt-1 text-gray-300">
              Projected Risk: <strong>${complianceResult.risk_amount_usd}</strong> ({complianceResult.risk_pct}% of starting balance).
            </p>
            {complianceResult.violations && complianceResult.violations.length > 0 && (
              <ul className="text-xs text-rose-400 list-disc list-inside mt-2 font-semibold">
                {complianceResult.violations.map((v: string, i: number) => (
                  <li key={i}>{v}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default FundedAccountView;
