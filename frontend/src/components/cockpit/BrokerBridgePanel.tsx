import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Landmark, CheckCircle2, XCircle, AlertTriangle, Zap, Activity, Loader2 } from 'lucide-react';
import { api } from '../../lib/api';
import { useCockpitStore } from '../../store/useCockpitStore';

function generateIdempotencyKey(): string {
  return 'ik-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
}

function formatCurrency(v: number | undefined | null): string {
  if (v === undefined || v === null || Number.isNaN(v)) return 'UNAVAILABLE';
  return '$' + v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function BrokerBridgePanel() {
  const queryClient = useQueryClient();
  const circuitBreakerTripped = useCockpitStore((s) => s.circuitBreakerTripped);
  const [showEmergencyConfirm, setShowEmergencyConfirm] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [lastActionMsg, setLastActionMsg] = useState<string | null>(null);

  // ===== Live account =====
  const accountQuery = useQuery({
    queryKey: ['broker', 'account'],
    queryFn: () => api.getBrokerAccount(),
    refetchInterval: 5000,
    retry: 1,
  });

  // ===== Live positions =====
  const positionsQuery = useQuery({
    queryKey: ['broker', 'positions'],
    queryFn: () => api.getBrokerPositions(),
    refetchInterval: 5000,
    retry: 1,
  });

  // ===== Pending proposals =====
  const proposalsQuery = useQuery({
    queryKey: ['broker', 'proposals'],
    queryFn: () => api.listProposals(),
    refetchInterval: 4000,
    retry: 1,
  });

  const pendingProposals = useMemo(() => {
    const list = proposalsQuery.data?.proposals || [];
    return list.filter((p: any) => p.status === 'APPROVED' || p.status === 'STAGED' || p.status === 'PENDING');
  }, [proposalsQuery.data]);

  // ===== Approve mutation =====
  const approveMutation = useMutation({
    mutationFn: (proposalId: string) =>
      api.approveProposal(proposalId, generateIdempotencyKey(), 'LIVE'),
    onSuccess: (data) => {
      setLastActionMsg('Proposal dispatched: ' + (data?.broker_ticket || data?.trade_id || 'OK'));
      setActionError(null);
      queryClient.invalidateQueries({ queryKey: ['broker'] });
    },
    onError: (e: any) => {
      setActionError('Approve failed: ' + (e?.message || 'unknown error'));
      setLastActionMsg(null);
    },
  });

  // ===== Reject mutation =====
  const rejectMutation = useMutation({
    mutationFn: (proposalId: string) => api.rejectProposal(proposalId),
    onSuccess: () => {
      setLastActionMsg('Proposal rejected (human veto)');
      setActionError(null);
      queryClient.invalidateQueries({ queryKey: ['broker', 'proposals'] });
    },
    onError: (e: any) => setActionError('Reject failed: ' + (e?.message || 'unknown error')),
  });

  // ===== Emergency close mutation =====
  const emergencyMutation = useMutation({
    mutationFn: () => api.emergencyCloseAll('MANUAL_EMERGENCY_LIQUIDATION'),
    onSuccess: async (data) => {
      setLastActionMsg('EMERGENCY: liquidated ' + (data?.count ?? 0) + ' positions. Tripping Kill Switch...');
      setActionError(null);
      try {
        await api.toggleCircuitBreaker(true, 'EMERGENCY_LIQUIDATION_TRIGGERED');
      } catch (e: any) {
        setActionError('Positions closed but kill switch trip failed: ' + (e?.message || ''));
      }
      queryClient.invalidateQueries({ queryKey: ['broker'] });
      setShowEmergencyConfirm(false);
    },
    onError: (e: any) => {
      setActionError('EMERGENCY failed: ' + (e?.message || 'unknown'));
      setShowEmergencyConfirm(false);
    },
  });

  const account = accountQuery.data;
  const isConnected = account?.is_connected === true;
  const latencyMs = account?.latency_ms ?? 0;
  const isHighLatency = latencyMs > 500;
  const positions = positionsQuery.data?.positions || [];
  const totalOpen = positionsQuery.data?.total_open || 0;

  const disableActions = circuitBreakerTripped || !isConnected;

  return (
    <div
      data-testid="broker-bridge-panel"
      className="bg-[#0d1117] border border-[#30363d] rounded-lg p-4 shadow-lg"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Landmark className="w-5 h-5 text-cyan-400" />
          <h3 className="text-sm font-bold text-gray-100 tracking-wide">
            INSTITUTIONAL BROKER BRIDGE
          </h3>
        </div>
        <div className="flex items-center space-x-3 text-xs">
          {accountQuery.isLoading ? (
            <span className="flex items-center text-gray-400">
              <Loader2 className="w-3 h-3 mr-1 animate-spin" /> loading...
            </span>
          ) : isConnected ? (
            <>
              <span className="flex items-center text-green-400">
                <div className="w-2 h-2 rounded-full bg-green-400 mr-1.5 animate-pulse" />
                CONNECTED
              </span>
              <span className={'flex items-center ' + (isHighLatency ? 'text-red-400' : 'text-gray-300')}>
                <Zap className="w-3 h-3 mr-1" />
                {latencyMs.toFixed(0)}ms {isHighLatency && '⚠️ HIGH'}
              </span>
            </>
          ) : (
            <span className="text-red-400 font-semibold">DISCONNECTED</span>
          )}
        </div>
      </div>

      {/* Account Info Grid */}
      <div className="grid grid-cols-4 gap-3 mb-4 p-3 bg-[#161b22] rounded border border-[#30363d]">
        <div>
          <div className="text-[10px] text-gray-500 uppercase">Account</div>
          <div className="text-xs text-gray-200 font-mono">{account?.account_id ?? 'UNAVAILABLE'}</div>
        </div>
        <div>
          <div className="text-[10px] text-gray-500 uppercase">Balance</div>
          <div className="text-sm text-cyan-300 font-semibold">{formatCurrency(account?.balance)}</div>
        </div>
        <div>
          <div className="text-[10px] text-gray-500 uppercase">Equity</div>
          <div className="text-sm text-green-300 font-semibold">{formatCurrency(account?.equity)}</div>
        </div>
        <div>
          <div className="text-[10px] text-gray-500 uppercase">Free Margin</div>
          <div className="text-sm text-gray-200 font-semibold">{formatCurrency(account?.free_margin)}</div>
        </div>
      </div>

      {/* Approval Queue */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider">
            📋 Approval Queue
          </h4>
          <span className="text-xs text-gray-500">{pendingProposals.length} pending</span>
        </div>
        {pendingProposals.length === 0 ? (
          <div className="text-xs text-gray-500 italic p-3 bg-[#161b22] rounded border border-[#30363d]">
            No pending proposals. Stage an order via Pre-Flight to see approval requests here.
          </div>
        ) : (
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {pendingProposals.map((p: any) => (
              <div
                key={p.proposal_id}
                data-testid={'proposal-row-' + p.proposal_id}
                className="p-2 bg-[#161b22] border border-[#30363d] rounded flex items-center justify-between text-xs"
              >
                <div className="flex-1">
                  <span className="font-mono text-cyan-400">#{String(p.proposal_id).slice(-6)}</span>
                  <span className="ml-2 text-gray-200 font-semibold">{p.symbol}</span>
                  <span
                    className={
                      'ml-2 px-1.5 py-0.5 rounded text-[10px] font-bold ' +
                      (p.direction === 'BUY' ? 'bg-green-950 text-green-400' : 'bg-red-950 text-red-400')
                    }
                  >
                    {p.direction}
                  </span>
                  <span className="ml-2 text-gray-400">
                    {p.position_size_lots ?? '?'} lots @ {p.entry_price}
                  </span>
                  <span className="ml-2 text-gray-500">SL: {p.stop_loss}</span>
                </div>
                <div className="flex space-x-1">
                  <button
                    data-testid={'approve-btn-' + p.proposal_id}
                    onClick={() => approveMutation.mutate(p.proposal_id)}
                    disabled={disableActions || approveMutation.isPending}
                    className="px-2 py-1 bg-green-900/40 hover:bg-green-800/60 disabled:bg-gray-800 disabled:text-gray-600 text-green-300 rounded flex items-center"
                  >
                    <CheckCircle2 className="w-3 h-3 mr-1" /> Approve
                  </button>
                  <button
                    data-testid={'reject-btn-' + p.proposal_id}
                    onClick={() => rejectMutation.mutate(p.proposal_id)}
                    disabled={rejectMutation.isPending}
                    className="px-2 py-1 bg-red-900/40 hover:bg-red-800/60 disabled:bg-gray-800 text-red-300 rounded flex items-center"
                  >
                    <XCircle className="w-3 h-3 mr-1" /> Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Positions */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider">💼 Live Broker Positions</h4>
          <span className="text-xs text-gray-500">{totalOpen} open</span>
        </div>
        {positions.length === 0 ? (
          <div className="text-xs text-gray-500 italic p-3 bg-[#161b22] rounded border border-[#30363d]">
            No open positions.
          </div>
        ) : (
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {positions.map((pos: any) => (
              <div
                key={pos.ticket}
                className="p-2 bg-[#161b22] border border-[#30363d] rounded flex items-center justify-between text-xs font-mono"
              >
                <span className="text-gray-300">
                  <span className="text-cyan-400">#{String(pos.ticket).slice(-6)}</span>
                  <span className="ml-2">{pos.symbol}</span>
                  <span className={'ml-2 ' + (pos.direction === 'BUY' ? 'text-green-400' : 'text-red-400')}>
                    {pos.direction}
                  </span>
                  <span className="ml-2 text-gray-400">{pos.volume} lots</span>
                </span>
                <span className={(pos.unrealized_pnl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}>
                  {formatCurrency(pos.unrealized_pnl)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Emergency Section */}
      <div className="border-t border-[#30363d] pt-3">
        {!showEmergencyConfirm ? (
          <button
            data-testid="emergency-close-btn"
            onClick={() => setShowEmergencyConfirm(true)}
            disabled={!isConnected}
            className="w-full py-2 bg-red-950/50 hover:bg-red-900/60 disabled:bg-gray-900 disabled:text-gray-600 border border-red-800 text-red-300 font-bold text-xs rounded flex items-center justify-center"
          >
            <AlertTriangle className="w-4 h-4 mr-2" />
            🚨 EMERGENCY LIQUIDATE ALL POSITIONS
          </button>
        ) : (
          <div className="p-3 bg-red-950/30 border border-red-800 rounded space-y-2">
            <div className="text-xs text-red-300 font-bold flex items-center">
              <AlertTriangle className="w-4 h-4 mr-1" /> CONFIRM EMERGENCY LIQUIDATION
            </div>
            <div className="text-[11px] text-gray-300">
              This will close ALL {totalOpen} open positions AND trip the Kill Switch. Trader must manually reset.
            </div>
            <div className="flex space-x-2">
              <button
                data-testid="emergency-confirm-btn"
                onClick={() => emergencyMutation.mutate()}
                disabled={emergencyMutation.isPending}
                className="flex-1 py-1.5 bg-red-800 hover:bg-red-700 text-white font-bold text-xs rounded"
              >
                {emergencyMutation.isPending ? 'LIQUIDATING...' : 'CONFIRM LIQUIDATE ALL'}
              </button>
              <button
                data-testid="emergency-cancel-btn"
                onClick={() => setShowEmergencyConfirm(false)}
                className="flex-1 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs rounded"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Action Feedback */}
      {actionError && (
        <div
          data-testid="broker-action-error"
          className="mt-3 p-2 bg-red-950/40 border border-red-800 rounded text-xs text-red-300"
        >
          {actionError}
        </div>
      )}
      {lastActionMsg && !actionError && (
        <div
          data-testid="broker-action-success"
          className="mt-3 p-2 bg-green-950/40 border border-green-800 rounded text-xs text-green-300 flex items-center"
        >
          <Activity className="w-3 h-3 mr-1.5" /> {lastActionMsg}
        </div>
      )}

      {circuitBreakerTripped && (
        <div className="mt-3 p-2 bg-yellow-950/40 border border-yellow-800 rounded text-xs text-yellow-300 font-semibold">
          ⚠️ Kill Switch is ACTIVE. All approval actions are locked.
        </div>
      )}
    </div>
  );
}

export default BrokerBridgePanel;
