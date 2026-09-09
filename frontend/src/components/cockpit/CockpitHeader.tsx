import React, { useState } from 'react';
import { useCockpitStore } from '../../store/useCockpitStore';
import { api } from '../../lib/api';
import { ShieldAlert, ShieldCheck, Activity, Wifi, WifiOff, AlertTriangle } from 'lucide-react';

export const CockpitHeader: React.FC = () => {
  const { wsConnected, circuitBreakerTripped, circuitBreakerReason, setCircuitBreaker } = useCockpitStore();
  const [toggling, setToggling] = useState(false);

  const handleKillSwitch = async () => {
    setToggling(true);
    try {
      const nextState = !circuitBreakerTripped;
      await api.toggleCircuitBreaker(nextState, nextState ? "Cockpit Emergency Trigger" : "Cockpit Manual Reset");
      setCircuitBreaker(nextState, nextState ? "Emergency Kill Switch Activated by Trader" : undefined);
    } catch (err) {
      console.error("Kill switch toggle failed:", err);
    } finally {
      setToggling(false);
    }
  };

  return (
    <div className="bg-slate-900 border-b border-slate-800 px-6 py-4 flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center space-x-3">
        <div className="p-2 bg-indigo-500/10 rounded-lg border border-indigo-500/30">
          <Activity className="w-6 h-6 text-indigo-400" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold text-slate-100 tracking-tight">INSTITUTIONAL AI TERMINAL</h1>
            <span className="text-xs px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800 font-mono">
              v1.0-PRO
            </span>
          </div>
          <p className="text-xs text-slate-400">Deterministic • Fail-Closed • Real-Time Safety Shell</p>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {/* WS Stream Status */}
        <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium border ${
          wsConnected 
            ? 'bg-emerald-950/60 border-emerald-800 text-emerald-300'
            : 'bg-rose-950/60 border-rose-800 text-rose-300 animate-pulse'
        }`}>
          {wsConnected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
          <span>{wsConnected ? 'LIVE WS STREAM' : 'DISCONNECTED (FAIL-CLOSED)'}</span>
        </div>

        {/* Kill Switch Circuit Breaker */}
        <button
          onClick={handleKillSwitch}
          disabled={toggling}
          className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-bold text-xs uppercase tracking-wider transition-all shadow-lg ${
            circuitBreakerTripped
              ? 'bg-rose-600 hover:bg-rose-700 text-white shadow-rose-900/50 ring-2 ring-rose-400 animate-pulse'
              : 'bg-slate-800 hover:bg-rose-900/40 text-slate-300 hover:text-rose-300 border border-slate-700 hover:border-rose-600'
          }`}
        >
          {circuitBreakerTripped ? (
            <>
              <ShieldAlert className="w-4 h-4" />
              <span>KILL SWITCH ACTIVE (RESET)</span>
            </>
          ) : (
            <>
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>ENGAGE KILL SWITCH</span>
            </>
          )}
        </button>
      </div>

      {circuitBreakerTripped && (
        <div className="w-full bg-rose-950/80 border border-rose-600 text-rose-200 px-4 py-2 rounded-lg flex items-center space-x-3 text-xs">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
          <span><strong>CIRCUIT BREAKER ENGAGED:</strong> {circuitBreakerReason || 'All order routing strictly vetoed under Fail-Closed Protocol.'}</span>
        </div>
      )}
    </div>
  );
};
