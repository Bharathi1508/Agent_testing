import fs from "node:fs";
import path from "node:path";

export const dynamic = "force-dynamic";

type TestResult = {
  test_id: string;
  name: string;
  action: string;
  table?: string | null;
  column?: string | null;
  passed: boolean;
  latency_ms?: number;
  error?: string | null;
};

type AssuranceReport = {
  agent_id: string;
  assurance_type: string;
  executed_at: string;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  score: number;
  status: string;
  results: TestResult[];
};

function readReport(): AssuranceReport | null {
  const locations = [
    path.resolve(process.cwd(), "..", "reports", "metadata_76_actual_results.json"),
    path.resolve(process.cwd(), "reports", "metadata_76_actual_results.json"),
  ];

  for (const file of locations) {
    if (fs.existsSync(file)) {
      return JSON.parse(fs.readFileSync(file, "utf8")) as AssuranceReport;
    }
  }

  return null;
}

const card: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e2e8f0",
  borderRadius: 14,
  padding: 22,
};

export default function MetadataAssurancePage() {
  const report = readReport();

  if (!report) {
    return (
      <main style={{ padding: 32, fontFamily: "Arial, sans-serif" }}>
        <h1>Metadata Agent Assurance</h1>
        <p>No functional assurance report found.</p>
        <p>Run the 76-test suite from your HEAAP project root.</p>
        <a href="/">Back to HEAAP</a>
      </main>
    );
  }

  const results = report.results ?? [];
  const passed = report.passed_tests;
  const failed = report.failed_tests;
  const total = report.total_tests;
  const score = report.score;

  const avgLatency = results.length
    ? results.reduce((sum, item) => sum + (item.latency_ms ?? 0), 0) /
      results.length
    : 0;

  const groups = Object.entries(
    results.reduce<Record<string, { total: number; passed: number }>>(
      (acc, item) => {
        const key = item.name || item.action;
        if (!acc[key]) acc[key] = { total: 0, passed: 0 };
        acc[key].total += 1;
        if (item.passed) acc[key].passed += 1;
        return acc;
      },
      {}
    )
  );

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#f1f5f9",
        color: "#0f172a",
        padding: "28px 32px",
        fontFamily: "Arial, sans-serif",
      }}
    >
      <div style={{ maxWidth: 1300, margin: "0 auto" }}>
        <a href="/" style={{ color: "#2563eb", textDecoration: "none" }}>
          ← HEAAP Dashboard
        </a>

        <div style={{ margin: "22px 0" }}>
          <h1 style={{ fontSize: 30, marginBottom: 8 }}>
            Metadata Agent — Functional Assurance
          </h1>
          <p style={{ color: "#64748b" }}>
            Real test results from the HEAAP automated 76-case metadata suite
          </p>
        </div>

        <section
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
            gap: 16,
            marginBottom: 20,
          }}
        >
          {[
            { label: "Total Tests", value: total, color: "#0f172a" },
            { label: "Passed", value: passed, color: "#15803d" },
            { label: "Failed", value: failed, color: "#dc2626" },
            { label: "Assurance Score", value: `${score}%`, color: "#15803d" },
          ].map((metric) => (
            <div key={metric.label} style={card}>
              <div style={{ color: "#64748b", fontSize: 14 }}>
                {metric.label}
              </div>
              <div
                style={{
                  fontSize: 34,
                  fontWeight: 700,
                  color: metric.color,
                  marginTop: 12,
                }}
              >
                {metric.value}
              </div>
            </div>
          ))}
        </section>

        <section style={{ ...card, marginBottom: 20 }}>
          <h2 style={{ marginTop: 0 }}>Test Execution Summary</h2>

          <div
            style={{
              height: 16,
              background: "#fee2e2",
              borderRadius: 12,
              overflow: "hidden",
              margin: "18px 0",
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${total ? (passed / total) * 100 : 0}%`,
                background: "#16a34a",
              }}
            />
          </div>

          <p>
            <strong>{passed} passed</strong> out of {total} tests
            {failed > 0 ? ` · ${failed} failed` : " · No failures"}
          </p>
          <p style={{ color: "#64748b", fontSize: 14 }}>
            Agent: {report.agent_id} | Status: {report.status} | Average
            latency: {avgLatency.toFixed(2)} ms
          </p>
          <p style={{ color: "#64748b", fontSize: 14 }}>
            Executed: {report.executed_at || "Not recorded"}
          </p>
        </section>

        <section style={{ ...card, marginBottom: 20 }}>
          <h2 style={{ marginTop: 0 }}>Test Categories</h2>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "#f8fafc", textAlign: "left" }}>
                  {["Category", "Total", "Passed", "Failed"].map((name) => (
                    <th key={name} style={{ padding: 12 }}>{name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {groups.map(([name, counts]) => (
                  <tr key={name} style={{ borderTop: "1px solid #e2e8f0" }}>
                    <td style={{ padding: 12 }}>{name}</td>
                    <td style={{ padding: 12 }}>{counts.total}</td>
                    <td style={{ padding: 12, color: "#15803d" }}>
                      {counts.passed}
                    </td>
                    <td style={{ padding: 12, color: "#dc2626" }}>
                      {counts.total - counts.passed}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section style={card}>
          <h2 style={{ marginTop: 0 }}>Detailed Assurance Results</h2>
          <p style={{ color: "#64748b" }}>
            Individual results recorded by the Metadata Agent test runner
          </p>

          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: 14,
              }}
            >
              <thead>
                <tr style={{ background: "#f8fafc", textAlign: "left" }}>
                  {[
                    "Test ID",
                    "Test Name",
                    "Action",
                    "Table",
                    "Column",
                    "Result",
                    "Latency",
                  ].map((heading) => (
                    <th key={heading} style={{ padding: 12 }}>
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {results.map((item) => (
                  <tr
                    key={item.test_id}
                    style={{ borderTop: "1px solid #e2e8f0" }}
                  >
                    <td style={{ padding: 12 }}>{item.test_id}</td>
                    <td style={{ padding: 12 }}>{item.name}</td>
                    <td style={{ padding: 12 }}>{item.action}</td>
                    <td style={{ padding: 12 }}>{item.table || "—"}</td>
                    <td style={{ padding: 12 }}>{item.column || "—"}</td>
                    <td style={{ padding: 12 }}>
                      <span
                        style={{
                          color: item.passed ? "#15803d" : "#dc2626",
                          fontWeight: 700,
                        }}
                        title={item.error || undefined}
                      >
                        {item.passed ? "PASS" : "FAIL"}
                      </span>
                    </td>
                    <td style={{ padding: 12 }}>
                      {item.latency_ms ?? "—"} ms
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}
