import React, { useState, useEffect } from 'react';
import { api, TradeJournalItem } from '../lib/api';

export function TradeJournalView() {
  const [trades, setTrades] = useState<TradeJournalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [symbolFilter, setSymbolFilter] = useState('');
  const [resultFilter, setResultFilter] = useState('');
  const [showLogModal, setShowLogModal] = useState(false);

  // New trade form state
  const [newSymbol, setNewSymbol] = useState('EUR/USD');
  const [newDirection, setNewDirection] = useState('BUY');
  const [newStrategy, setNewStrategy] = useState('Liquidity Sweep Continuation');
  const [newLots, setNewLots] = useState(0.5);
  const [newEntry, setNewEntry] = useState(1.0850);
  const [newSL, setNewSL] = useState(1.0820);
  const [newTP, setNewTP] = useState(1.0910);
  const [newPnl, setNewPnl] = useState(0);
  const [newResult, setNewResult] = useState('WIN');
  const [newNotes, setNewNotes] = useState('');

  const loadTrades = async () => {
    setLoading(true);
    try {
      const filter: any = {};
      if (symbolFilter) filter.symbol = symbolFilter;
      if (resultFilter) filter.result = resultFilter;
      const data = await api.getTrades(filter);
      setTrades(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTrades();
  }, [symbolFilter, resultFilter]);

  const handleCreateTrade = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const r = (newResult === 'WIN' ? 2.0 : (newResult === 'LOSS' ? -1.0 : 0.0));
      await api.createTrade({
        symbol: newSymbol,
        timeframe: '1h',
        direction: newDirection,
        strategyName: newStrategy,
        positionSizeLots: Number(newLots),
        entryFill: Number(newEntry),
        stopLoss: Number(newSL),
        takeProfit: Number(newTP),
        pnl: Number(newPnl),
        realizedR: r,
        result: newResult,
        status: newResult === 'OPEN' ? 'OPEN' : 'CLOSED',
        notes: newNotes,
      });
      setShowLogModal(false);
      loadTrades();
    } catch (err) {
      console.error(err);
    }
  };

  const totalPnl = trades.reduce((acc, t) => acc + (t.pnl || 0), 0);
  const wins = trades.filter(t => t.result === 'WIN').length;
  const closed = trades.filter(t => t.result !== 'OPEN').length;
  const winRate = closed > 0 ? ((wins / closed) * 100).toFixed(1) : '0.0';

  return (
    <div className="flex flex-col gap-6">
      {/* Header & Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl">
          <span className="text-xs font-mono text-slate-400 uppercase">Total Logged Trades</span>
          <div className="text-2xl font-black font-mono text-white mt-1">{trades.length}</div>
        </div>
        <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl">
          <span className="text-xs font-mono text-slate-400 uppercase">Win Rate (Closed)</span>
          <div className="text-2xl font-black font-mono text-emerald-400 mt-1">{winRate}%</div>
        </div>
        <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl">
          <span className="text-xs font-mono text-slate-400 uppercase">Total Realized P/L</span>
          <div className={`text-2xl font-black font-mono mt-1 ${totalPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            ${totalPnl.toFixed(2)}
          </div>
        </div>
        <div className="flex items-center justify-end">
          <button
            onClick={() => setShowLogModal(true)}
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl transition-all shadow-lg shadow-indigo-500/25 text-sm"
          >
            + Log New Trade
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl flex flex-wrap gap-4 items-center justify-between">
        <div className="flex gap-3">
          <input
            type="text"
            placeholder="Filter Pair (e.g. EUR/USD)..."
            value={symbolFilter}
            onChange={(e) => setSymbolFilter(e.target.value.toUpperCase())}
            className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
          />
          <select
            value={resultFilter}
            onChange={(e) => setResultFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
          >
            <option value="">All Results</option>
            <option value="WIN">WIN</option>
            <option value="LOSS">LOSS</option>
            <option value="BREAKEVEN">BREAKEVEN</option>
            <option value="OPEN">OPEN</option>
          </select>
        </div>
        <div className="text-xs text-slate-500 font-mono">
          Showing {trades.length} recorded entries
        </div>
      </div>

      {/* Trade Journal Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-950 border-b border-slate-800 text-slate-400 uppercase text-[10px] tracking-wider">
              <tr>
                <th className="py-3 px-4">Date</th>
                <th className="py-3 px-4">Pair</th>
                <th className="py-3 px-4">Strategy</th>
                <th className="py-3 px-4">Direction</th>
                <th className="py-3 px-4">Entry</th>
                <th className="py-3 px-4">SL / TP</th>
                <th className="py-3 px-4">Lots</th>
                <th className="py-3 px-4">Result</th>
                <th className="py-3 px-4">R-Mult</th>
                <th className="py-3 px-4 text-right">P/L ($)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading ? (
                <tr>
                  <td colSpan={10} className="py-8 text-center text-slate-500">Loading Journal Database...</td>
                </tr>
              ) : trades.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-8 text-center text-slate-500">No journaled trades found. Click '+ Log New Trade' or approve an analysis setup.</td>
                </tr>
              ) : (
                trades.map((t) => (
                  <tr key={t.id} className="hover:bg-slate-850/40 transition-colors">
                    <td className="py-3 px-4 text-slate-400">{t.openedAt ? new Date(t.openedAt).toLocaleDateString() : 'N/A'}</td>
                    <td className="py-3 px-4 font-bold text-white">{t.symbol}</td>
                    <td className="py-3 px-4 text-indigo-300 truncate max-w-[150px]">{t.strategyName || 'Manual Setup'}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded font-bold ${t.direction === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                        {t.direction}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-300">{t.entryFill ?? 'N/A'}</td>
                    <td className="py-3 px-4 text-slate-400">{t.stopLoss ?? 'N/A'} / {t.takeProfit ?? 'N/A'}</td>
                    <td className="py-3 px-4 text-slate-300">{t.positionSizeLots}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        t.result === 'WIN' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' :
                        t.result === 'LOSS' ? 'bg-rose-950 text-rose-400 border border-rose-800' :
                        'bg-slate-800 text-slate-300'
                      }`}>
                        {t.result || 'OPEN'}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-bold text-slate-200">{t.realizedR ? `${t.realizedR > 0 ? '+' : ''}${t.realizedR}R` : '-'}</td>
                    <td className={`py-3 px-4 text-right font-bold ${t.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      ${t.pnl?.toFixed(2) ?? '0.00'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Log Trade Modal */}
      {showLogModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3 mb-4">
              <h3 className="text-lg font-bold text-white">Manual Trade Log</h3>
              <button onClick={() => setShowLogModal(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>
            <form onSubmit={handleCreateTrade} className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Symbol</label>
                  <input type="text" value={newSymbol} onChange={e => setNewSymbol(e.target.value.toUpperCase())} className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-white" />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Direction</label>
                  <select value={newDirection} onChange={e => setNewDirection(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-white">
                    <option value="BUY">BUY</option>
                    <option value="SELL">SELL</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Strategy Name</label>
                <input type="text" value={newStrategy} onChange={e => setNewStrategy(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-white" />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Lots</label>
                  <input type="number" step="0.01" value={newLots} onChange={e => setNewLots(parseFloat(e.target.value))} className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-white" />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Entry Price</label>
                  <input type="number" step="0.0001" value={newEntry} onChange={e => setNewEntry(parseFloat(e.target.value))} className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-white" />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Result</label>
                  <select value={newResult} onChange={e => setNewResult(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-white">
                    <option value="WIN">WIN</option>
                    <option value="LOSS">LOSS</option>
                    <option value="BREAKEVEN">BREAKEVEN</option>
                    <option value="OPEN">OPEN</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Stop Loss</label>
                  <input type="number" step="0.0001" value={newSL} onChange={e => setNewSL(parseFloat(e.target.value))} className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-white" />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Take Profit</label>
                  <input type="number" step="0.0001" value={newTP} onChange={e => setNewTP(parseFloat(e.target.value))} className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-white" />
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Realized P/L ($)</label>
                <input type="number" step="0.1" value={newPnl} onChange={e => setNewPnl(parseFloat(e.target.value))} className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-white" />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowLogModal(false)} className="px-4 py-2 bg-slate-800 text-slate-300 rounded hover:bg-slate-700">Cancel</button>
                <button type="submit" className="px-4 py-2 bg-indigo-600 text-white font-bold rounded hover:bg-indigo-500">Save Entry</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
