import { describe, it, expect, vi, beforeEach } from 'vitest';
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
    // Wait for CONNECTED badge so we know loading is done and button is enabled
    await waitFor(() => expect(screen.getByText(/CONNECTED/i)).toBeInTheDocument());
    
    const emergencyBtn = screen.getByTestId('emergency-close-btn');
    expect(emergencyBtn).not.toBeDisabled();
    fireEvent.click(emergencyBtn);
    
    await waitFor(() => expect(screen.getByTestId('emergency-confirm-btn')).toBeInTheDocument());
    expect(screen.getByTestId('emergency-cancel-btn')).toBeInTheDocument();
    expect(apiModule.api.emergencyCloseAll).not.toHaveBeenCalled();
  });
});
