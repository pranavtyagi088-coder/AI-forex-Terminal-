import React, { useState } from 'react';
import { runAnalysis, AnalysisResponse, api, WebhookAlertItem, RadarSignal } from './lib/api';
import { FundedAccountView } from './components/FundedAccountView';
import { TradeJournalView } from './components/TradeJournalView';
import { BacktestView } from './components/BacktestView';

export default function App() {
  const [activeTab, setActiveTab] = useState<'analysis' | 'journal' | 'backtest' | 'funded'>('analysis');
  const [symbol, setSymbol] = useState('EUR/USD');
  const [timeframe, setTimeframe] = useState('1h');
  const [direction, setDirection] = useState('BUY');
  const [accountBalance, setAccountBalance] = useState<number>(10000);
  const [riskPercent, setRiskPercent] = useState<number>(1.0);
  const [chartBase64, setChartBase64] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [journalSaved, setJournalSaved] = useState(false);
  const [alerts, setAlerts] = useState<WebhookAlertItem[]>([]);
  const [radarSignals, setRadarSignals] = useState<RadarSignal[]>([]);
  const [scanning, setScanning] = useState(false);

  React.useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const data = await api.getWebhookAlerts();
        setAlerts(data);
      } catch { /* silent */ }
    };
    fetchAlerts();
    const fetchRadar = async () => {
      try {
        const sigs = await api.getRadarSignals();
        setRadarSignals(sigs);
      } catch { /* silent */ }
    };
    fetchRadar();
    const radarTimer = setInterval(fetchRadar, 15000);
    const timer = setInterval(fetchAlerts, 8000);
    return () => { clearInterval(timer); clearInterval(radarTimer); };
  }, []);

  const handleApplyAlert = (alert: WebhookAlertItem) => {
    setSymbol(alert.symbol);
    setTimeframe(alert.timeframe);
    setDirection(alert.suggested_direction);
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      setError('Image size exceeds 5MB limit.');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setChartBase64(reader.result as string);
      setError(null);
    };
    reader.readAsDataURL(file);
  };

  const handleRunAnalysis = async () => {
    setLoading(true);
    setError(null);
    setJournalSaved(false);
    try {
      const payload: any = {
        symbol,
        timeframe,
        direction,
        account_balance: accountBalance,
        risk_percent: riskPercent,
        image_paths: chartBase64 ? [chartBase64] : [],
      };
      const data = await runAnalysis(payload);
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'Failed to execute analysis');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveToJournal = async () => {
    if (!result) return;
    try {
      await api.createTrade({
        symbol: result.symbol,
        timeframe: result.timeframe,
        strategyName: result.strategy_intelligence?.best_strategy_name || 'Manual Setup',
        direction: result.direction,
        positionSizeLots: result.position_sizing?.position_size_lots || 0.1,
        entryFill: result.position_sizing?.entry_price,
        stopLoss: result.position_sizing?.stop_loss,
        takeProfit: result.position_sizing?.take_profit,
        riskAmount: result.position_sizing?.risk_amount_dollars,
        rrPlanned: result.risk_reward_ratio,
        marketRegime: result.market_state?.regime,
        confidence: result.confidence,
        notes: `Setup approved via AI Forex Terminal. Score: ${result.score_total}/100`,
        result: 'OPEN',
        status: 'OPEN'
      });
      setJournalSaved(true);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans p-6">
      {/* Header */}
      <header className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center border-b border-slate-800 pb-5 mb-8">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-cyan-400 via-sky-400 to-indigo-400 bg-clip-text text-transparent">
            AI FOREX TERMINAL
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Institutional SMC Structure | ICT Liquidity Engine | Trade Journal & Backtesting
          </p>
        </div>
        <div className="flex flex-wrap gap-2 mt-4 md:mt-0 font-mono text-xs">
          <button
            onClick={() => setActiveTab('analysis')}
            className={`px-3.5 py-2 rounded-lg font-medium transition-all ${
              activeTab === 'analysis'
                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/25'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200'
            }`}
          >
            Market Analysis
          </button>
          <button
            onClick={() => setActiveTab('journal')}
            className={`px-3.5 py-2 rounded-lg font-medium transition-all ${
              activeTab === 'journal'
                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/25'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200'
            }`}
          >
            Trade Journal
          </button>
          <button
            onClick={() => setActiveTab('backtest')}
            className={`px-3.5 py-2 rounded-lg font-medium transition-all ${
              activeTab === 'backtest'
                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/25'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200'
            }`}
          >
            Backtesting Engine
          </button>
          <button
            onClick={() => setActiveTab('funded')}
            className={`px-3.5 py-2 rounded-lg font-medium transition-all ${
              activeTab === 'funded'
                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/25'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200'
            }`}
          >
            Funded Guard
          </button>
        </div>
      </header>

      {/* Dynamic Tab Body */}
      {activeTab === 'journal' ? (
        <main className="max-w-7xl mx-auto">
          <TradeJournalView />
        </main>
      ) : activeTab === 'backtest' ? (
        <main className="max-w-7xl mx-auto">
          <BacktestView />
        </main>
      ) : activeTab === 'funded' ? (
        <main className="max-w-7xl mx-auto">
          <FundedAccountView />
        </main>
      ) : (
        <main className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Controls Form Card */}
          <div className="lg:col-span-4 bg-slate-900/80 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-xl shadow-xl flex flex-col gap-5">
            <h2 className="text-xl font-bold text-slate-200 border-b border-slate-800 pb-3">
              Terminal Setup
            </h2>

            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Symbol</label>
              <input
                type="text"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Timeframe</label>
                <select
                  value={timeframe}
                  onChange={(e) => setTimeframe(e.target.value)}
                  className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:border-indigo-500"
                >
                  <option value="5m">5m</option>
                  <option value="15m">15m</option>
                  <option value="1h">1h</option>
                  <option value="4h">4h</option>
                  <option value="1d">1d</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Direction</label>
                <select
                  value={direction}
                  onChange={(e) => setDirection(e.target.value)}
                  className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:border-indigo-500"
                >
                  <option value="BUY">BUY (Long)</option>
                  <option value="SELL">SELL (Short)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Account ($)</label>
                <input
                  type="number"
                  value={accountBalance}
                  onChange={(e) => setAccountBalance(parseFloat(e.target.value) || 0)}
                  className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Risk (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={riskPercent}
                  onChange={(e) => setRiskPercent(parseFloat(e.target.value) || 0)}
                  className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Chart Screenshot</label>
              <input
                type="file"
                accept="image/png, image/jpeg, image/webp"
                onChange={handleImageUpload}
                className="w-full mt-1 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-indigo-600/20 file:text-indigo-300 hover:file:bg-indigo-600/30 text-xs text-slate-400 bg-slate-950 rounded-xl p-2 border border-slate-800"
              />
            </div>

            {error && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-400">
                {error}
              </div>
            )}

            <button
              onClick={handleRunAnalysis}
              disabled={loading}
              className="w-full mt-2 py-3 bg-gradient-to-r from-indigo-600 to-sky-600 hover:from-indigo-500 hover:to-sky-500 text-white font-semibold rounded-xl transition-all shadow-lg shadow-indigo-500/25 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                  Running Institutional Engine...
                </>
              ) : (
                'Run Institutional Analysis'
              )}
            </button>
          </div>

          {/* Result View */}
          <div className="lg:col-span-8 flex flex-col gap-6">
            {!result && !loading && (
              <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-12 text-center flex flex-col items-center justify-center min-h-[400px]">
                <div className="w-16 h-16 rounded-full bg-slate-800/80 flex items-center justify-center text-slate-500 mb-4 text-2xl font-mono">
                  [AI]
                </div>
                <h3 className="text-lg font-bold text-slate-300">Terminal Ready</h3>
                <p className="text-sm text-slate-500 max-w-sm mt-1">
                  Configure symbol parameters and click Run to calculate SMC structure, ICT liquidity, and AI confluence.
                </p>
              </div>
            )}

            {result && (
              <>
                {/* Decision Banner with Save to Journal Button */}
                <div
                  className={`p-5 rounded-2xl border backdrop-blur-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 ${
                    result.direction === 'NO_TRADE'
                      ? 'bg-rose-950/40 border-rose-500/30 text-rose-200'
                      : 'bg-emerald-950/40 border-emerald-500/30 text-emerald-200'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl font-mono">{result.direction === 'NO_TRADE' ? '[VETO]' : '[OK]'}</span>
                    <div>
                      <h3 className="text-lg font-bold tracking-tight">
                        {result.direction === 'NO_TRADE' ? 'NO-TRADE RECOMMENDED (SAFETY VETO)' : `TRADE APPROVED: ${result.direction}`}
                      </h3>
                      <p className="text-xs opacity-80">
                        Confluence Score: {result.score_total ?? 0}/100 | AI Confidence: {Math.round(result.confidence * 100)}%
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    {result.direction !== 'NO_TRADE' && (
                      <button
                        onClick={handleSaveToJournal}
                        disabled={journalSaved}
                        className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all ${
                          journalSaved ? 'bg-emerald-800 text-emerald-200' : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg'
                        }`}
                      >
                        {journalSaved ? '✓ Saved in Journal' : '+ Save Setup to Journal'}
                      </button>
                    )}
                    <div className="text-right">
                      <span className="text-xs uppercase font-semibold tracking-wider opacity-70">Calculated R:R</span>
                      <p className="text-xl font-extrabold">{result.risk_reward_ratio ? `1:${result.risk_reward_ratio}` : 'N/A'}</p>
                    </div>
                  </div>
                </div>

                {/* Veto Reasons if No-Trade */}
                {result.no_trade_reasons && result.no_trade_reasons.length > 0 && (
                  <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-xs text-rose-300">
                    <span className="font-semibold uppercase tracking-wider block mb-1">Safety Gate Triggered:</span>
                    <ul className="list-disc list-inside space-y-1">
                      {result.no_trade_reasons.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Core Cards Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* SMC Structure Card */}
                  <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5">
                    <div className="flex justify-between items-center mb-3">
                      <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">SMC Market Structure</h4>
                      <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold ${
                        result.structure?.structure_bias === 'BULLISH' ? 'bg-emerald-500/20 text-emerald-400' :
                        result.structure?.structure_bias === 'BEARISH' ? 'bg-rose-500/20 text-rose-400' :
                        'bg-amber-500/20 text-amber-400'
                      }`}>
                        {result.structure?.structure_bias || 'NEUTRAL'}
                      </span>
                    </div>
                    <div className="space-y-2 text-xs">
                      <div className="flex justify-between text-slate-300">
                        <span className="text-slate-500">Last Structure Event:</span>
                        <span className="font-mono font-bold text-indigo-400">{result.structure?.last_event || 'CONSOLIDATION'}</span>
                      </div>
                      <div className="flex justify-between text-slate-300">
                        <span className="text-slate-500">Key Swing High:</span>
                        <span className="font-mono">{result.structure?.last_swing_high ?? 'N/A'}</span>
                      </div>
                      <div className="flex justify-between text-slate-300">
                        <span className="text-slate-500">Key Swing Low:</span>
                        <span className="font-mono">{result.structure?.last_swing_low ?? 'N/A'}</span>
                      </div>
                    </div>
                  </div>

                  {/* ICT Liquidity Card */}
                  <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5">
                    <div className="flex justify-between items-center mb-3">
                      <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">ICT Liquidity & FVGs</h4>
                      <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-sky-500/20 text-sky-400">
                        {result.liquidity?.unmitigated_fvg_count ?? 0} Open FVGs
                      </span>
                    </div>
                    <div className="space-y-2 text-xs">
                      <div className="flex justify-between text-slate-300">
                        <span className="text-slate-500">Bullish / Bearish Gaps:</span>
                        <span className="font-mono text-emerald-400 font-bold">
                          +{result.liquidity?.bullish_fvg_open ?? 0} <span className="text-slate-600">/</span> <span className="text-rose-400">-{result.liquidity?.bearish_fvg_open ?? 0}</span>
                        </span>
                      </div>
                      <div className="flex justify-between text-slate-300">
                        <span className="text-slate-500">Nearest Bullish FVG:</span>
                        <span className="font-mono">
                          {result.liquidity?.nearest_bullish_fvg ? `${result.liquidity.nearest_bullish_fvg.pips} pips` : 'None'}
                        </span>
                      </div>
                      <div className="flex justify-between text-slate-300">
                        <span className="text-slate-500">Nearest Bearish FVG:</span>
                        <span className="font-mono">
                          {result.liquidity?.nearest_bearish_fvg ? `${result.liquidity.nearest_bearish_fvg.pips} pips` : 'None'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Technical State Card */}
                  <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5">
                    <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Technical State</h4>
                    <div className="space-y-2 text-xs">
                      <div className="flex justify-between text-slate-300">
                        <span className="text-slate-500">Live Price:</span>
                        <span className="font-mono font-bold text-white">{result.market_state?.current_price ?? 'N/A'}</span>
                      </div>
                      <div className="flex justify-between text-slate-300">
                        <span className="text-slate-500">Regime:</span>
                        <span className="font-mono">{result.market_state?.regime ?? 'UNKNOWN'}</span>
                      </div>
                      <div className="flex justify-between text-slate-300">
                        <span className="text-slate-500">Session:</span>
                        <span className="font-mono">{result.market_state?.active_session ?? 'UNKNOWN'}</span>
                      </div>
                      <div className="flex justify-between text-slate-300">
                        <span className="text-slate-500">ATR / RSI:</span>
                        <span className="font-mono">{result.market_state?.atr?.toFixed(5) ?? 'N/A'} (RSI: {result.market_state?.rsi?.toFixed(1) ?? 'N/A'})</span>
                      </div>
                    </div>
                  </div>

                  {/* Position Sizing Card */}
                  <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5">
                    <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Position Sizing & Risk</h4>
                    <div className="space-y-2 text-xs">
                      <div className="flex justify-between text-slate-300">
                        <span className="text-slate-500">Recommended Lots:</span>
                        <span className="font-mono font-bold text-indigo-400">{result.position_sizing?.position_size_lots ?? 'N/A'} Lots</span>
                      </div>
                      <div className="flex justify-between text-slate-300">
                        <span className="text-slate-500">Risk Amount ($):</span>
                        <span className="font-mono text-rose-400 font-bold">${result.position_sizing?.risk_amount_dollars?.toFixed(2) ?? 'N/A'}</span>
                      </div>
                      <div className="flex justify-between text-slate-300">
                        <span className="text-slate-500">SL / TP Pips:</span>
                        <span className="font-mono">{result.position_sizing?.stop_loss_pips} pips / {result.position_sizing?.take_profit_pips} pips</span>
                      </div>
                      <div className="flex justify-between text-slate-300">
                        <span className="text-slate-500">Target SL / TP Price:</span>
                        <span className="font-mono">{result.position_sizing?.stop_loss} / {result.position_sizing?.take_profit}</span>
                      </div>
                    </div>
                  </div>

                  {/* Strategy Intelligence Card */}
                  <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 md:col-span-2">
                    <div className="flex justify-between items-center mb-3">
                      <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Strategy Intelligence</h4>
                      <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold ${
                        result.strategy_intelligence?.best_strategy?.recommendation === 'BEST_MATCH' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                        result.strategy_intelligence?.best_strategy?.recommendation === 'SUITABLE' ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30' :
                        'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                      }`}>
                        {result.strategy_intelligence?.best_strategy_name || 'NO_CONFIDENT_STRATEGY'}
                      </span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
                      <div className="space-y-2">
                        <div className="flex justify-between text-slate-300">
                          <span className="text-slate-500">Strategy Match Score:</span>
                          <span className="font-mono font-bold text-indigo-400">{result.strategy_intelligence?.best_strategy_score ?? 0}/100</span>
                        </div>
                        <div className="flex justify-between text-slate-300">
                          <span className="text-slate-500">Health / Decay Status:</span>
                          <span className={`font-mono font-bold ${
                            result.strategy_intelligence?.best_strategy?.decay_status === 'ACTIVE' || result.strategy_intelligence?.best_strategy?.decay_status === 'HEALTHY' ? 'text-emerald-400' : 'text-amber-400'
                          }`}>{result.strategy_intelligence?.best_strategy?.decay_status || 'ACTIVE'}</span>
                        </div>
                        <div className="flex justify-between text-slate-300">
                          <span className="text-slate-500">Decay Score Adjustment:</span>
                          <span className="font-mono text-rose-400 font-bold">{result.strategy_intelligence?.best_strategy?.decay_adjustment ?? 0}</span>
                        </div>
                        <div className="flex justify-between text-slate-300">
                          <span className="text-slate-500">Total Strategies Evaluated:</span>
                          <span className="font-mono">{result.strategy_intelligence?.evaluated_count ?? 0}</span>
                        </div>
                      </div>

                      <div className="space-y-2 border-t md:border-t-0 md:border-l border-slate-800 pt-3 md:pt-0 md:pl-6">
                        {result.strategy_intelligence?.best_strategy?.matched_conditions && result.strategy_intelligence.best_strategy.matched_conditions.length > 0 ? (
                          <div>
                            <span className="text-slate-500 block mb-1">Matched Conditions:</span>
                            <div className="space-y-1">
                              {result.strategy_intelligence.best_strategy.matched_conditions.slice(0, 3).map((c, i) => (
                                <div key={i} className="text-emerald-400 font-mono text-[11px]">+ {c}</div>
                              ))}
                            </div>
                          </div>
                        ) : (
                          <div className="text-slate-500 font-mono text-[11px]">No conditions matched yet.</div>
                        )}
                      </div>
                    </div>

                    {result.strategy_intelligence?.strategy_ranking && result.strategy_intelligence.strategy_ranking.length > 1 && (
                      <div className="mt-4 pt-3 border-t border-slate-800/80">
                        <span className="text-slate-500 block mb-2 uppercase text-[10px] font-semibold tracking-wider">Alternative Institutional Strategies</span>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
                          {result.strategy_intelligence.strategy_ranking.slice(1, 5).map((s, i) => (
                            <div key={i} className="flex justify-between items-center bg-slate-950/40 px-3 py-1.5 rounded-lg border border-slate-850">
                              <span className="text-slate-400 font-medium">{s.name}</span>
                              <div className="flex gap-2 font-mono">
                                <span className={s.recommendation === 'REJECTED' ? 'text-rose-400/80' : 'text-emerald-400/80'}>
                                  [{s.recommendation}]
                                </span>
                                <span className="text-slate-200 font-bold">{s.final_strategy_score} pts</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* AI Multimodal Summary Card */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6">
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                    Institutional AI Multi-Timeframe Analysis
                  </h4>
                  <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">
                    {result.summary}
                  </p>
                </div>
              </>
            )}
          </div>
        </main>
      )}
    </div>
  );
}
