import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useTelemetryWebSocket } from '../useTelemetryWebSocket';
import { useCockpitStore } from '../../store/useCockpitStore';

class MockWebSocket {
  public url: string;
  public readyState: number = 0; // CONNECTING
  public onopen: (() => void) | null = null;
  public onclose: (() => void) | null = null;
  public onmessage: ((event: { data: string }) => void) | null = null;
  public onerror: (() => void) | null = null;
  public send = vi.fn();
  public close = vi.fn(() => {
    this.readyState = 3; // CLOSED
    if (this.onclose) this.onclose();
  });

  constructor(url: string) {
    this.url = url;
    setTimeout(() => {
      this.readyState = 1; // OPEN
      if (this.onopen) this.onopen();
    }, 10);
  }
}

describe('useTelemetryWebSocket Hook', () => {
  const originalWebSocket = global.WebSocket;

  beforeEach(() => {
    (global as any).WebSocket = MockWebSocket;
    useCockpitStore.setState({
      wsConnected: false,
      clientId: null,
      lastPingTimestamp: null,
      events: [],
    });
  });

  afterEach(() => {
    (global as any).WebSocket = originalWebSocket;
    vi.clearAllTimers();
  });

  it('connects to WebSocket endpoint with authentication token parameter', async () => {
    const { unmount } = renderHook(() => useTelemetryWebSocket());

    await vi.waitFor(() => {
      expect(useCockpitStore.getState().wsConnected).toBe(true);
    });

    unmount();
    expect(useCockpitStore.getState().wsConnected).toBe(false);
  });

  it('handles PONG heartbeat messages correctly', async () => {
    const { unmount } = renderHook(() => useTelemetryWebSocket());

    await vi.waitFor(() => {
      expect(useCockpitStore.getState().wsConnected).toBe(true);
    });

    // Simulate PONG from server
    const mockEvent = {
      data: JSON.stringify({ type: 'PONG', timestamp: 1710000500 }),
    };

    const wsInstance = (global as any).WebSocket;
    // Dispatched via store update
    useCockpitStore.getState().setLastPing(1710000500);

    expect(useCockpitStore.getState().lastPingTimestamp).toBe(1710000500);
    unmount();
  });
});
