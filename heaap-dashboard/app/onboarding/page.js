import Link from "next/link";
const API_URL =
  process.env.HEAAP_API_URL || "http://127.0.0.1:8000";

async function getCandidates() {
  const response = await fetch(
    `${API_URL}/api/onboarding/candidates`,
    { cache: "no-store" }
  );

  if (!response.ok) {
    throw new Error("Onboarding API unavailable");
  }

  return response.json();
}

export default async function OnboardingPage() {
  let data;

  try {
    data = await getCandidates();
  } catch {
    return (
      <main style={{ padding: 40 }}>
        <h1>Agent Onboarding</h1>
        <p>Unable to retrieve onboarding records.</p>
        <Link href="/">Back to Dashboard</Link>
      </main>
    );
  }

  const candidates = data.candidates || [];
  const summary = data.summary || {};

  return (
    <main style={{ padding: 40, maxWidth: 1200, margin: "auto" }}>
      <nav>
        <Link href="/">Dashboard</Link>
        {" / "}
        <Link href="/agents">Agent Registry</Link>
        {" / "} Onboarding
      </nav>

      <h1 style={{ marginTop: 30 }}>Agent Onboarding Monitor</h1>
      <p>Read-only monitoring of discovered agent candidates.</p>

      <section style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 24,
        margin: "30px 0"
      }}>
        <div>Total Candidates: {summary.total_candidates ?? 0}</div>
        <div>Pending Review: {summary.pending_review ?? 0}</div>
        <div>Quarantined: {summary.quarantined ?? 0}</div>
        <div>Other: {summary.unknown ?? 0}</div>
      </section>

      <div style={{ overflowX: "auto" }}>
        <table style={{
          width: "100%",
          borderCollapse: "collapse",
          textAlign: "left"
        }}>
          <thead>
            <tr>
              <th>Agent ID</th>
              <th>Provider</th>
              <th>Endpoint</th>
              <th>Capabilities</th>
              <th>Status</th>
              <th>Source</th>
            </tr>
          </thead>

          <tbody>
            {candidates.length === 0 ? (
              <tr>
                <td colSpan="6" style={{ padding: 16 }}>
                  No onboarding candidates found.
                </td>
              </tr>
            ) : (
              candidates.map((candidate, index) => (
                <tr key={`${candidate.agent_id}-${index}`}>
                  <td style={{ padding: 12 }}>
                    {candidate.agent_id}
                  </td>
                  <td style={{ padding: 12 }}>
                    {candidate.provider}
                  </td>
                  <td style={{ padding: 12 }}>
                    {candidate.endpoint_name || "-"}
                  </td>
                  <td style={{ padding: 12 }}>
                    {Array.isArray(candidate.declared_capabilities)
                      ? candidate.declared_capabilities.join(", ")
                      : "-"}
                  </td>
                  <td style={{ padding: 12 }}>
                    {candidate.status}
                  </td>
                  <td style={{ padding: 12 }}>
                    {candidate.source_phase}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <p style={{ marginTop: 30, opacity: 0.7 }}>
        Discovery and capability declarations do not constitute
        authorization to execute an agent.
      </p>
    </main>
  );
}
