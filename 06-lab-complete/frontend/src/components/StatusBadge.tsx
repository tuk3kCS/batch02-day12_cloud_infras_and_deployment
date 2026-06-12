import { CheckCircle2, CircleAlert, CircleDot, Clock3 } from "lucide-react";

interface Props {
  status: string;
}

const tone: Record<string, string> = {
  running: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
  ready: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
  active: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
  configured: "border-cyan-400/30 bg-cyan-400/10 text-cyan-100",
  buildable: "border-sky-400/30 bg-sky-400/10 text-sky-100",
  present: "border-sky-400/30 bg-sky-400/10 text-sky-100",
  external: "border-violet-400/30 bg-violet-400/10 text-violet-100",
  manual: "border-amber-400/30 bg-amber-400/10 text-amber-100",
  missing: "border-rose-400/30 bg-rose-400/10 text-rose-100",
  "not-present": "border-slate-500/30 bg-slate-500/10 text-slate-300",
  unavailable: "border-rose-400/30 bg-rose-400/10 text-rose-100"
};

export function StatusBadge({ status }: Props) {
  const Icon =
    status === "missing" || status === "unavailable"
      ? CircleAlert
      : status === "manual" || status === "not-present"
        ? Clock3
        : status === "running" || status === "active"
          ? CheckCircle2
          : CircleDot;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${
        tone[status] ?? "border-slate-500/30 bg-slate-500/10 text-slate-300"
      }`}
    >
      <Icon className="h-3.5 w-3.5" />
      {status}
    </span>
  );
}
