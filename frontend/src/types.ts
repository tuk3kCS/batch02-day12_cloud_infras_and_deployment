export type Status =
  | "running"
  | "configured"
  | "buildable"
  | "present"
  | "active"
  | "external"
  | "manual"
  | "missing"
  | "not-present"
  | "unavailable";

export interface Overview {
  appName: string;
  version: string;
  environment: string;
  instanceId: string;
  uptimeSeconds: number;
  totalRequests: number;
  errorCount: number;
  ready: boolean;
  redis: string;
}

export interface Inventory {
  root: string;
  files: Record<string, string[] | boolean>;
  counts: {
    dockerfiles: number;
    composeFiles: number;
    kubernetesManifests: number;
    terraformFiles: number;
    cicdWorkflows: number;
    monitoringConfigs: number;
  };
  readmeBytes: number;
}

export interface ArchitectureNode {
  id: string;
  label: string;
  type: string;
  status: Status | string;
}

export interface ArchitectureEdge {
  from: string;
  to: string;
  label: string;
}

export interface PipelineStage {
  name: string;
  status: Status | string;
  source: string;
}

export interface ServiceItem {
  name: string;
  kind: string;
  source: string;
  status: Status | string;
  baseImage?: string;
}

export interface LogItem {
  timestamp: string;
  event: string;
  instance: string;
  [key: string]: unknown;
}

export interface DashboardState {
  generatedAt: string;
  overview: Overview;
  inventory: Inventory;
  architecture: {
    nodes: ArchitectureNode[];
    edges: ArchitectureEdge[];
    pipeline: PipelineStage[];
  };
  services: ServiceItem[];
  deployments: Record<string, string[]>;
  containers: ServiceItem[];
  resources: {
    cpuPercent: number | null;
    memoryPercent: number | null;
    redisConnectedClients: number | null;
    redisUsedMemoryHuman: string | null;
  };
  logs: LogItem[];
  environment: Record<string, unknown>;
}
