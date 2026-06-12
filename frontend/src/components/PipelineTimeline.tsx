import type { PipelineStage } from "../types";
import { StatusBadge } from "./StatusBadge";

interface Props {
  stages: PipelineStage[];
}

export function PipelineTimeline({ stages }: Props) {
  return (
    <section className="panel p-5">
      <h2 className="text-lg font-semibold text-white">CI/CD Pipeline Viewer</h2>
      <p className="muted mt-1">Source Code to User Request flow.</p>
      <div className="mt-6 grid gap-4 md:grid-cols-3 xl:grid-cols-5">
        {stages.map((stage, index) => (
          <div key={stage.name} className="relative">
            {index < stages.length - 1 ? (
              <div className="absolute left-8 top-5 hidden h-px w-full bg-cyan-300/25 md:block" />
            ) : null}
            <div className="relative z-10 panel-muted h-full p-4">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full border border-cyan-300/30 bg-cyan-400/10 text-sm font-semibold text-cyan-100">
                {index + 1}
              </div>
              <h3 className="text-sm font-semibold text-white">{stage.name}</h3>
              <p className="mt-2 min-h-10 text-xs text-slate-400">{stage.source}</p>
              <div className="mt-3">
                <StatusBadge status={stage.status} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
