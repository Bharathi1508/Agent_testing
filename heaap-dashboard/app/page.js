import { Suspense } from "react";
import {
  getAssuranceSummary,
  getAssuranceReports,
} from "../lib/assurance-api";
async function DashboardContent() {
  let summary;
  let reports;

  try {
    [summary, reports] = await Promise.all([
      getAssuranceSummary(),
      getAssuranceReports(),
    ]);
  } catch {
    return (
      <main style={{ padding: 40 }}>
        <h1>HEAAP Dashboard</h1>
        <p>Unable to connect to the FastAPI backend.</p>
        <p>Start the backend on port 8000 and refresh.</p>
      </main>
    );
  }

  const cards = [
    ["Total Reports", summary.total_reports],
    ["Unique Agents", summary.unique_agents],
    ["Passed", summary.passed],
    ["Failed", summary.failed],
  ];

  return (
    <main style={{ padding: 40, maxWidth: 1200, margin: "auto" }}>
      <h1>HEAAP Assurance Dashboard</h1>
      <p>Hybrid Enterprise Agent Assurance Platform</p>
      <p>Execution mode: Offline mock | Read-only</p>

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 16,
          marginTop: 30,
        }}
      >
        {cards.map(([label, value]) => (
          <article
            key={label}
            style={{
              padding: 24,
              border: "1px solid #64748b",
              borderRadius: 12,
            }}
          >
            <p>{label}</p>
            <h2>{value ?? 0}</h2>
          </article>
        ))}
      </section>

      <h2 style={{ marginTop: 40 }}>Assurance Reports</h2>

      {reports.length === 0 ? (
        <p>No assurance reports available yet.</p>
      ) : (
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
                <th>Report ID</th>
                <th>Agents</th>
                <th>Overall Verdict</th>
                <th>Created At</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((report) => (
                <tr key={report.report_id}>
                  <td style={{ padding: 12 }}>
                    {report.report_id}
                  </td>
                  <td style={{ padding: 12 }}>
                    {report.total_agents ?? report.agents?.length ?? 0}
                  </td>
                  <td style={{ padding: 12 }}>
                    {report.overall_verdict}
                  </td>
                  <td style={{ padding: 12 }}>
                    {report.created_at || "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}

export default function HomePage() {
  return (
    <Suspense fallback={
      <main style={{ padding: 40 }}>
        <h1>HEAAP Assurance Dashboard</h1>
        <p>Loading assurance summary...</p>
      </main>
    }>
      <DashboardContent />
    </Suspense>
  );
}