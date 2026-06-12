import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface Props {
  cpu: number | null;
  memory: number | null;
  requests: number;
  errors: number;
}

export function ResourceChart({ cpu, memory, requests, errors }: Props) {
  const data = [
    { name: "CPU", value: cpu ?? 0 },
    { name: "Memory", value: memory ?? 0 },
    { name: "Requests", value: Math.min(100, requests) },
    { name: "Errors", value: Math.min(100, errors) }
  ];

  return (
    <section className="panel p-5">
      <h2 className="text-lg font-semibold text-white">Monitoring Metrics</h2>
      <p className="muted mt-1">Live runtime metrics from the FastAPI process.</p>
      <div className="mt-5 h-72">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ left: -18, right: 10, top: 10, bottom: 0 }}>
            <defs>
              <linearGradient id="metricFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.45} />
                <stop offset="95%" stopColor="#22d3ee" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#ffffff" strokeOpacity={0.08} />
            <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
            <YAxis stroke="#94a3b8" fontSize={12} />
            <Tooltip
              contentStyle={{
                background: "#0d1828",
                border: "1px solid rgba(255,255,255,0.12)",
                borderRadius: 8,
                color: "#fff"
              }}
            />
            <Area type="monotone" dataKey="value" stroke="#22d3ee" fill="url(#metricFill)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
