import { LogsTable } from "../components/LogsTable";
import type { DashboardState } from "../types";

interface Props {
  data: DashboardState;
}

export function Logs({ data }: Props) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Logs</h1>
        <p className="muted mt-2">Structured JSON events emitted by the production backend.</p>
      </div>
      <LogsTable logs={data.logs} />
    </div>
  );
}
