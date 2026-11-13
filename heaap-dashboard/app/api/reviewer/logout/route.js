import { NextResponse } from "next/server";

export async function POST() {
  const response = NextResponse.json({ logged_out: true });

  response.cookies.set("heaap_reviewer_session", "", {
    httpOnly: true,
    sameSite: "strict",
    path: "/",
    maxAge: 0,
  });

  return response;
}
