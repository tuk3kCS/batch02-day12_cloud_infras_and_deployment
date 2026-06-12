import type { ArchitectureEdge, ArchitectureNode } from "../types";
import { StatusBadge } from "./StatusBadge";

interface Props {
  nodes: ArchitectureNode[];
  edges: ArchitectureEdge[];
}

const positions: Record<string, { x: number; y: number }> = {
  user: { x: 60, y: 150 },
  frontend: { x: 230, y: 70 },
  lb: { x: 420, y: 150 },
  api: { x: 610, y: 150 },
  redis: { x: 800, y: 70 },
  docker: { x: 800, y: 230 },
  cloud: { x: 990, y: 150 }
};

const nodeTone: Record<string, string> = {
  edge: "fill-cyan-400/15 stroke-cyan-300/45",
  frontend: "fill-violet-400/15 stroke-violet-300/45",
  network: "fill-sky-400/15 stroke-sky-300/45",
  backend: "fill-emerald-400/15 stroke-emerald-300/45",
  database: "fill-amber-400/15 stroke-amber-300/45",
  container: "fill-indigo-400/15 stroke-indigo-300/45",
  cloud: "fill-rose-400/15 stroke-rose-300/45"
};

export function ArchitectureDiagram({ nodes, edges }: Props) {
  return (
    <section className="panel overflow-hidden p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">Infrastructure Architecture</h2>
          <p className="muted">Generated from backend runtime and repository manifests.</p>
        </div>
      </div>
      <div className="overflow-x-auto">
        <svg viewBox="0 0 1120 340" className="min-w-[900px]">
          <defs>
            <marker id="arrow" markerHeight="8" markerWidth="8" orient="auto" refX="7" refY="4">
              <path d="M0,0 L8,4 L0,8 Z" fill="#67e8f9" />
            </marker>
          </defs>
          {edges.map((edge) => {
            const from = positions[edge.from];
            const to = positions[edge.to];
            if (!from || !to) return null;
            return (
              <g key={`${edge.from}-${edge.to}`}>
                <line
                  x1={from.x + 56}
                  y1={from.y}
                  x2={to.x - 56}
                  y2={to.y}
                  stroke="#67e8f9"
                  strokeOpacity="0.42"
                  strokeWidth="2"
                  markerEnd="url(#arrow)"
                />
                <text
                  x={(from.x + to.x) / 2}
                  y={(from.y + to.y) / 2 - 10}
                  textAnchor="middle"
                  className="fill-slate-400 text-[11px]"
                >
                  {edge.label}
                </text>
              </g>
            );
          })}
          {nodes.map((node) => {
            const pos = positions[node.id];
            if (!pos) return null;
            return (
              <g key={node.id}>
                <rect
                  x={pos.x - 72}
                  y={pos.y - 42}
                  width="144"
                  height="84"
                  rx="8"
                  className={nodeTone[node.type] ?? "fill-slate-400/10 stroke-slate-400/40"}
                />
                <text x={pos.x} y={pos.y - 4} textAnchor="middle" className="fill-white text-[13px] font-semibold">
                  {node.label}
                </text>
                <text x={pos.x} y={pos.y + 18} textAnchor="middle" className="fill-slate-400 text-[11px]">
                  {node.type}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {nodes.map((node) => (
          <div key={node.id} className="panel-muted flex items-center justify-between gap-3 p-3">
            <span className="truncate text-sm text-slate-200">{node.label}</span>
            <StatusBadge status={node.status} />
          </div>
        ))}
      </div>
    </section>
  );
}
