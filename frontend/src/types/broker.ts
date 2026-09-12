export interface BrokerAccountInfo {
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
