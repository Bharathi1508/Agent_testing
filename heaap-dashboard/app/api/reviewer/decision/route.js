import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const API = process.env.HEAAP_API_URL || "http://127.0.0.1:8000";

export async function POST(request) {
  const token = (await cookies()).get("heaap_reviewer_session")?.value;

  if (!token) {
    return NextResponse.json(
      { detail: "Reviewer login required" },
      { status: 401 }
    );
  }

  const origin = request.headers.get("origin");
  const expectedOrigin = new URL(request.url).origin;

  if (origin !== expectedOrigin) {
    return NextResponse.json(
      { detail: "Invalid request origin" },
      { status: 403 }
    );
  }

  const body = await request.json();

  const { review_id, decision, reason, expected_sha256 } = body;

  if (
    typeof review_id !== "string" ||
    !/^[A-Za-z0-9_-]{1,128}$/.test(review_id)
  ) {
    return NextResponse.json(
      { detail: "Invalid review ID" },
      { status: 400 }
    );
  }

  const response = await fetch(
    `${API}/api/governance/reviews/${review_id}/decision`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        decision,
        reason,
        expected_sha256,
      }),
      cache: "no-store",
    }
  ).catch(() => null);

  if (!response) {
    return NextResponse.json(
      { detail: "Governance backend unavailable" },
      { status: 503 }
    );
  }

  const result = await response.json();

  return NextResponse.json(result, {
    status: response.status,
  });
}
