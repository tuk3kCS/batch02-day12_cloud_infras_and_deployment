import { Activity, Cpu, Database, MemoryStick } from "lucide-react";
import { MetricCard } from "../components/MetricCard";
import { ResourceChart } from "../components/ResourceChart";
import type { DashboardState } from "../types";

interface Props {
  data: DashboardState;
}

export function Monitoring({ data }: Props) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Monitoring</h1>
        <p className="muted mt-2">Live application and resource usage metrics from the backend process.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="CPU" value={data.resources.cpuPercent === null ? "N/A" : `${data.resources.cpuPercent}%`} icon={Cpu} />
        <MetricCard title="Memory" value={data.resources.memoryPercent === null ? "N/A" : `${data.resources.memoryPercent}%`} icon={MemoryStick} />
        <MetricCard title="Redis Clients" value={data.resources.redisConnectedClients ?? "N/A"} icon={Database} />
        <MetricCard title="Redis Memory" value={data.resources.redisUsedMemoryHuman ?? "N/A"} icon={Activity} />
      </div>
      <ResourceChart
        cpu={data.resources.cpuPercent}
        memory={data.resources.memoryPercent}
        requests={data.overview.totalRequests}
        errors={data.overview.errorCount}
      />
    </div>
  );
}
