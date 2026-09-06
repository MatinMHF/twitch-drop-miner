import React, { useRef, useEffect } from 'react';
import { useWebSocket } from '../context/WebSocketContext';
import { Terminal, Trash2 } from 'lucide-react';

export const LiveLogsViewer: React.FC = () => {
  const { logs } = useWebSocket();
  const bottomRef = useRef<HTMLDivElement>(null);

  return (
    <div className="bg-slate-950/90 border border-slate-800 rounded-2xl p-5 shadow-xl font-mono text-xs">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 text-slate-400">
        <div className="flex items-center space-x-2">
          <Terminal className="w-4 h-4 text-purple-400" />
          <span className="font-semibold text-slate-200">Live Service Telemetry & Logs</span>
        </div>
        <span className="text-[11px] text-slate-500">Real-time WebSocket feed</span>
      </div>

      <div className="mt-3 h-48 overflow-y-auto space-y-1 text-slate-300 pr-1">
        {logs.length === 0 ? (
          <p className="text-slate-600 italic py-4 text-center">Awaiting log events...</p>
        ) : (
          logs.map((log, idx) => (
            <div key={idx} className="leading-relaxed hover:bg-slate-900/50 px-1.5 py-0.5 rounded">
              <span className="text-purple-400">{log.substring(0, 10)}</span>{' '}
              <span className="text-slate-300">{log.substring(10)}</span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};
