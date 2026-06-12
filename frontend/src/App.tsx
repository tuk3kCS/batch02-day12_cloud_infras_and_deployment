import { AlertTriangle, Loader2 } from "lucide-react";
import { useState } from "react";
import { Layout } from "./components/Layout";
import { useDashboardState } from "./hooks/useDashboardState";
import { Containers } from "./pages/Containers";
import { Dashboard } from "./pages/Dashboard";
import { Deployments } from "./pages/Deployments";
import { Infrastructure } from "./pages/Infrastructure";
import { Logs } from "./pages/Logs";
import { Monitoring } from "./pages/Monitoring";
import { SettingsPage } from "./pages/Settings";

function App() {
  const [activePage, setActivePage] = useState("dashboard");
  const { data, error, loading } = useDashboardState();

  return (
    <Layout activePage={activePage} onNavigate={setActivePage}>
      {loading ? (
        <div className="grid min-h-[60vh] place-items-center">
          <div className="panel flex items-center gap-3 px-5 py-4 text-slate-300">
            <Loader2 className="h-5 w-5 animate-spin text-cyan-100" />
            Loading infrastructure state
          </div>
        </div>
      ) : error || !data ? (
        <div className="grid min-h-[60vh] place-items-center">
          <div className="panel max-w-xl p-6">
            <div className="flex items-center gap-3 text-rose-100">
              <AlertTriangle className="h-5 w-5" />
              <h1 className="text-lg font-semibold">Dashboard API unavailable</h1>
            </div>
            <p className="mt-3 text-sm text-slate-400">
              {error ?? "No dashboard state was returned."}
            </p>
          </div>
        </div>
      ) : (
        <>
          {activePage === "dashboard" ? <Dashboard data={data} /> : null}
          {activePage === "infrastructure" ? <Infrastructure data={data} /> : null}
          {activePage === "deployments" ? <Deployments data={data} /> : null}
          {activePage === "containers" ? <Containers data={data} /> : null}
          {activePage === "monitoring" ? <Monitoring data={data} /> : null}
          {activePage === "logs" ? <Logs data={data} /> : null}
          {activePage === "settings" ? <SettingsPage data={data} /> : null}
        </>
      )}
    </Layout>
  );
}

export default App;
