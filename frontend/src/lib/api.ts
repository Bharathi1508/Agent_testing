const API_BASE_URL = "/api/heaap";

export interface Agent {
  agent_id: string;
  agent_name?: string;
  name?: string;
  status: string;
  execution_type?: string;
  capabilities: string[];
}

export interface Health {
  status: string;
  application?: string;
  onboarding?: string;
  assurance?: string;
}

async function apiRequest<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const heaapApi = {
  getHealth: () => apiRequest<Health>("/health"),
  getAgents: () => apiRequest<Agent[]>("/registry/agents"),
};
