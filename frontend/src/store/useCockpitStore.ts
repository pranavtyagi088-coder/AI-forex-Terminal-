import { create } from 'zustand';
import { TerminalEvent, CockpitTelemetrySnapshot } from '../types/telemetry';
import { api } from '../lib/api';

interface CockpitState {
  wsConnected: boolean;
  clientId: string | null;
  lastPingTimestamp: number | null;
  telemetry: CockpitTelemetrySnapshot | null;
  telemetryLoading: boolean;
  telemetryError: string | null;
  events: TerminalEvent[];
  circuitBreakerTripped: boolean;
  circuitBreakerReason: string | null;
  
  // Actions
  setWsConnected: (connected: boolean, clientId?: string) => void;
  updateTelemetry: (snapshot: CockpitTelemetrySnapshot) => void;
  addEvent: (event: TerminalEvent) => void;
  setEvents: (events: TerminalEvent[]) => void;
  setCircuitBreaker: (tripped: boolean, reason?: string) => void;
  setLastPing: (timestamp: number) => void;
  fetchSnapshot: () => Promise<void>;
}

export const useCockpitStore = create<CockpitState>((set) => ({
  wsConnected: false,
  clientId: null,
  lastPingTimestamp: null,
  telemetry: null,
  telemetryLoading: false,
  telemetryError: null,
  events: [],
  circuitBreakerTripped: false,
  circuitBreakerReason: null,

  setWsConnected: (connected, clientId) =>
    set((state) => ({
      wsConnected: connected,
      clientId: clientId !== undefined ? clientId : state.clientId,
    })),

  updateTelemetry: (snapshot) =>
    set({
      telemetry: snapshot,
      circuitBreakerTripped: snapshot.circuit_breaker_active,
      circuitBreakerReason: snapshot.circuit_breaker_reason || null,
      telemetryError: null,
    }),

  addEvent: (event) =>
    set((state) => {
      // Deduplicate by event_id if present
      if (event.event_id && state.events.some((e) => e.event_id === event.event_id)) {
        return state;
      }
      return {
        events: [event, ...state.events.slice(0, 199)], // keep latest 200 events
        circuitBreakerTripped:
          event.type === 'CIRCUIT_BREAKER_TRIPPED'
            ? true
            : event.type === 'CIRCUIT_BREAKER_RESET'
            ? false
            : state.circuitBreakerTripped,
        circuitBreakerReason:
          event.type === 'CIRCUIT_BREAKER_TRIPPED' ? event.message : state.circuitBreakerReason,
      };
    }),

  setEvents: (events) => set({ events }),

  setCircuitBreaker: (tripped, reason) =>
    set({
      circuitBreakerTripped: tripped,
      circuitBreakerReason: reason || null,
    }),

  setLastPing: (timestamp) => set({ lastPingTimestamp: timestamp }),

  fetchSnapshot: async () => {
    set({ telemetryLoading: true, telemetryError: null });
    try {
      const snapshot = await api.getTelemetrySnapshot();
      let recentEvents: TerminalEvent[] = [];
      try {
        recentEvents = await api.getRecentEvents(50);
      } catch (eventErr) {
        // Safe degrade: if event log fails but snapshot succeeds, keep logging but don't crash whole app
        console.warn("⚠️ Failed to load recent events snapshot:", eventErr);
      }

      set({
        telemetry: snapshot,
        circuitBreakerTripped: snapshot.circuit_breaker_active,
        circuitBreakerReason: snapshot.circuit_breaker_reason || null,
        events: recentEvents,
        telemetryLoading: false,
        telemetryError: null,
      });
    } catch (err: any) {
      // Fail-closed: telemetry set to null, never fabricate status
      set({
        telemetry: null,
        telemetryLoading: false,
        telemetryError: err instanceof Error ? err.message : String(err),
      });
    }
  }
}));
