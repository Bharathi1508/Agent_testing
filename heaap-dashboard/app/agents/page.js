import { Suspense } from "react";

const API_URL =
  process.env.HEAAP_API_URL || "http://127.0.0.1:8000";

async function getAgents() {
  const response = await fetch(
    `${API_URL}/api/registry/agents`,
    { cache: "no-store" }
  );

  if (!response.ok) {
    throw new Error("Registry API unavailable");
  }

  return response.json();
}

async function AgentRegistryContent() {
  let data;

  try {
    data = await getAgents();
  } catch {
    return (
      <main style={{ padding: 40 }}>
        <h1>HEAAP Agent Registry</h1>
        <p>Unable to load registry data from FastAPI.</p>
      </main>
    );
  }

  const agents = data.agents || [];
  const summary = data.summary || {};

  return (
    <main style={{ padding: 40, maxWidth: 1200, margin: "auto" }}>
      <nav style={{ marginBottom: 24 }}>
        <a href="/">Dashboard</a> / Agent Registry
      </nav>

      <h1>Agent Registry</h1>
      <p>Discovered and registered enterprise agents</p>

      <section
        style={{
          display: "flex",
          gap: 20,
          flexWrap: "wrap",
          margin: "30px 0",
        }}
      >
        <div>Total Agents: {summary.total_agents ?? 0}</div>
        <div>Approved: {summary.approved_agents ?? 0}</div>
        <div>Unapproved: {summary.unapproved_agents ?? 0}</div>
      </section>

      <div style={{ overflowX: "auto" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            textAlign: "left",
          }}
        >
          <thead>
            <tr>
              <th>Agent ID</th>
              <th>Provider</th>
              <th>Capabilities</th>
              <th>Onboarding</th>
              <th>Trust</th>
              <th>Production</th>
            </tr>
          </thead>

          <tbody>
            {agents.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ padding: 16 }}>
                  No registered agents found.
                </td>
              </tr>
            ) : (
              agents.map((agent) => (
                <tr key={agent.agent_id}>
                  <td style={{ padding: 12 }}>
                    <a
                      href={`/agents/${encodeURIComponent(agent.agent_id)}`}
                      style={{ color: "#60a5fa" }}
                    >
                      {agent.agent_id}
                    </a>
                  </td>

                  <td style={{ padding: 12 }}>
                    {agent.provider || "-"}
                  </td>

                  <td style={{ padding: 12 }}>
                    {(agent.declared_capabilities || []).join(", ") || "-"}
                  </td>

                  <td style={{ padding: 12 }}>
                    {agent.onboarding_status || "-"}
                  </td>

                  <td style={{ padding: 12 }}>
                    {agent.trust_status || "-"}
                  </td>

                  <td style={{ padding: 12 }}>
                    {agent.production_approved
                      ? "Approved"
                      : "Not approved"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <p style={{ marginTop: 30, opacity: 0.7 }}>
        Read-only registry. No automatic approvals or agent execution.
      </p>
    </main>
  );
}

export default function AgentRegistryPage() {
  return (
    <Suspense
      fallback={
        <main style={{ padding: 40 }}>
          <h1>HEAAP Agent Registry</h1>
          <p>Loading registered agents...</p>
        </main>
      }
    >
      <AgentRegistryContent />
    </Suspense>
  );
}
