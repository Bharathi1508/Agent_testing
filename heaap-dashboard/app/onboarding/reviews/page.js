import Link from "next/link";
const API_URL =
  process.env.HEAAP_API_URL || "http://127.0.0.1:8000";

export default async function OnboardingReviewsPage() {
  let reviews = [];
  let error = null;

  try {
    const response = await fetch(
      `${API_URL}/api/onboarding/reviews`,
      { cache: "no-store" }
    );

    if (!response.ok) {
      throw new Error("Review API unavailable");
    }

    const data = await response.json();
    reviews = data.reviews || [];
  } catch {
    error = "Unable to load onboarding reviews.";
  }

  return (
    <main style={{ padding: 40, maxWidth: 1100, margin: "auto" }}>
      <nav>
        <Link href="/">Dashboard</Link>
        {" / "}
        <Link href="/onboarding">Onboarding</Link>
        {" / "} Reviews
      </nav>

      <h1 style={{ marginTop: 30 }}>Onboarding Reviews</h1>
      <p>Inspect existing agent onboarding decisions and evidence.</p>

      {error && <p role="alert">{error}</p>}

      {!error && reviews.length === 0 && (
        <p>No onboarding review documents found.</p>
      )}

      {reviews.map((review) => (
        <article
          key={review.review_id}
          style={{
            padding: 20,
            marginTop: 16,
            border: "1px solid #64748b",
            borderRadius: 12,
          }}
        >
          <h2>
            <Link
              href={`/onboarding/reviews/${encodeURIComponent(
                review.review_id
              )}`}
            >
              {review.review_id}
            </Link>
          </h2>

          <p>Agent: {review.agent_id || "Unknown"}</p>
          <p>Status: {review.status}</p>
          <p>
            Execution authorized in record:{" "}
            {review.execution_authorized ? "Yes" : "No"}
          </p>
          <p>
            Production approved in record:{" "}
            {review.production_approved ? "Yes" : "No"}
          </p>
        </article>
      ))}
    </main>
  );
}
