import React, { useState, useEffect } from 'react';
import { useTelemetryWebSocket } from './hooks/useTelemetryWebSocket';
import { useCockpitStore } from './store/useCockpitStore';
import { CockpitHeader } from './components/cockpit/CockpitHeader';
import { RiskRadarGauges } from './components/cockpit/RiskRadarGauges';
import { PreFlightTerminal } from './components/cockpit/PreFlightTerminal';
import { LiveEventStream } from './components/cockpit/LiveEventStream';
import { StrategyRegimePanel } from './components/cockpit/StrategyRegimePanel';
import { SweepIntelligencePanel } from './components/cockpit/SweepIntelligencePanel';

import BacktestView from './components/BacktestView';
import { FundedAccountView } from './components/FundedAccountView';
import { TradeJournalView } from './components/TradeJournalView';

import { LayoutDashboard, FlaskConical, Award, BookOpen } from 'lucide-react';

export function App() {
  const fetchSnapshot = useCockpitStore((state) => state.fetchSnapshot);
  const [activeTab, setActiveTab] = useState<'cockpit' | 'backtest' | 'funded' | 'journal'>('cockpit');

  // Activate WebSocket live stream on mount
  useTelemetryWebSocket();

  // Initial HTTP Snapshot Fetch
  useEffect(() => {
    fetchSnapshot();
  }, [fetchSnapshot]);

  return (
    <div className="min-h-screen bg-[#0d1117] text-gray-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-black">
      {/* Cockpit Top Navigation Header */}
      <CockpitHeader />

      {/* Main Terminal Tabs */}
      <div className="bg-[#161b22] border-b border-[#30363d] px-6 py-2 flex items-center space-x-2">
        <button
          onClick={() => setActiveTab('cockpit')}
          className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            activeTab === 'cockpit'
              ? 'bg-cyan-950 text-cyan-400 border border-cyan-700/60 shadow-[0_0_12px_rgba(6,182,212,0.15)]'
              : 'text-gray-400 hover:text-gray-200 hover:bg-[#21262d]'
          }`}
        >
          <LayoutDashboard className="w-3.5 h-3.5" />
          <span>Live Risk Cockpit</span>
        </button>

        <button
          onClick={() => setActiveTab('backtest')}
          className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            activeTab === 'backtest'
              ? 'bg-cyan-950 text-cyan-400 border border-cyan-700/60 shadow-[0_0_12px_rgba(6,182,212,0.15)]'
              : 'text-gray-400 hover:text-gray-200 hover:bg-[#21262d]'
          }`}
        >
          <FlaskConical className="w-3.5 h-3.5" />
          <span>Research & Backtest</span>
        </button>

        <button
          onClick={() => setActiveTab('funded')}
          className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            activeTab === 'funded'
              ? 'bg-cyan-950 text-cyan-400 border border-cyan-700/60 shadow-[0_0_12px_rgba(6,182,212,0.15)]'
              : 'text-gray-400 hover:text-gray-200 hover:bg-[#21262d]'
          }`}
        >
          <Award className="w-3.5 h-3.5" />
          <span>Funded Pass Tracker</span>
        </button>

        <button
          onClick={() => setActiveTab('journal')}
          className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            activeTab === 'journal'
              ? 'bg-cyan-950 text-cyan-400 border border-cyan-700/60 shadow-[0_0_12px_rgba(6,182,212,0.15)]'
              : 'text-gray-400 hover:text-gray-200 hover:bg-[#21262d]'
          }`}
        >
          <BookOpen className="w-3.5 h-3.5" />
          <span>Decision Journal</span>
        </button>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 p-6 max-w-[1750px] w-full mx-auto space-y-6">
        {activeTab === 'cockpit' && (
          <div className="space-y-6">
            {/* Top Critical Risk Radar Gauges */}
            <RiskRadarGauges />

            {/* Middle Split: 9-Gate Pre-Flight Terminal (Left 60%) + Sweep & Strategy Panels (Right 40%) */}
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
              <div className="xl:col-span-7">
                <PreFlightTerminal />
              </div>
              <div className="xl:col-span-5 space-y-6">
                <SweepIntelligencePanel />
                <StrategyRegimePanel />
              </div>
            </div>

            {/* Bottom Real-Time Event Audit Stream */}
            <LiveEventStream />
          </div>
        )}

        {activeTab === 'backtest' && <BacktestView />}
        {activeTab === 'funded' && <FundedAccountView />}
        {activeTab === 'journal' && <TradeJournalView />}
      </main>

      {/* Institutional Safety Banner */}
      <footer className="border-t border-[#30363d] bg-[#161b22] py-2.5 px-6 text-center text-xs text-gray-400 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block animate-pulse"></span>
          <span>DETERMINISTIC SAFETY PIPELINE: 9/9 GATES ACTIVE</span>
        </div>
        <div className="font-mono text-gray-400 text-[11px]">
          RULE #3: NO_TRADE &gt; BAD_TRADE | AI WEIGHT &le; 15% CAP
        </div>
      </footer>
    </div>
  );
}

export default App;
