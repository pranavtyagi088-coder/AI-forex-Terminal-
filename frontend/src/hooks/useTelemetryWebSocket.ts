import { useEffect, useRef } from 'react';
import { env } from '../lib/env';
import { useCockpitStore } from '../store/useCockpitStore';
import { TerminalEvent } from '../types/telemetry';

export function useTelemetryWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const { setWsConnected, addEvent, setLastPing } = useCockpitStore();

  useEffect(() => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const url = env.WS_BASE_URL + '?token=' + env.API_AUTH_TOKEN;
    console.log('🔌 [WebSocket] Connecting to:', url);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('⚡ [WebSocket] Connected successfully!');
      setWsConnected(true);
    };

    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        setLastPing();
        setWsConnected(true);

        const event: TerminalEvent = {
          id: data.id || data.decision_id || ('EVT-' + Date.now() + '-' + Math.random().toString(36).substring(2, 6)),
          timestamp: data.timestamp || (Date.now() / 1000),
          severity: data.severity || 'INFO',
          type: data.type || 'SYSTEM',
          source: data.source || data.source_module || 'ws_stream',
          message: data.message || data.details || JSON.stringify(data),
          details: data,
        };

        addEvent(event);
      } catch (err) {
        console.error('❌ Failed to parse WebSocket message:', err);
      }
    };

    ws.onclose = () => {
      console.warn('⚠️ [WebSocket] Stream Disconnected');
      setWsConnected(false);
    };

    ws.onerror = (err) => {
      console.error('❌ [WebSocket] Stream Error:', err);
      ws.close();
    };

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [setWsConnected, addEvent, setLastPing]);

  const sendCommand = (cmd: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(cmd);
    }
  };

  return { sendCommand };
}
