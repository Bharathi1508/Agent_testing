import Link from "next/link";
const API_URL =
  process.env.HEAAP_API_URL || "http://127.0.0.1:8000";

async function getAnalytics() {
  const response = await fetch(
    `${API_URL}/api/analytics/assurance`,
    { cache: "no-store" }
  );

  if (!response.ok) {
    throw new Error("Analytics API unavailable");
  }

  return response.json();
}

function MetricCard({ label, value }) {
  return (
    <article style={{
      padding: 24,
      border: "1px solid #475569",
      borderRadius: 12,
    }}>
      <p>{label}</p>
      <h2>{value}</h2>
    </article>
  );
}

export default async function AssuranceAnalyticsPage() {
  let data;

  try {
    data = await getAnalytics();
  } catch {
    return (
      <main style={{ padding: 40 }}>
        <h1>Assurance Analytics</h1>
        <p>Unable to connect to the analytics API.</p>
      </main>
    );
  }

  const summary = data.summary || {};
  const agents = data.agents || [];
  const trend = data.trend || [];

  const cards = [
    ["Reports", summary.total_reports],
    ["Unique Agents", summary.unique_agents],
    ["Evaluations", summary.total_evaluations],
    ["Passed", summary.passed],
    ["Failed", summary.failed],
    ["Unsupported", summary.unsupported],
    ["Pass Rate", `${summary.pass_rate_pct ?? 0}%`],
  ];

  return (
    <main style={{
      padding: 40,
      maxWidth: 1200,
      margin: "auto",
    }}>
      <nav>
        <Link href="/">Dashboard</Link>
        {" / "} Analytics
      </nav>

      <h1 style={{ marginTop: 30 }}>Agent Assurance Analytics</h1>
      <p>Offline mock evaluation results — read-only.</p>

      <section style={{
        display: "grid",
        gridTemplateColumns:
          "repeat(auto-fit, minmax(180px, 1fr))",
        gap: 16,
        marginTop: 30,
      }}>
        {cards.map(([label, value]) => (
          <MetricCard
            key={label}
            label={label}
            value={value ?? 0}
          />
        ))}
      </section>

      <h2 style={{ marginTop: 40 }}>Agent Performance</h2>

      <div style={{ overflowX: "auto" }}>
        <table style={{
          width: "100%",
          borderCollapse: "collapse",
          textAlign: "left",
        }}>
          <thead>
            <tr>
              <th>Agent ID</th>
              <th>Evaluations</th>
              <th>Passed</th>
              <th>Failed</th>
              <th>Unsupported</th>
            </tr>
          </thead>

          <tbody>
            {agents.map((agent) => (
              <tr key={agent.agent_id}>
                <td style={{ padding: 12 }}>
                  <Link href={`/agents/${encodeURIComponent(
                    agent.agent_id
                  )}`}>
                    {agent.agent_id}
                  </Link>
                </td>
                <td>{agent.evaluations}</td>
                <td>{agent.passed}</td>
                <td>{agent.failed}</td>
                <td>{agent.unsupported}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 style={{ marginTop: 40 }}>Evaluation Trend</h2>

      {trend.length === 0 ? (
        <p>No assurance reports available.</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{
            width: "100%",
            borderCollapse: "collapse",
            textAlign: "left",
          }}>
            <thead>
              <tr>
                <th>Report</th>
                <th>Date</th>
                <th>Passed</th>
                <th>Failed</th>
                <th>Unsupported</th>
              </tr>
            </thead>
            <tbody>
              {trend.map((item, index) => (
                <tr key={`${item.report_id}-${index}`}>
                  <td style={{ padding: 12 }}>
                    {item.report_id}
                  </td>
                  <td>{item.created_at || "-"}</td>
                  <td>{item.passed}</td>
                  <td>{item.failed}</td>
                  <td>{item.unsupported}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
