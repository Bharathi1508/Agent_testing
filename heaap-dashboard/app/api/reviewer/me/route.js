import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const API = process.env.HEAAP_API_URL || "http://127.0.0.1:8000";

export async function GET() {
  const token = (await cookies()).get("heaap_reviewer_session")?.value;

  if (!token) {
    return NextResponse.json({ authenticated: false }, { status: 401 });
  }

  const response = await fetch(`${API}/api/governance/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  }).catch(() => null);

  if (!response || !response.ok) {
    return NextResponse.json({ authenticated: false }, { status: 401 });
  }

  const reviewer = await response.json();

  return NextResponse.json({
    authenticated: true,
    reviewer,
  });
}
