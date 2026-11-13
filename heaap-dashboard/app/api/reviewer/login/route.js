import { NextResponse } from "next/server";

const API = process.env.HEAAP_API_URL || "http://127.0.0.1:8000";

export async function POST(request) {
  const { username, password } = await request.json();

  const response = await fetch(`${API}/api/governance/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
    cache: "no-store",
  }).catch(() => null);

  if (!response) {
    return NextResponse.json(
      { detail: "Authentication backend unavailable" },
      { status: 503 }
    );
  }

  if (!response.ok) {
    return NextResponse.json(
      { detail: "Invalid reviewer credentials" },
      { status: 401 }
    );
  }

  const data = await response.json();

  const result = NextResponse.json({ authenticated: true });

  result.cookies.set("heaap_reviewer_session", data.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    path: "/",
    maxAge: 900,
  });

  return result;
}
