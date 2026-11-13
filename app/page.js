import { getDashboardData } from "../lib/assurance-api";
import styles from "./page.module.css";

export const dynamic = "force-dynamic";

function Status({ value }) {
  const normalized = String(value || "UNKNOWN").toUpperCase();

  const className =
    normalized === "PASS"
      ? styles.pass
      : normalized === "FAIL"
      ? styles.fail
      : styles.unknown;

  return <span className={className}>{normalized}</span>;
}

export default async function Home() {
  let data;
  let error = null;

  try {
    data = await getDashboardData();
  } catch (err) {
    error = "Cannot connect to the HEAAP FastAPI backend.";
  }

  if (error) {
    return (
      <main className={styles.container}>
        <h1>HEAAP Assurance Dashboard</h1>
        <p className={styles.error}>{error}</p>
        <p>
          Start the FastAPI server on port 8000 and refresh this page.
        </p>
      </main>
    );
  }

  const { summary, reports } = data;

  const evaluations = reports.flatMap((report) =>
    (report.agents || []).map((agent) => ({
      ...agent,
      report_id: report.report_id,
      evaluated_at: report.created_at,
    }))
  );

  const metrics = [
    ["Total Reports", summary.total_reports],
    ["Unique Agents", summary.unique_agents],
    ["Passed Evaluations", summary.passed],
    ["Failed Evaluations", summary.failed],
  ];

  return (
    <main className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1>HEAAP</h1>
          <p>Hybrid Enterprise Agent Assurance Platform</p>
        </div>
        <span className={styles.mode}>OFFLINE MOCK</span>
      </header>

      <section className={styles.intro}>
        <h2>Assurance Overview</h2>
        <p>
          Read-only monitoring of agent contract evaluations
          and supervisor assurance reports.
        </p>
      </section>

      <section className={styles.metrics}>
        {metrics.map(([label, value]) => (
          <article className={styles.metric} key={label}>
            <span>{label}</span>
            <strong>{value ?? 0}</strong>
          </article>
        ))}
      </section>

      <section className={styles.panel}>
        <h2>Agent Assurance Results</h2>

        <div className={styles.tableWrap}>
          <table>
            <thead>
              <tr>
                <th>Agent ID</th>
                <th>Verdict</th>
                <th>Passed Tests</th>
                <th>Failed Tests</th>
                <th>Report ID</th>
              </tr>
            </thead>
            <tbody>
              {evaluations.length === 0 ? (
                <tr>
                  <td colSpan="5">
                    No assurance reports available.
                  </td>
                </tr>
              ) : (
                evaluations.map((agent, index) => (
                  <tr key={`${agent.report_id}-${agent.agent_id}-${index}`}>
                    <td>{agent.agent_id}</td>
                    <td><Status value={agent.verdict} /></td>
                    <td>{agent.passed ?? 0}</td>
                    <td>{agent.failed ?? 0}</td>
                    <td>{agent.report_id}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className={styles.panel}>
        <h2>Supervisor Assurance History</h2>

        {reports.length === 0 ? (
          <p>No saved supervisor reports found.</p>
        ) : (
          <div className={styles.history}>
            {reports.map((report) => (
              <article
                className={styles.historyItem}
                key={report.report_id}
              >
                <div>
                  <strong>{report.report_id}</strong>
                  <p>{report.created_at || "Date unavailable"}</p>
                </div>
                <Status value={report.overall_verdict} />
              </article>
            ))}
          </div>
        )}
      </section>

      <footer className={styles.footer}>
        Contract results are mock evaluations, not production
        authorization or independent capability verification.
      </footer>
    </main>
  );
}
