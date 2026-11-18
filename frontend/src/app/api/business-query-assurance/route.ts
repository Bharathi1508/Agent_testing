import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    if (
      typeof body.question !== "string" ||
      !body.question.trim()
    ) {
      return NextResponse.json(
        { detail: "A business question is required." },
        { status: 400 }
      );
    }

    const base = (
      process.env.HEAAP_API_URL ||
      "http://127.0.0.1:8000"
    ).replace(/\/$/, "");

    const response = await fetch(
      `${base}/api/heaap/pipeline/validate`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: body.question.trim() }),
        cache: "no-store",
        signal: AbortSignal.timeout(120000),
      }
    );

    const data = await response.json();

    return NextResponse.json(data, {
      status: response.status,
    });
  } catch (error) {
    console.error("Business query assurance error:", error);

    return NextResponse.json(
      { detail: "Unable to contact the HEAAP pipeline." },
      { status: 502 }
    );
  }
}
