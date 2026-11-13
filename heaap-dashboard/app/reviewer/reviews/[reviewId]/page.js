"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";

export default function ReviewerDecisionPage({ params }) {
  const { reviewId } = use(params);

  const [review, setReview] = useState(null);
  const [decision, setDecision] = useState("rejected");
  const [reason, setReason] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch("/api/governance/reviews", { cache: "no-store" })
      .then((res) => {
        if (!res.ok) throw new Error("Cannot load reviews");
        return res.json();
      })
      .then((data) => {
        const item = data.reviews.find(
          (entry) => entry.review_id === reviewId
        );
        setReview(item || null);
      })
      .catch(() => setMessage("Unable to load review"));
  }, [reviewId]);

  async function submit(event) {
    event.preventDefault();

    if (!confirmed || !review || review.decision) return;

    setLoading(true);
    setMessage("");

    try {
      const response = await fetch("/api/reviewer/decision", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          review_id: review.review_id,
          decision,
          reason,
          expected_sha256: review.source_sha256,
        }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Decision failed");
      }

      setMessage("Decision recorded successfully");
      setReview({ ...review, decision: result.decision });
      setConfirmed(false);
    } catch (err) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (!review) {
    return (
      <main style={{ padding: 40 }}>
        {message || "Loading review..."}
      </main>
    );
  }

  return (
    <main style={{ maxWidth: 850, margin: "40px auto", padding: 24 }}>
      <Link href="/governance">Back to Governance</Link>

      <h1>Human Review Decision</h1>

      <p><strong>Review:</strong> {review.review_id}</p>
      <p><strong>Agent:</strong> {review.agent_id || "-"}</p>
      <p><strong>Onboarding status:</strong> {review.onboarding_status}</p>
      <p><strong>Evidence SHA-256:</strong> {review.source_sha256}</p>

      <p>
        <Link href={`/onboarding/reviews/${review.review_id}`}>
          Open full onboarding evidence
        </Link>
      </p>

      {review.decision ? (
        <p>This review already has a recorded decision.</p>
      ) : (
        <form onSubmit={submit}>
          <fieldset>
            <legend>Decision</legend>

            <label>
              <input
                type="radio"
                checked={decision === "approved_for_next_stage"}
                onChange={() => setDecision("approved_for_next_stage")}
              />
              Approve for next stage
            </label>

            <label style={{ marginLeft: 20 }}>
              <input
                type="radio"
                checked={decision === "rejected"}
                onChange={() => setDecision("rejected")}
              />
              Reject
            </label>
          </fieldset>

          <p>
            <label>
              Reason
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                minLength={10}
                maxLength={2000}
                required
                rows={5}
                style={{ display: "block", width: "100%" }}
              />
            </label>
          </p>

          <label>
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
            I have reviewed the evidence and confirm this decision.
          </label>

          <p>
            <button disabled={!confirmed || loading} type="submit">
              {loading ? "Submitting..." : "Record decision"}
            </button>
          </p>
        </form>
      )}

      {message && <p role="status">{message}</p>}

      <p>
        This decision does not grant production approval or
        authorize live agent execution.
      </p>
    </main>
  );
}
