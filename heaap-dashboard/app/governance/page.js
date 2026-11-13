import Link from "next/link";

const API_URL =
  process.env.HEAAP_API_URL || "http://127.0.0.1:8000";

export default async function GovernancePage() {
  let reviews = [];
  let error = null;

  try {
    const response = await fetch(
      `${API_URL}/api/governance/reviews`,
      { cache: "no-store" }
    );

    if (!response.ok) {
      throw new Error("Governance API unavailable");
    }

    const data = await response.json();
    reviews = data.reviews || [];
  } catch {
    error = "Unable to retrieve governance records.";
  }

  const pending = reviews.filter(
    (r) => !r.decision
  ).length;

  const approved = reviews.filter(
    (r) => r.decision?.decision === "approved_for_next_stage"
  ).length;

  const rejected = reviews.filter(
    (r) => r.decision?.decision === "rejected"
  ).length;

  return (
    <main style={{
      padding: 40,
      maxWidth: 1200,
      margin: "auto"
    }}>
      <nav>
        <Link href="/">Dashboard</Link>
        {" / "}
        <Link href="/onboarding/reviews">
          Onboarding Reviews
        </Link>
        {" / "} Governance
      </nav>

      <h1 style={{ marginTop: 30 }}>
        Enterprise Governance
      </h1>

      <p>Human review decisions and audit records</p>
      <p>Local prototype — read-only dashboard</p>

      {error && <p role="alert">{error}</p>}

      <section style={{
        display: "flex",
        gap: 24,
        flexWrap: "wrap",
        margin: "30px 0"
      }}>
        <div>Total: {reviews.length}</div>
        <div>Undecided: {pending}</div>
        <div>Approved for next stage: {approved}</div>
        <div>Rejected: {rejected}</div>
      </section>

      <div style={{ overflowX: "auto" }}>
        <table style={{
          width: "100%",
          borderCollapse: "collapse",
          textAlign: "left"
        }}>
          <thead>
            <tr>
              <th>Review</th>
              <th>Agent</th>
              <th>Onboarding</th>
              <th>Decision</th>
              <th>Reviewer</th>
              <th>Timestamp</th>
            </tr>
          </thead>

          <tbody>
            {reviews.map((review) => (
              <tr key={review.review_id}>
                <td style={{ padding: 12 }}>
                  <Link href={
                    `/onboarding/reviews/${encodeURIComponent(
                      review.review_id
                    )}`
                  }>
                    {review.review_id}
                  </Link>
                </td>

                <td>
  {review.agent_id || "-"}

  <div>
    <Link href={`/reviewer/reviews/${encodeURIComponent(review.review_id)}`}>
      Review Decision
    </Link>
  </div>
</td>
                <td>{review.onboarding_status}</td>
                <td>
                  {review.decision?.decision || "Undecided"}
                </td>
                <td>
                  {review.decision?.reviewer || "-"}
                </td>
                <td>
                  {review.decision?.decided_at || "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {!error && reviews.length === 0 && (
        <p>No governance reviews found.</p>
      )}

      <p style={{ marginTop: 30 }}>
        Approval for the next stage does not authorize
        production deployment or live agent execution.
      </p>
    </main>
  );
}
