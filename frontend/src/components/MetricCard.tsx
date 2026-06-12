import type { LucideIcon } from "lucide-react";

interface Props {
  title: string;
  value: string | number;
  detail?: string;
  icon: LucideIcon;
}

export function MetricCard({ title, value, detail, icon: Icon }: Props) {
  return (
    <section className="panel p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="muted">{title}</p>
          <p className="mt-3 text-2xl font-semibold text-white">{value}</p>
          {detail ? <p className="mt-2 text-xs text-slate-500">{detail}</p> : null}
        </div>
        <div className="rounded-lg border border-cyan-400/20 bg-cyan-400/10 p-2.5 text-cyan-100">
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </section>
  );
}
