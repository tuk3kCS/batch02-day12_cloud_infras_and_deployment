import {
  Activity,
  Boxes,
  Cloud,
  Container,
  GitBranch,
  LayoutDashboard,
  ListTree,
  Moon,
  ScrollText,
  Settings
} from "lucide-react";
import type { ReactNode } from "react";

const nav = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "infrastructure", label: "Infrastructure", icon: Cloud },
  { id: "deployments", label: "Deployments", icon: GitBranch },
  { id: "containers", label: "Containers", icon: Container },
  { id: "monitoring", label: "Monitoring", icon: Activity },
  { id: "logs", label: "Logs", icon: ScrollText },
  { id: "settings", label: "Settings", icon: Settings }
];

interface Props {
  activePage: string;
  onNavigate: (page: string) => void;
  children: ReactNode;
}

export function Layout({ activePage, onNavigate, children }: Props) {
  return (
    <div className="min-h-screen text-slate-100">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 border-r border-white/10 bg-ink-950/88 backdrop-blur lg:block">
        <div className="flex h-20 items-center gap-3 px-6">
          <div className="grid h-10 w-10 place-items-center rounded-lg bg-cyan-400/15 text-cyan-100">
            <Boxes className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm text-slate-400">Day 12 Codelab</p>
            <h1 className="text-base font-semibold text-white">Cloud Infra Console</h1>
          </div>
        </div>
        <nav className="space-y-1 px-3">
          {nav.map((item) => {
            const Icon = item.icon;
            const active = item.id === activePage;
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition ${
                  active
                    ? "bg-cyan-400/12 text-cyan-50"
                    : "text-slate-400 hover:bg-white/6 hover:text-white"
                }`}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </button>
            );
          })}
        </nav>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 border-b border-white/10 bg-ink-950/75 backdrop-blur">
          <div className="flex min-h-16 items-center justify-between gap-4 px-4 md:px-8">
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-cyan-200/70">
                Production Infrastructure
              </p>
              <p className="text-sm text-slate-400">FastAPI + Docker + Redis + Nginx + Cloud Deploy</p>
            </div>
            <div className="hidden items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm text-slate-300 sm:flex">
              <Moon className="h-4 w-4 text-cyan-100" />
              Dark mode
            </div>
          </div>
          <div className="flex gap-2 overflow-x-auto border-t border-white/10 px-4 py-2 lg:hidden">
            {nav.map((item) => (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={`whitespace-nowrap rounded-lg px-3 py-2 text-xs ${
                  item.id === activePage ? "bg-cyan-400/15 text-cyan-50" : "text-slate-400"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </header>
        <main className="px-4 py-6 md:px-8">{children}</main>
      </div>
    </div>
  );
}
