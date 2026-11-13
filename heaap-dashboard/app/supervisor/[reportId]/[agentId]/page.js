import Link from "next/link";
import { notFound } from "next/navigation";

const API_URL =
  process.env.HEAAP_API_URL || "http://127.0.0.1:8000";

export default async function SupervisorExplanationPage({ params }) {
  const { reportId, agentId } = await params;

  const safeId = /^[A-Za-z0-9_-]{1,128}$/;

  if (!safeId.test(reportId) || !safeId.test(agentId)) {
    notFound();
  }

  let response;

  try {
    response = await fetch(
      `${API_URL}/api/supervisor/explanations/` +
      `${encodeURIComponent(reportId)}/` +
      `${encodeURIComponent(agentId)}`,
      { cache: "no-store" }
    );
  } catch {
    return <main style={{ padding: 40 }}>Backend unavailable.</main>;
  }

  if (response.status === 404) {
    notFound();
  }

  if (!response.ok) {
    return <main style={{ padding: 40 }}>Unable to load explanation.</main>;
  }

  const data = await response.json();

  return (
    <main style={{ padding: 40, maxWidth: 1100, margin: "auto" }}>
      <nav>
        <Link href="/analytics">Assurance Analytics</Link>
        {" / "} Supervisor Explanation
      </nav>

      <h1>Supervisor Decision Explanation</h1>

      <p><strong>Agent:</strong> {data.agent_id}</p>
      <p><strong>Report:</strong> {data.report_id}</p>
      <p><strong>Verdict:</strong> {data.recorded_verdict}</p>
      <p><strong>Execution mode:</strong> {data.execution_mode}</p>

      <h2>Decision Explanation</h2>
      <p>{data.explanation}</p>

      <h2>Review Indicated</h2>
      <p>{data.requires_review_by_verdict ? "Yes" : "No"}</p>

      <h2>Recorded Evidence</h2>
      <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
        {JSON.stringify(data.evidence, null, 2)}
      </pre>

      <h2>Limitations</h2>
      <ul>
        {(data.limitations || []).map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>

      <p>
        Read-only evaluation. No agent execution or production approval.
      </p>
    </main>
  );
}