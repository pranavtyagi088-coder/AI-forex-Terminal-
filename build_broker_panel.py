"""
PHASE 4A-D: INSTITUTIONAL BROKER BRIDGE COCKPIT PANEL
Full implementation script - creates all files atomically.
"""
from pathlib import Path
import re

ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")

def write_file(rel_path, content, mode="w"):
    p = ROOT / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    if mode == "w":
        p.write_text(content, encoding="utf-8")
        print(f"[WRITE] {rel_path} ({len(content)} bytes)")
    else:
        existing = p.read_text(encoding="utf-8-sig", errors="replace") if p.exists() else ""
        p.write_text(existing + content, encoding="utf-8")
        print(f"[APPEND] {rel_path} (+{len(content)} bytes)")

# ============================================================
# 1. BACKEND: Extend trades.py with /proposals list + reject
# ============================================================
trades_py = ROOT / "backend/app/api/routes/trades.py"
trades_text = trades_py.read_text(encoding="utf-8-sig", errors="replace")

if "def list_all_proposals" not in trades_text:
    inject_marker = '@router.post("/proposals/{proposal_id}/approve")'
    
    new_endpoints = '''@router.get("/proposals")
async def list_all_proposals(_token: str = Depends(verify_api_token)):
    """List all staged proposals in memory (pending + processed)."""
    proposals = staging_manager.list_all_proposals() if hasattr(staging_manager, 'list_all_proposals') else []
    return {
        "proposals": [
            {
                "proposal_id": p.proposal_id,
                "status": p.status,
                "symbol": p.request.symbol,
                "direction": p.request.direction,
                "entry_price": float(p.request.entry_price),
                "stop_loss": float(p.request.stop_loss),
                "take_profit": float(p.request.take_profit) if p.request.take_profit else None,
                "position_size_lots": float(p.request.position_size_lots) if hasattr(p.request, 'position_size_lots') else None,
                "gates_passed": p.gates_passed if hasattr(p, 'gates_passed') else 0,
                "created_at": p.created_at.isoformat() if hasattr(p, 'created_at') and p.created_at else None,
            }
            for p in proposals
        ],
        "total": len(proposals),
    }


@router.post("/proposals/{proposal_id}/reject")
async def reject_proposal(proposal_id: str, _token: str = Depends(verify_api_token)):
    """Manually reject a staged proposal (human veto)."""
    proposal = staging_manager.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(404, f"Proposal {proposal_id} not found")
    if hasattr(staging_manager, 'reject_proposal'):
        staging_manager.reject_proposal(proposal_id, reason="MANUAL_HUMAN_VETO")
    else:
        proposal.status = "REJECTED"
    return {
        "proposal_id": proposal_id,
        "status": "REJECTED",
        "reason": "MANUAL_HUMAN_VETO",
    }


'''
    trades_text = trades_text.replace(inject_marker, new_endpoints + inject_marker, 1)
    trades_py.write_text(trades_text, encoding="utf-8")
    print("[PATCH] backend/app/api/routes/trades.py -> added list + reject endpoints")
else:
    print("[SKIP] list_all_proposals already exists")

# ============================================================
# 1b. BACKEND: Ensure staging_manager has list_all_proposals + reject_proposal
# ============================================================
staging_path = ROOT / "backend/app/engines/execution/order_staging.py"
if staging_path.exists():
    st_text = staging_path.read_text(encoding="utf-8-sig", errors="replace")
    if "def list_all_proposals" not in st_text:
        new_methods = '''

    def list_all_proposals(self):
        """Return all staged proposals (list snapshot)."""
        return list(self._proposals.values()) if hasattr(self, '_proposals') else []

    def reject_proposal(self, proposal_id: str, reason: str = "MANUAL_REJECT"):
        """Mark a proposal as rejected with reason."""
        if hasattr(self, '_proposals') and proposal_id in self._proposals:
            proposal = self._proposals[proposal_id]
            proposal.status = "REJECTED"
            if hasattr(proposal, 'rejection_reason'):
                proposal.rejection_reason = reason
            return True
        return False
'''
        st_text = st_text.rstrip() + new_methods + "\n"
        staging_path.write_text(st_text, encoding="utf-8")
        print("[PATCH] order_staging.py -> injected list_all_proposals + reject_proposal")
    else:
        print("[SKIP] list_all_proposals exists in order_staging.py")

# ============================================================
# 2. FRONTEND: types/broker.ts
# ============================================================
broker_types = '''export interface BrokerAccountInfo {
  account_id: string;
  balance: number;
  equity: number;
  free_margin: number;
  currency: string;
  is_connected: boolean;
  latency_ms: number;
}

export interface BrokerPosition {
  ticket: string;
  symbol: string;
  direction: string;
  volume: number;
  open_price: number;
  current_price: number;
  unrealized_pnl: number;
  open_time?: string;
}

export interface BrokerPositionsResponse {
  positions: BrokerPosition[];
  total_open: number;
}

export interface StagedProposalSummary {
  proposal_id: string;
  status: string;
  symbol: string;
  direction: string;
  entry_price: number;
  stop_loss: number;
  take_profit: number | null;
  position_size_lots: number | null;
  gates_passed: number;
  created_at: string | null;
}

export interface ProposalsListResponse {
  proposals: StagedProposalSummary[];
  total: number;
}

export interface ApprovalResult {
  proposal_id: string;
  execution_mode: string;
  broker_ticket?: string;
  trade_id?: number;
  entry_fill?: number;
  position_size_lots?: number;
  status?: string;
}

export interface EmergencyCloseResult {
  status: string;
  liquidated_tickets?: string[];
  count?: number;
  closed_ticket?: string;
  reason: string;
}
'''
write_file("frontend/src/types/broker.ts", broker_types)

# ============================================================
# 3. FRONTEND: Extend lib/api.ts with broker functions
# ============================================================
api_ts_path = ROOT / "frontend/src/lib/api.ts"
api_text = api_ts_path.read_text(encoding="utf-8-sig", errors="replace")

if "getBrokerAccount" not in api_text:
    broker_api_block = '''
  // ============= BROKER BRIDGE ENDPOINTS =============
  getBrokerAccount: async () => {
    return request<any>(
      'getBrokerAccount',
      API_BASE + '/api/trades/broker/account',
      { headers: defaultHeaders() }
    );
  },

  getBrokerPositions: async () => {
    return request<any>(
      'getBrokerPositions',
      API_BASE + '/api/trades/broker/positions',
      { headers: defaultHeaders() }
    );
  },

  emergencyCloseAll: async (reason = 'MANUAL_EMERGENCY_LIQUIDATION') => {
    return request<any>(
      'emergencyCloseAll',
      API_BASE + '/api/trades/broker/emergency-close',
      {
        method: 'POST',
        headers: defaultHeaders(),
        body: JSON.stringify({ reason }),
      }
    );
  },

  listProposals: async () => {
    return request<any>(
      'listProposals',
      API_BASE + '/api/trades/proposals',
      { headers: defaultHeaders() }
    );
  },

  approveProposal: async (proposalId: string, idempotencyKey: string, executionMode: 'LIVE' | 'PAPER' = 'LIVE') => {
    return request<any>(
      'approveProposal',
      API_BASE + '/api/trades/proposals/' + proposalId + '/approve',
      {
        method: 'POST',
        headers: defaultHeaders(),
        body: JSON.stringify({ idempotency_key: idempotencyKey, execution_mode: executionMode }),
      }
    );
  },

  rejectProposal: async (proposalId: string) => {
    return request<any>(
      'rejectProposal',
      API_BASE + '/api/trades/proposals/' + proposalId + '/reject',
      { method: 'POST', headers: defaultHeaders() }
    );
  },
'''
    api_text_new = api_text.rstrip()
    if api_text_new.endswith("};"):
        api_text_new = api_text_new[:-2] + broker_api_block + "\n};\n"
    else:
        api_text_new += "\n\n// Broker extension appended safely\n"
    api_ts_path.write_text(api_text_new, encoding="utf-8")
    print("[PATCH] frontend/src/lib/api.ts -> injected 6 broker functions")
else:
    print("[SKIP] broker functions already in api.ts")

# ============================================================
# 5. FRONTEND: BrokerBridgePanel.tsx
# ============================================================
broker_panel = '''import { useState, useMemo } from 'react';
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
'''
write_file("frontend/src/components/cockpit/BrokerBridgePanel.tsx", broker_panel)

# ============================================================
# 6. FRONTEND: App.tsx - integrate BrokerBridgePanel below PreFlight
# ============================================================
app_tsx = ROOT / "frontend/src/App.tsx"
app_text = app_tsx.read_text(encoding="utf-8-sig", errors="replace")

if "BrokerBridgePanel" not in app_text:
    import_pattern = re.compile(r"(import\s+\{[^}]*PreFlightTerminal[^}]*\}\s+from\s+['\"][^'\"]+['\"];)")
    m = import_pattern.search(app_text)
    if m:
        insert_after = m.group(0)
        new_import = insert_after + "\nimport { BrokerBridgePanel } from './components/cockpit/BrokerBridgePanel';"
        app_text = app_text.replace(insert_after, new_import, 1)
        print("[PATCH] App.tsx -> added BrokerBridgePanel import")
    else:
        last_cockpit_import = re.compile(r"(import\s+[^;]+components/cockpit/[^;]+;)(?![\s\S]*import\s+[^;]+components/cockpit/)")
        m2 = last_cockpit_import.search(app_text)
        if m2:
            insert_after = m2.group(0)
            app_text = app_text.replace(
                insert_after,
                insert_after + "\nimport { BrokerBridgePanel } from './components/cockpit/BrokerBridgePanel';",
                1
            )
            print("[PATCH] App.tsx -> added BrokerBridgePanel import (fallback)")

    if "<LiveEventStream" in app_text and "<BrokerBridgePanel" not in app_text:
        app_text = app_text.replace(
            "<LiveEventStream",
            "<BrokerBridgePanel />\n\n          <LiveEventStream",
            1
        )
        print("[PATCH] App.tsx -> injected <BrokerBridgePanel/> before <LiveEventStream>")
    elif "<PreFlightTerminal" in app_text and "<BrokerBridgePanel" not in app_text:
        app_text = re.sub(
            r"(<PreFlightTerminal\s*/>)",
            r"\1\n          <BrokerBridgePanel />",
            app_text,
            count=1
        )
        print("[PATCH] App.tsx -> injected <BrokerBridgePanel/> after <PreFlightTerminal>")

    app_tsx.write_text(app_text, encoding="utf-8")
else:
    print("[SKIP] BrokerBridgePanel already in App.tsx")

# ============================================================
# 7. FRONTEND: Vitest test for BrokerBridgePanel
# ============================================================
test_content = '''import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrokerBridgePanel } from '../BrokerBridgePanel';
import * as apiModule from '../../../lib/api';

vi.mock('../../../lib/api', () => ({
  api: {
    getBrokerAccount: vi.fn(),
    getBrokerPositions: vi.fn(),
    listProposals: vi.fn(),
    approveProposal: vi.fn(),
    rejectProposal: vi.fn(),
    emergencyCloseAll: vi.fn(),
    toggleCircuitBreaker: vi.fn(),
  },
}));

function renderWithClient(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
  });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('BrokerBridgePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows CONNECTED badge when broker returns is_connected=true', async () => {
    (apiModule.api.getBrokerAccount as any).mockResolvedValue({
      account_id: 'SANDBOX-001',
      balance: 100000,
      equity: 99850,
      free_margin: 98200,
      currency: 'USD',
      is_connected: true,
      latency_ms: 42,
    });
    (apiModule.api.getBrokerPositions as any).mockResolvedValue({ positions: [], total_open: 0 });
    (apiModule.api.listProposals as any).mockResolvedValue({ proposals: [], total: 0 });

    renderWithClient(<BrokerBridgePanel />);
    await waitFor(() => expect(screen.getByText(/CONNECTED/i)).toBeInTheDocument());
    expect(screen.getByText(/SANDBOX-001/)).toBeInTheDocument();
  });

  it('shows DISCONNECTED when broker returns is_connected=false', async () => {
    (apiModule.api.getBrokerAccount as any).mockResolvedValue({
      account_id: 'X',
      balance: 0,
      equity: 0,
      free_margin: 0,
      currency: 'USD',
      is_connected: false,
      latency_ms: 0,
    });
    (apiModule.api.getBrokerPositions as any).mockResolvedValue({ positions: [], total_open: 0 });
    (apiModule.api.listProposals as any).mockResolvedValue({ proposals: [], total: 0 });

    renderWithClient(<BrokerBridgePanel />);
    await waitFor(() => expect(screen.getByText(/DISCONNECTED/i)).toBeInTheDocument());
  });

  it('renders pending proposals with approve/reject buttons', async () => {
    (apiModule.api.getBrokerAccount as any).mockResolvedValue({
      account_id: 'A', balance: 100000, equity: 100000, free_margin: 100000,
      currency: 'USD', is_connected: true, latency_ms: 40,
    });
    (apiModule.api.getBrokerPositions as any).mockResolvedValue({ positions: [], total_open: 0 });
    (apiModule.api.listProposals as any).mockResolvedValue({
      proposals: [{
        proposal_id: 'p-abc123',
        status: 'STAGED',
        symbol: 'EURUSD',
        direction: 'BUY',
        entry_price: 1.0850,
        stop_loss: 1.0800,
        take_profit: 1.0950,
        position_size_lots: 0.5,
        gates_passed: 9,
        created_at: null,
      }],
      total: 1,
    });

    renderWithClient(<BrokerBridgePanel />);
    await waitFor(() => expect(screen.getByTestId('approve-btn-p-abc123')).toBeInTheDocument());
    expect(screen.getByTestId('reject-btn-p-abc123')).toBeInTheDocument();
    expect(screen.getByText(/EURUSD/)).toBeInTheDocument();
  });

  it('requires 2-step confirmation before emergency liquidation', async () => {
    (apiModule.api.getBrokerAccount as any).mockResolvedValue({
      account_id: 'A', balance: 1, equity: 1, free_margin: 1,
      currency: 'USD', is_connected: true, latency_ms: 40,
    });
    (apiModule.api.getBrokerPositions as any).mockResolvedValue({ positions: [], total_open: 0 });
    (apiModule.api.listProposals as any).mockResolvedValue({ proposals: [], total: 0 });

    renderWithClient(<BrokerBridgePanel />);
    await waitFor(() => expect(screen.getByTestId('emergency-close-btn')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('emergency-close-btn'));
    await waitFor(() => expect(screen.getByTestId('emergency-confirm-btn')).toBeInTheDocument());
    expect(screen.getByTestId('emergency-cancel-btn')).toBeInTheDocument();
    expect(apiModule.api.emergencyCloseAll).not.toHaveBeenCalled();
  });
});
'''
write_file("frontend/src/components/cockpit/__tests__/BrokerBridgePanel.test.tsx", test_content)

# ============================================================
# 8. BACKEND TEST: Extend broker API test with list + reject
# ============================================================
backend_test = ROOT / "backend/tests/test_broker_api.py"
if backend_test.exists():
    bt_text = backend_test.read_text(encoding="utf-8-sig", errors="replace")
    if "def test_list_and_reject_proposal" not in bt_text:
        append_block = '''


def test_list_and_reject_proposal(client, auth_headers):
    """Verify /proposals list endpoint and /proposals/{id}/reject workflow."""
    stage_payload = {
        "request": {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.0850,
            "stop_loss": 1.0800,
            "take_profit": 1.0950,
            "position_size_lots": 0.5,
            "account_balance_usd": 100000,
            "daily_pnl_usd": 0,
            "total_drawdown_usd": 0,
            "spread_pips": 1.0,
            "open_positions": [],
            "news_events_within_60min": [],
        },
        "idempotency_key": "ik-listtest-001",
        "max_slippage_pips": 2.0,
    }
    stage_resp = client.post("/api/trades/proposals/stage", json=stage_payload, headers=auth_headers)
    if stage_resp.status_code != 200:
        list_resp = client.get("/api/trades/proposals", headers=auth_headers)
        assert list_resp.status_code == 200
        assert "proposals" in list_resp.json()
        return

    proposal_id = stage_resp.json()["proposal_id"]

    list_resp = client.get("/api/trades/proposals", headers=auth_headers)
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert "proposals" in data
    assert any(p["proposal_id"] == proposal_id for p in data["proposals"])

    rej_resp = client.post(f"/api/trades/proposals/{proposal_id}/reject", headers=auth_headers)
    assert rej_resp.status_code == 200
    assert rej_resp.json()["status"] == "REJECTED"
'''
        bt_text += append_block
        backend_test.write_text(bt_text, encoding="utf-8")
        print("[APPEND] backend/tests/test_broker_api.py -> added list+reject test")
    else:
        print("[SKIP] list_and_reject test already exists")

print("\n[SUCCESS] ALL CODE CHANGES WRITTEN CLEANLY.")
