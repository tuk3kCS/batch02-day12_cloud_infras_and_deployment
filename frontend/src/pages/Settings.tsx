import type { DashboardState } from "../types";

interface Props {
  data: DashboardState;
}

export function SettingsPage({ data }: Props) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Settings</h1>
        <p className="muted mt-2">Environment information exposed by the backend without secrets.</p>
      </div>
      <section className="panel overflow-hidden">
        <div className="border-b border-white/10 p-5">
          <h2 className="text-lg font-semibold text-white">Environment Information</h2>
        </div>
        <div className="grid gap-3 p-5 md:grid-cols-2">
          {Object.entries(data.environment).map(([key, value]) => (
            <div key={key} className="panel-muted p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">{key}</p>
              <p className="mt-2 break-words font-mono text-sm text-slate-200">{JSON.stringify(value)}</p>
            </div>
          ))}
        </div>
      </section>
      <section className="panel p-5">
        <h2 className="text-lg font-semibold text-white">Repository Root</h2>
        <p className="mt-3 break-all rounded-lg bg-black/20 p-3 font-mono text-sm text-slate-300">
          {data.inventory.root}
        </p>
      </section>
    </div>
  );
}
