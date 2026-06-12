import { ArchitectureDiagram } from "../components/ArchitectureDiagram";
import { StatusBadge } from "../components/StatusBadge";
import type { DashboardState } from "../types";

interface Props {
  data: DashboardState;
}

export function Infrastructure({ data }: Props) {
  const files = data.inventory.files;
  const rows = [
    ["README", files.readme ? "present" : "missing", "README.md"],
    ["Docker Compose", data.inventory.counts.composeFiles ? "configured" : "missing", String(files.dockerCompose ?? "")],
    ["Dockerfiles", data.inventory.counts.dockerfiles ? "configured" : "missing", String(files.dockerfiles ?? "")],
    ["Kubernetes", data.inventory.counts.kubernetesManifests ? "configured" : "not-present", String(files.kubernetes ?? "")],
    ["Terraform", data.inventory.counts.terraformFiles ? "configured" : "not-present", String(files.terraform ?? "")],
    ["Monitoring", data.inventory.counts.monitoringConfigs ? "configured" : "not-present", String(files.monitoring ?? "")],
    ["Railway", data.deployments.railway.length ? "configured" : "missing", data.deployments.railway.join(", ")],
    ["Render", data.deployments.render.length ? "configured" : "missing", data.deployments.render.join(", ")],
    ["Cloud Run", data.deployments.cloudRun.length ? "configured" : "not-present", data.deployments.cloudRun.join(", ")]
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Infrastructure</h1>
        <p className="muted mt-2">Repository-aware architecture and cloud infrastructure inventory.</p>
      </div>
      <ArchitectureDiagram nodes={data.architecture.nodes} edges={data.architecture.edges} />
      <section className="panel overflow-hidden">
        <div className="border-b border-white/10 p-5">
          <h2 className="text-lg font-semibold text-white">Infrastructure Components</h2>
          <p className="muted mt-1">Detected from repository files and deployment manifests.</p>
        </div>
        <div className="overflow-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-ink-900 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-5 py-3">Component</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/8">
              {rows.map(([component, status, source]) => (
                <tr key={component} className="hover:bg-white/[0.03]">
                  <td className="px-5 py-4 font-medium text-white">{component}</td>
                  <td className="px-5 py-4"><StatusBadge status={status} /></td>
                  <td className="px-5 py-4 font-mono text-xs text-slate-400">{source || "No file detected"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
