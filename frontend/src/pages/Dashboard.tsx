import { Activity, AlertTriangle, Clock, Database, GitBranch, Server } from "lucide-react";
import { ArchitectureDiagram } from "../components/ArchitectureDiagram";
import { MetricCard } from "../components/MetricCard";
import { PipelineTimeline } from "../components/PipelineTimeline";
import { ResourceChart } from "../components/ResourceChart";
import { StatusBadge } from "../components/StatusBadge";
import type { DashboardState } from "../types";

interface Props {
  data: DashboardState;
}

function formatUptime(seconds: number) {
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  return hours > 0 ? `${hours}h ${minutes % 60}m` : `${minutes}m`;
}

export function Dashboard({ data }: Props) {
  const workerEntries = Object.entries(data.overview.workerRequests || {});
  workerEntries.sort((a, b) => a[0].localeCompare(b[0]));

  const w1 = workerEntries[0] ? `W1 (${workerEntries[0][0].slice(-4)}): ${workerEntries[0][1]}` : "";
  const w2 = workerEntries[1] ? `W2 (${workerEntries[1][0].slice(-4)}): ${workerEntries[1][1]}` : "";

  let reqDetail = "Total HTTP requests";
  if (w1 && w2) {
    reqDetail = `${w1} | ${w2}`;
  } else if (w1) {
    reqDetail = w1;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="page-title">System Overview</h1>
          <p className="muted mt-2">
            {data.overview.appName} running as {data.overview.instanceId}
          </p>
        </div>
        <StatusBadge status={data.overview.ready ? "running" : "unavailable"} />
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="Uptime" value={formatUptime(data.overview.uptimeSeconds)} icon={Clock} detail={data.generatedAt} />
        <MetricCard title="Requests" value={data.overview.totalRequests} icon={Activity} detail={reqDetail} />
        <MetricCard title="Errors" value={data.overview.errorCount} icon={AlertTriangle} detail="Middleware error count" />
        <MetricCard title="Redis" value={data.overview.redis} icon={Database} detail="State store readiness" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.45fr_0.9fr]">
        <ArchitectureDiagram nodes={data.architecture.nodes} edges={data.architecture.edges} />
        <ResourceChart
          cpu={data.resources.cpuPercent}
          memory={data.resources.memoryPercent}
          requests={data.overview.totalRequests}
          errors={data.overview.errorCount}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_0.8fr]">
        <PipelineTimeline stages={data.architecture.pipeline} />
        <section className="panel p-5">
          <h2 className="text-lg font-semibold text-white">Repository Signal</h2>
          <div className="mt-5 grid gap-3">
            {[
              ["Dockerfiles", data.inventory.counts.dockerfiles, Server],
              ["Compose files", data.inventory.counts.composeFiles, Server],
              ["CI/CD configs", data.inventory.counts.cicdWorkflows, GitBranch],
              ["Monitoring configs", data.inventory.counts.monitoringConfigs, Activity]
            ].map((item) => {
              const [label, value, Icon] = item as [string, number, any];
              const IconComponent = Icon;
              return (
                <div key={String(label)} className="panel-muted flex items-center justify-between p-4">
                  <div className="flex items-center gap-3">
                    <IconComponent className="h-4 w-4 text-cyan-100" />
                    <span className="text-sm text-slate-300">{label}</span>
                  </div>
                  <span className="text-lg font-semibold text-white">{String(value)}</span>
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
}
