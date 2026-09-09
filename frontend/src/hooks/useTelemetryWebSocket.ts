import { useEffect, useRef, useCallback } from 'react';
import { useCockpitStore } from '../store/useCockpitStore';
import { TerminalEvent } from '../types/telemetry';

const WS_BASE_URL = "ws://127.0.0.1:8000/ws/telemetry";
const AUTH_TOKEN = "dev-secret-token";

export function useTelemetryWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const { setWsConnected, addEvent, setLastPing } = useCockpitStore();

  const connect = useCallback(() => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      const url = `${WS_BASE_URL}?token=${AUTH_TOKEN}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("⚡ [WebSocket] Connected to Institutional Telemetry Stream");
        setWsConnected(true);

        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send("ping");
          }
        }, 25000);
      };

      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);

          if (data.type === 'PONG') {
            setLastPing(data.timestamp);
            return;
          }

          if (data.type === 'SYSTEM' && data.client_id) {
            setWsConnected(true, data.client_id);
          }

          const terminalEvent: TerminalEvent = {
            event_id: data.event_id || `EVT-${Date.now()}`,
            type: data.type,
            severity: data.severity || 'INFO',
            source: data.source || data.source_module || 'ws_stream',
            message: data.message || JSON.stringify(data),
            symbol: data.symbol || null,
            payload: data.payload || data,
            timestamp: data.timestamp || Date.now() / 1000,
          };

          addEvent(terminalEvent);
        } catch (err) {
          console.error("❌ Failed to parse incoming WebSocket message:", err);
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      reconnectTimeoutRef.current = setTimeout(connect, 5000);
    }
  }, [setWsConnected, addEvent, setLastPing]);

  useEffect(() => {
    connect();

    return () => {
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const sendCommand = (cmd: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(cmd);
    }
  };

  return { sendCommand };
}
