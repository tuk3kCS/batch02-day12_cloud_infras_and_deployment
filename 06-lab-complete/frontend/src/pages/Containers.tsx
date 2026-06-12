import { StatusBadge } from "../components/StatusBadge";
import type { DashboardState } from "../types";

interface Props {
  data: DashboardState;
}

export function Containers({ data }: Props) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Containers</h1>
        <p className="muted mt-2">Docker images, Compose services, and container runtime configuration.</p>
      </div>
      <section className="panel overflow-hidden">
        <div className="border-b border-white/10 p-5">
          <h2 className="text-lg font-semibold text-white">Container Status</h2>
        </div>
        <div className="overflow-auto">
          <table className="w-full min-w-[820px] text-left text-sm">
            <thead className="bg-ink-900 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-5 py-3">Name</th>
                <th className="px-5 py-3">Kind</th>
                <th className="px-5 py-3">Source</th>
                <th className="px-5 py-3">Base Image</th>
                <th className="px-5 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/8">
              {data.containers.map((container) => (
                <tr key={`${container.kind}-${container.name}-${container.source}`} className="hover:bg-white/[0.03]">
                  <td className="px-5 py-4 font-medium text-white">{container.name}</td>
                  <td className="px-5 py-4 text-slate-300">{container.kind}</td>
                  <td className="px-5 py-4 font-mono text-xs text-slate-400">{container.source}</td>
                  <td className="px-5 py-4 text-slate-300">{container.baseImage ?? "-"}</td>
                  <td className="px-5 py-4"><StatusBadge status={container.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
