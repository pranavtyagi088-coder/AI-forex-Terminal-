import { env } from './env';
import {
  PreFlightRequest,
  PreFlightResponse,
  CockpitTelemetrySnapshot,
  TerminalEvent,
} from '../types/telemetry';

const API_BASE = env.API_BASE_URL;
const AUTH_TOKEN = env.API_AUTH_TOKEN;

export class NormalizedApiError extends Error {
  status: number;
  endpoint: string;
  details?: any;

  constructor(message: string, status: number, endpoint: string, details?: any) {
    super(message);
    this.name = 'NormalizedApiError';
    this.status = status;
    this.endpoint = endpoint;
    this.details = details;
    Object.setPrototypeOf(this, NormalizedApiError.prototype);
  }
}

export function parseFastApiError(
  payload: any,
  status: number,
  endpoint: string
): NormalizedApiError {
  if (!payload) {
    return new NormalizedApiError(`HTTP ${status} Response Error`, status, endpoint);
  }

  if (Array.isArray(payload.detail)) {
    const parts = payload.detail.map((item: any) => {
      const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : 'field';
      return `${field}: ${item.msg}`;
    });
    const message = `Validation Error: ${parts.join(', ')}`;
    return new NormalizedApiError(message, status, endpoint, payload.detail);
  }

  if (typeof payload.detail === 'string') {
    return new NormalizedApiError(payload.detail, status, endpoint);
  }

  if (payload.detail && typeof payload.detail === 'object') {
    return new NormalizedApiError(JSON.stringify(payload.detail), status, endpoint, payload.detail);
  }

  if (payload.message && typeof payload.message === 'string') {
    return new NormalizedApiError(payload.message, status, endpoint);
  }

  return new NormalizedApiError(`HTTP ${status} Response Error`, status, endpoint, payload);
}

const defaultHeaders = () => ({
  'Content-Type': 'application/json',
  'Authorization': 'Bearer ' + AUTH_TOKEN,
});

async function request<T>(endpointName: string, url: string, options?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, options);
  } catch (err: any) {
    if (err instanceof NormalizedApiError) throw err;
    throw new NormalizedApiError(
      `[${endpointName}] Network Connection Failure: ${err?.message || String(err)}`,
      0,
      endpointName,
      err
    );
  }

  if (!res.ok) {
    let payload: any = null;
    try {
      payload = await res.json();
    } catch {
      // payload stays null
    }
    throw parseFastApiError(payload, res.status, endpointName);
  }

  return res.json() as Promise<T>;
}

export const api = {
  getCockpitSnapshot: async (): Promise<CockpitTelemetrySnapshot> => {
    return request<CockpitTelemetrySnapshot>(
      'getCockpitSnapshot',
      API_BASE + '/api/telemetry/cockpit',
      { headers: defaultHeaders() }
    );
  },

  getTelemetrySnapshot: async (): Promise<CockpitTelemetrySnapshot> => {
    return api.getCockpitSnapshot();
  },

  evaluatePreFlight: async (req: PreFlightRequest): Promise<PreFlightResponse> => {
    return request<PreFlightResponse>(
      'evaluatePreFlight',
      API_BASE + '/api/trades/pre-flight-check',
      {
        method: 'POST',
        headers: defaultHeaders(),
        body: JSON.stringify(req),
      }
    );
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
    return request<any>(
      'toggleCircuitBreaker',
      API_BASE + '/api/admin/circuit-breaker/toggle',
      {
        method: 'POST',
        headers: defaultHeaders(),
        body: JSON.stringify({ enable, reason }),
      }
    );
  },
};
