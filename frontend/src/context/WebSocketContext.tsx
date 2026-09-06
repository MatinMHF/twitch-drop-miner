import React, { createContext, useContext, useEffect, useState, useRef } from 'react';
import { MinerStatus } from '../services/types';
import { useAuth } from './AuthContext';

interface WebSocketContextType {
  status: MinerStatus | null;
  isConnected: boolean;
  logs: string[];
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const [status, setStatus] = useState<MinerStatus | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [logs, setLogs] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const addLog = (message: string) => {
    const time = new Date().toLocaleTimeString();
    setLogs((prev) => [`[${time}] ${message}`, ...prev.slice(0, 99)]);
  };

  useEffect(() => {
    if (!user?.is_active) {
      if (wsRef.current) {
        wsRef.current.close();
      }
      return;
    }

    const connect = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/ws`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        addLog('Connected to Twitch Drop Miner live telemetry stream.');
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === 'STATUS_UPDATE') {
            setStatus(payload.data);
          }
        } catch {
          // ignore non-json
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        addLog('Telemetry connection closed. Reconnecting in 3s...');
        reconnectTimeoutRef.current = window.setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [user?.is_active]);

  return (
    <WebSocketContext.Provider value={{ status, isConnected, logs }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) throw new Error('useWebSocket must be used within WebSocketProvider');
  return context;
};
