import { PreFlightRequest, PreFlightResponse, CockpitTelemetrySnapshot, TerminalEvent } from '../types/telemetry';
import { env } from './env';

const API_BASE = env.API_BASE_URL;
const AUTH_TOKEN = env.API_AUTH_TOKEN;

export class NormalizedApiError extends Error {
  public status: number;
  public endpoint: string;
  public details: any;

  constructor(message: string, status: number = 500, endpoint: string = '', details: any = null) {
    super(message);
    this.name = 'NormalizedApiError';
    this.status = status;
    this.endpoint = endpoint;
    this.details = details;
  }
}

const getHeaders = (isJson: boolean = true): HeadersInit => {
  const headers: Record<string, string> = {
    "Authorization": `Bearer ${AUTH_TOKEN}`,
    "X-API-Key": AUTH_TOKEN,
  };
  if (isJson) {
    headers["Content-Type"] = "application/json";
  }
  return headers;
};

export function parseFastApiError(errJson: any, status: number, endpoint: string): NormalizedApiError {
  if (!errJson) {
    return new NormalizedApiError(`HTTP ${status} Response Error`, status, endpoint);
  }

  if (errJson.detail) {
    if (Array.isArray(errJson.detail)) {
      const messages = errJson.detail.map((item: any) => {
        const field = item.loc ? item.loc.slice(1).join('.') : 'body';
        return `${field ? field + ': ' : ''}${item.msg || 'Invalid field'}`;
      });
      return new NormalizedApiError(`Validation Error: ${messages.join(' | ')}`, status, endpoint, errJson.detail);
    }
    if (typeof errJson.detail === 'object') {
      return new NormalizedApiError(JSON.stringify(errJson.detail), status, endpoint, errJson.detail);
    }
    return new NormalizedApiError(String(errJson.detail), status, endpoint, errJson.detail);
  }

  if (errJson.message) {
    return new NormalizedApiError(String(errJson.message), status, endpoint, errJson);
  }

  return new NormalizedApiError(`API Request Failed (HTTP ${status})`, status, endpoint, errJson);
}

async function handleResponse<T>(res: Response, endpoint: string): Promise<T> {
  if (!res.ok) {
    let errJson: any = null;
    try {
      errJson = await res.json();
    } catch {
      // Body not JSON
    }
    throw parseFastApiError(errJson, res.status, endpoint);
  }
  return res.json() as Promise<T>;
}

export const api = {
  evaluatePreFlight: async (req: PreFlightRequest): Promise<PreFlightResponse> => {
    let res: Response;
    try {
      res = await fetch(`${API_BASE}/api/trades/preflight`, {
        method: "POST",
        headers: getHeaders(),
        body: JSON.stringify(req),
      });

      if (res.status === 404) {
        res = await fetch(`${API_BASE}/api/trades/pre-flight`, {
          method: "POST",
          headers: getHeaders(),
          body: JSON.stringify(req),
        });
      }
    } catch (networkErr: any) {
      throw new NormalizedApiError(
        `Network Connection Failure: Unable to reach backend at ${API_BASE}. Ensure server is running.`,
        0,
        'evaluatePreFlight'
      );
    }

    return handleResponse<PreFlightResponse>(res, "evaluatePreFlight");
  },

  getTelemetrySnapshot: async (): Promise<CockpitTelemetrySnapshot> => {
    const res = await fetch(`${API_BASE}/api/telemetry/snapshot`, {
      headers: getHeaders(),
    });
    return handleResponse<CockpitTelemetrySnapshot>(res, "getTelemetrySnapshot");
  },

  getRecentEvents: async (limit: number = 50): Promise<TerminalEvent[]> => {
    const res = await fetch(`${API_BASE}/api/telemetry/events?limit=${limit}`, {
      headers: getHeaders(),
    });
    return handleResponse<TerminalEvent[]>(res, "getRecentEvents");
  },

  toggleCircuitBreaker: async (trip: boolean, reason: string = "Manual Admin Action") => {
    const res = await fetch(`${API_BASE}/api/admin/circuit-breaker/toggle`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ trip, reason }),
    });
    return handleResponse<any>(res, "toggleCircuitBreaker");
  },

  getPropFirmPresets: async () => {
    const res = await fetch(`${API_BASE}/api/prop-firm/presets`, { headers: getHeaders() });
    return handleResponse<any>(res, "getPropFirmPresets");
  },

  getPropFirmAccount: async () => {
    const res = await fetch(`${API_BASE}/api/prop-firm/account`, { headers: getHeaders() });
    return handleResponse<any>(res, "getPropFirmAccount");
  },
};
