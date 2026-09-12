from pathlib import Path

ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")

# 1. Correct test_broker_api.py fixture name
bt_file = ROOT / "backend/tests/test_broker_api.py"
if bt_file.exists():
    text = bt_file.read_text(encoding="utf-8-sig", errors="replace")
    text = text.replace(
        "def test_list_and_reject_proposal(client, auth_headers):",
        "def test_list_and_reject_proposal(test_client, auth_headers):"
    )
    start_idx = text.find("def test_list_and_reject_proposal")
    if start_idx != -1:
        block = text[start_idx:]
        corrected_block = block.replace("client.", "test_client.")
        text = text[:start_idx] + corrected_block
    bt_file.write_text(text, encoding="utf-8")
    print("[FIX 1/3] test_broker_api.py fixture -> test_client")

# 2. Fix path safety in backend/tests/test_production_infra.py
infra_test = ROOT / "backend/tests/test_production_infra.py"
if infra_test.exists():
    text = infra_test.read_text(encoding="utf-8-sig", errors="replace")
    text = text.replace(
        'dc = Path("docker-compose.yml")',
        'dc = Path(__file__).resolve().parent.parent.parent / "docker-compose.yml"'
    )
    text = text.replace(
        'conf = Path("frontend/nginx.conf")',
        'conf = Path(__file__).resolve().parent.parent.parent / "frontend/nginx.conf"'
    )
    infra_test.write_text(text, encoding="utf-8")
    print("[FIX 2/3] test_production_infra.py -> absolute root paths")

# 3. Fix Frontend test in BrokerBridgePanel.test.tsx
fe_test = ROOT / "frontend/src/components/cockpit/__tests__/BrokerBridgePanel.test.tsx"
if fe_test.exists():
    text = fe_test.read_text(encoding="utf-8-sig", errors="replace")
    old_test_block = """  it('requires 2-step confirmation before emergency liquidation', async () => {
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
  });"""

    new_test_block = """  it('requires 2-step confirmation before emergency liquidation', async () => {
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
  });"""

    text = text.replace(old_test_block, new_test_block)
    fe_test.write_text(text, encoding="utf-8")
    print("[FIX 3/3] BrokerBridgePanel.test.tsx -> query loading wait added")

print("[ALL 3 FIXES COMPLETED SUCCESSFULLY]")
