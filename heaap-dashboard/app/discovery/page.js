
async function getCandidates() {
  const baseUrl =
    process.env.HEAAP_API_URL || "http://127.0.0.1:8001";

  const response = await fetch(
    `${baseUrl}/api/discovery/candidates`,
    { cache: "no-store" }
  );

  if (!response.ok) {
    throw new Error("Unable to load discovered agents");
  }

  return response.json();
}

export default async function DiscoveryPage() {
  let data;
  let error = null;

  try {
    data = await getCandidates();
  } catch (err) {
    error = err.message;
  }

  const candidates = data?.candidates || [];
  const summary = data?.summary || {};

  return (
    <main style={{
      padding: "32px",
      maxWidth: "1200px",
      margin: "0 auto"
    }}>
      <p style={{ color: "#64748b" }}>
        HEAAP / Agent Discovery
      </p>

      <h1>Dynamic Agent Discovery</h1>

      <p style={{ color: "#64748b" }}>
        Review newly discovered agent manifests before
        onboarding and registration.
      </p>

      {error && (
        <p role="alert" style={{ color: "#dc2626" }}>
          {error}
        </p>
      )}

      <section style={{
        display: "flex",
        gap: "16px",
        marginTop: "24px",
        marginBottom: "24px",
        flexWrap: "wrap"
      }}>
        {[
          ["Total Candidates", summary.total_candidates ?? 0],
          ["Valid Manifests", summary.valid_manifests ?? 0],
          ["Invalid Manifests", summary.invalid_manifests ?? 0]
        ].map(([label, value]) => (
          <div key={label} style={{
            padding: "20px",
            border: "1px solid #e2e8f0",
            borderRadius: "12px",
            minWidth: "180px"
          }}>
            <div style={{ color: "#64748b" }}>{label}</div>
            <strong style={{ fontSize: "28px" }}>{value}</strong>
          </div>
        ))}
      </section>

      <section style={{ overflowX: "auto" }}>
        <h2>Discovered Candidates</h2>

        <table style={{
          width: "100%",
          borderCollapse: "collapse",
          textAlign: "left"
        }}>
          <thead>
            <tr>
              {[
                "Agent ID",
                "Framework",
                "Capabilities",
                "Discovery Status",
                "Trust Status"
              ].map((heading) => (
                <th key={heading} style={{
                  padding: "12px",
                  borderBottom: "1px solid #cbd5e1"
                }}>
                  {heading}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {candidates.map((agent, index) => (
              <tr key={`${agent.source_file}-${index}`}>
                <td style={{ padding: "12px" }}>
                  {agent.agent_id || agent.source_file}
                </td>
                <td style={{ padding: "12px" }}>
                  {agent.framework || "Unknown"}
                </td>
                <td style={{ padding: "12px" }}>
                  {(agent.declared_capabilities || []).join(", ") || "—"}
                </td>
                <td style={{ padding: "12px" }}>
                  {agent.discovery_status}
                </td>
                <td style={{ padding: "12px" }}>
                  {agent.trust_status || "Unverified"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {!error && candidates.length === 0 && (
          <p>No discovered agents found.</p>
        )}
      </section>

      <p style={{
        marginTop: "24px",
        color: "#64748b",
        fontSize: "14px"
      }}>
        Discovery is read-only. Candidate agents are not
        automatically approved, registered, or executed.
      </p>
    </main>
  );
}

