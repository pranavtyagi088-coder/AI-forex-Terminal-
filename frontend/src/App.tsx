import React, { useState } from 'react';
import { useTelemetryWebSocket } from './hooks/useTelemetryWebSocket';
import { CockpitHeader } from './components/cockpit/CockpitHeader';
import { RiskRadarGauges } from './components/cockpit/RiskRadarGauges';
import { PreFlightTerminal } from './components/cockpit/PreFlightTerminal';
import { LiveEventStream } from './components/cockpit/LiveEventStream';
import { StrategyRegimePanel } from './components/cockpit/StrategyRegimePanel';

import BacktestView from './components/BacktestView';
import { FundedAccountView } from './components/FundedAccountView';
import { TradeJournalView } from './components/TradeJournalView';

import { LayoutDashboard, FlaskConical, Award, BookOpen } from 'lucide-react';

export function App() {
  // Mount real-time WebSocket telemetry stream (fail-closed auto reconnect)
  useTelemetryWebSocket();

  const [activeTab, setActiveTab] = useState<'cockpit' | 'backtest' | 'funded' | 'journal'>('cockpit');

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Cockpit Header */}
      <CockpitHeader />

      {/* Tab Navigation */}
      <div className="bg-slate-900 border-b border-slate-800 px-6 flex space-x-4">
        <button
          onClick={() => setActiveTab('cockpit')}
          className={`flex items-center space-x-2 py-3 px-3 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'cockpit'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <LayoutDashboard className="w-4 h-4" />
          <span>RISK COCKPIT</span>
        </button>

        <button
          onClick={() => setActiveTab('backtest')}
          className={`flex items-center space-x-2 py-3 px-3 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'backtest'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <FlaskConical className="w-4 h-4" />
          <span>RESEARCH & BACKTEST</span>
        </button>

        <button
          onClick={() => setActiveTab('funded')}
          className={`flex items-center space-x-2 py-3 px-3 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'funded'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Award className="w-4 h-4" />
          <span>PROP FIRM HEALTH</span>
        </button>

        <button
          onClick={() => setActiveTab('journal')}
          className={`flex items-center space-x-2 py-3 px-3 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'journal'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <BookOpen className="w-4 h-4" />
          <span>TRADE JOURNAL</span>
        </button>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
        {activeTab === 'cockpit' && (
          <div className="space-y-6">
            <RiskRadarGauges />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <PreFlightTerminal />
              <StrategyRegimePanel />
            </div>
            <LiveEventStream />
          </div>
        )}

        {activeTab === 'backtest' && <BacktestView />}
        {activeTab === 'funded' && <FundedAccountView />}
        {activeTab === 'journal' && <TradeJournalView />}
      </main>
    </div>
  );
}

export default App;
