import { PipelineTimeline } from "../components/PipelineTimeline";
import { StatusBadge } from "../components/StatusBadge";
import type { DashboardState } from "../types";

interface Props {
  data: DashboardState;
}

export function Deployments({ data }: Props) {
  const deploymentRows = Object.entries(data.deployments);
  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Deployments</h1>
        <p className="muted mt-2">Deployment status across Railway, Render, Cloud Run, CI/CD, and cluster targets.</p>
      </div>
      <PipelineTimeline stages={data.architecture.pipeline} />
      <section className="panel overflow-hidden">
        <div className="border-b border-white/10 p-5">
          <h2 className="text-lg font-semibold text-white">Deployment Manifests</h2>
        </div>
        <div className="grid gap-4 p-5 md:grid-cols-2 xl:grid-cols-3">
          {deploymentRows.map(([target, files]) => (
            <div key={target} className="panel-muted p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <h3 className="font-medium capitalize text-white">{target}</h3>
                <StatusBadge status={files.length ? "configured" : target === "kubernetes" || target === "terraform" ? "not-present" : "missing"} />
              </div>
              <div className="space-y-2">
                {files.length ? (
                  files.map((file) => (
                    <p key={file} className="rounded-md bg-black/20 px-3 py-2 font-mono text-xs text-slate-300">
                      {file}
                    </p>
                  ))
                ) : (
                  <p className="text-sm text-slate-500">No manifest detected in repository.</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
