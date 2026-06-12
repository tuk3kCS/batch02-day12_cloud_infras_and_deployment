import type { DashboardState } from "./types";

// @ts-ignore
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export async function fetchDashboardState(signal?: AbortSignal): Promise<DashboardState> {
  const response = await fetch(`${API_BASE_URL}/dashboard/state`, {
    signal,
    headers: { Accept: "application/json" }
  });

  if (!response.ok) {
    throw new Error(`Dashboard API returned ${response.status}`);
  }

  return response.json() as Promise<DashboardState>;
}
