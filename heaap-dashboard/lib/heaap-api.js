import "server-only";

const API_BASE =
  process.env.HEAAP_API_URL ||
  "http://127.0.0.1:8000";

export async function heaapRequest(
  path,
  options = {}
) {
  const response = await fetch(
    `${API_BASE}${path}`,
    {
      ...options,
      cache: "no-store",
      headers: {
        Accept: "application/json",
        ...(options.body
          ? { "Content-Type": "application/json" }
          : {}),
        ...options.headers,
      },
    }
  );

  if (!response.ok) {
    const detail = await response.text();

    throw new Error(
      `HEAAP API ${response.status}: ${detail}`
    );
  }

  return response.json();
}

export async function getAgents() {
  return heaapRequest("/registry/agents");
}

export async function getHealth() {
  return heaapRequest("/health");
}

export async function getGovernanceStatus(agentId) {
  return heaapRequest(
    `/governance/status/${encodeURIComponent(agentId)}`
  );
}

export async function getGovernanceHistory(agentId) {
  return heaapRequest(
    `/governance/history/${encodeURIComponent(agentId)}`
  );
}

export async function getCapabilityAgents(capability) {
  return heaapRequest(
    `/supervisor/capabilities/${encodeURIComponent(capability)}/agents`
  );
}
