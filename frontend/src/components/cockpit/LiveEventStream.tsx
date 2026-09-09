import React, { useState, useRef, useEffect } from 'react';
import { useCockpitStore } from '../../store/useCockpitStore';
import { TerminalEvent, EventSeverity } from '../../types/telemetry';
import { Terminal, Filter, Trash2, Pause, Play } from 'lucide-react';

export const LiveEventStream: React.FC = () => {
  const { events, setEvents, wsConnected } = useCockpitStore();
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');
  const [isPaused, setIsPaused] = useState<boolean>(false);

  const streamEndRef = useRef<HTMLDivElement>(null);

  const filtered = events.filter((e) => {
    if (filterSeverity === 'ALL') return true;
    return e.severity === filterSeverity;
  });

  useEffect(() => {
    if (!isPaused) {
      streamEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events, isPaused]);

  const getSeverityBadge = (sev: EventSeverity) => {
    switch (sev) {
      case 'CRITICAL':
      case 'EMERGENCY':
        return 'bg-rose-950 text-rose-300 border-rose-800';
      case 'ERROR':
        return 'bg-rose-900/60 text-rose-200 border-rose-700';
      case 'WARN':
      case 'WARNING':
        return 'bg-amber-950 text-amber-300 border-amber-800';
      case 'INFO':
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center space-x-2">
          <Terminal className="w-4 h-4 text-indigo-400" />
          <h2 className="text-sm font-semibold text-slate-200">
            CRYPTOGRAPHIC AUDIT & TELEMETRY STREAM
          </h2>
          <span className={`text-[10px] px-2 py-0.5 rounded border font-mono ${
            wsConnected ? 'bg-emerald-950 text-emerald-300 border-emerald-800' : 'bg-rose-950 text-rose-300 border-rose-800'
          }`}>
            {wsConnected ? 'STREAMING' : 'OFFLINE'}
          </span>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={`flex items-center space-x-1 px-2.5 py-1 text-xs rounded border transition-colors ${
              isPaused ? 'bg-amber-950 border-amber-800 text-amber-300' : 'bg-slate-800 border-slate-700 text-slate-300'
            }`}
          >
            {isPaused ? <Play className="w-3 h-3" /> : <Pause className="w-3 h-3" />}
            <span>{isPaused ? 'RESUME' : 'PAUSE'}</span>
          </button>

          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-300"
          >
            <option value="ALL">All Severities ({events.length})</option>
            <option value="CRITICAL">Critical Only</option>
            <option value="WARN">Warnings Only</option>
            <option value="INFO">Info Only</option>
          </select>

          <button
            onClick={() => setEvents([])}
            className="p-1 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded"
            title="Clear Event Log"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div className="h-64 overflow-y-auto bg-slate-950 rounded-lg p-3 border border-slate-800 font-mono text-xs space-y-2">
        {filtered.length === 0 ? (
          <div className="text-slate-500 text-center py-8">Listening to real-time WebSocket event stream...</div>
        ) : (
          filtered.map((evt: TerminalEvent, idx: number) => (
            <div key={evt.event_id || idx} className="flex items-start space-x-2 border-b border-slate-900 pb-1.5">
              <span className="text-slate-500 text-[11px] shrink-0">
                {new Date(evt.timestamp * 1000).toLocaleTimeString()}
              </span>
              <span className={`px-1.5 py-0.2 rounded text-[10px] border shrink-0 ${getSeverityBadge(evt.severity)}`}>
                {evt.severity}
              </span>
              <span className="text-indigo-400 shrink-0">[{evt.source}]</span>
              <span className="text-slate-300 break-all">{evt.message}</span>
            </div>
          ))
        )}
        <div ref={streamEndRef} />
      </div>
    </div>
  );
};
