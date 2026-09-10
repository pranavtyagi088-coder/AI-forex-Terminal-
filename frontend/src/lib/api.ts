import { env } from './env';
import {
  PreFlightRequest,
  PreFlightResponse,
  CockpitTelemetrySnapshot,
  TerminalEvent,
} from '../types/telemetry';

const API_BASE = env.API_BASE_URL;
const AUTH_TOKEN = env.API_AUTH_TOKEN;

const defaultHeaders = () => ({
  'Content-Type': 'application/json',
  'Authorization': 'Bearer ' + AUTH_TOKEN,
});

async function handleResponse<T>(res: Response, endpointName: string): Promise<T> {
  if (!res.ok) {
    let errMessage = 'HTTP ' + res.status + ' ' + res.statusText;
    try {
      const errJson = await res.json();
      if (errJson.detail) {
        errMessage = typeof errJson.detail === 'string'
          ? errJson.detail
          : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore
    }
    throw new Error('[' + endpointName + '] ' + errMessage);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getCockpitSnapshot: async (): Promise<CockpitTelemetrySnapshot> => {
    const res = await fetch(API_BASE + '/api/telemetry/cockpit', {
      headers: defaultHeaders(),
    });
    return handleResponse<CockpitTelemetrySnapshot>(res, 'getCockpitSnapshot');
  },

  evaluatePreFlight: async (req: PreFlightRequest): Promise<PreFlightResponse> => {
    const res = await fetch(API_BASE + '/api/trades/pre-flight-check', {
      method: 'POST',
      headers: defaultHeaders(),
      body: JSON.stringify(req),
    });
    return handleResponse<PreFlightResponse>(res, 'evaluatePreFlight');
  },

  getRecentEvents: async (_limit = 50): Promise<TerminalEvent[]> => {
    try {
      const res = await fetch(API_BASE + '/api/telemetry/cockpit', {
        headers: defaultHeaders(),
      });
      if (!res.ok) return [];
      const data = await res.json();
      return data.recent_events || [];
    } catch {
      return [];
    }
  },

  toggleCircuitBreaker: async (enable: boolean, reason = 'Manual Trigger'): Promise<any> => {
    const res = await fetch(API_BASE + '/api/admin/circuit-breaker/toggle', {
      method: 'POST',
      headers: defaultHeaders(),
      body: JSON.stringify({ enable, reason }),
    });
    return handleResponse<any>(res, 'toggleCircuitBreaker');
  },
};
