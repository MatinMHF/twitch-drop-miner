import React, { useRef } from 'react';
import { useWebSocket } from '../context/WebSocketContext';
import { Terminal, Radio } from 'lucide-react';

export const LiveLogsViewer: React.FC = () => {
  const { logs } = useWebSocket();
  const bottomRef = useRef<HTMLDivElement>(null);

  return (
    <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 rounded-2xl p-6 shadow-xl">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800/80">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center space-x-2">
            <Terminal className="w-5 h-5 text-purple-400" />
            <span>Service Telemetry & Logs</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time WebSocket event logs & minute watch heartbeat stream.
          </p>
        </div>
        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-950/40 text-emerald-400 border border-emerald-500/30">
          <Radio className="w-3.5 h-3.5 animate-pulse text-emerald-400" />
          <span>Live Stream</span>
        </div>
      </div>

      <div className="mt-4 bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 font-mono text-xs h-56 overflow-y-auto space-y-1.5 text-slate-300">
        {logs.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-xs italic">
            Awaiting live mining events and heartbeat telemetry...
          </div>
        ) : (
          logs.map((log, idx) => (
            <div
              key={idx}
              className="leading-relaxed hover:bg-slate-800/40 px-2 py-1 rounded transition-colors flex items-baseline space-x-2"
            >
              <span className="text-purple-400 font-semibold shrink-0">
                {log.substring(0, 10)}
              </span>
              <span className="text-slate-300 break-all">{log.substring(10)}</span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};

