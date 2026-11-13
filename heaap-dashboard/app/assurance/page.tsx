type Agent = {
  agent_id: string;
  total_tests: number;
  passed: number;
  failed: number;
  errors: number;
  overall_pass_rate_pct: number;
};

type Overview = {
  total_agents: number;
  total_reports: number;
  total_tests: number;
  passed: number;
  failed: number;
  errors: number;
  overall_pass_rate_pct: number;
  agents: Agent[];
};


async function getOverview(): Promise<Overview> {
  const baseUrl =
    process.env.HEAAP_API_URL ?? "http://127.0.0.1:8001";

  const response = await fetch(
    `${baseUrl}/api/assurance-dashboard/overview`,
    { cache: "no-store" }
  );

  if (!response.ok) {
    throw new Error("Unable to load assurance reports");
  }

  return response.json();
}

export default async function AssurancePage() {
  let data: Overview | null = null;
  let error: string | null = null;

  try {
    data = await getOverview();
  } catch {
    error = "HEAAP backend is unavailable.";
  }

  return (
    <main style={{ padding: 32, maxWidth: 1200, margin: "auto" }}>
      <h1>HEAAP Agent Assurance Dashboard</h1>

      <p>
        Supervisor Agent Testing and Evaluation Results
      </p>

      <p>
        Local POC test results do not represent production certification.
      </p>

      {error && <p role="alert">{error}</p>}

      {data && (
        <>
          <section
            style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit, minmax(180px, 1fr))",
              gap: 16,
              marginTop: 24,
            }}
          >
            {[
              ["Agents Evaluated", data.total_agents],
              ["Total Tests", data.total_tests],
              ["Passed", data.passed],
              ["Failed", data.failed],
              ["Errors", data.errors],
              ["Pass Rate", `${data.overall_pass_rate_pct}%`],
            ].map(([label, value]) => (
              <div
                key={String(label)}
                style={{
                  padding: 20,
                  border: "1px solid #ddd",
                  borderRadius: 10,
                }}
              >
                <div>{label}</div>
                <h2>{value}</h2>
              </div>
            ))}
          </section>

          <h2 style={{ marginTop: 32 }}>
            Agent Evaluation Results
          </h2>

          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
              }}
            >
              <thead>
                <tr>
                  {[
                    "Agent",
                    "Tests",
                    "Passed",
                    "Failed",
                    "Errors",
                    "Score",
                  ].map((header) => (
                    <th
                      key={header}
                      style={{
                        padding: 12,
                        textAlign: "left",
                        borderBottom: "1px solid #ddd",
                      }}
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {data.agents.map((agent) => (
                  <tr key={agent.agent_id}>
                    <td style={{ padding: 12 }}>
                      {agent.agent_id}
                    </td>
                    <td>{agent.total_tests}</td>
                    <td>{agent.passed}</td>
                    <td>{agent.failed}</td>
                    <td>{agent.errors}</td>
                    <td>
                      {agent.overall_pass_rate_pct}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data.agents.length === 0 && (
            <p>No evaluation reports are available yet.</p>
          )}
        </>
      )}
    </main>
  );
}

