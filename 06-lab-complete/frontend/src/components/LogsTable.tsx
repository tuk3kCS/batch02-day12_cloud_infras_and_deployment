import type { LogItem } from "../types";

interface Props {
  logs: LogItem[];
}

export function LogsTable({ logs }: Props) {
  return (
    <section className="panel overflow-hidden">
      <div className="border-b border-white/10 p-5">
        <h2 className="text-lg font-semibold text-white">Logs Viewer</h2>
        <p className="muted mt-1">Structured events captured from the FastAPI runtime.</p>
      </div>
      <div className="max-h-[520px] overflow-auto">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="sticky top-0 bg-ink-900 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-5 py-3">Time</th>
              <th className="px-5 py-3">Event</th>
              <th className="px-5 py-3">Instance</th>
              <th className="px-5 py-3">Payload</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/8">
            {logs.length === 0 ? (
              <tr>
                <td className="px-5 py-8 text-slate-400" colSpan={4}>
                  No runtime log events captured yet.
                </td>
              </tr>
            ) : (
              logs.map((log, index) => (
                <tr key={`${log.timestamp}-${index}`} className="hover:bg-white/[0.03]">
                  <td className="px-5 py-3 font-mono text-xs text-slate-400">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </td>
                  <td className="px-5 py-3 text-cyan-100">{log.event}</td>
                  <td className="px-5 py-3 text-slate-300">{log.instance}</td>
                  <td className="px-5 py-3">
                    <code className="whitespace-pre-wrap text-xs text-slate-400">
                      {JSON.stringify(
                        Object.fromEntries(
                          Object.entries(log).filter(([key]) => !["timestamp", "event", "instance"].includes(key))
                        )
                      )}
                    </code>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
