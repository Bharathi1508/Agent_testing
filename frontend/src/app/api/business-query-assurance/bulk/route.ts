import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const questions = body?.questions;

    if (
      !Array.isArray(questions) ||
      questions.length < 1 ||
      questions.length > 100 ||
      questions.some(
        (question: unknown) =>
          typeof question !== "string" ||
          question.trim().length < 1 ||
          question.length > 2000
      )
    ) {
      return NextResponse.json(
        { detail: "Provide 1 to 100 non-empty questions, each up to 2000 characters." },
        { status: 400 }
      );
    }

    const base = (
      process.env.HEAAP_API_URL || "http://127.0.0.1:8000"
    ).replace(/\/$/, "");
    const response = await fetch(
      `${base}/api/heaap/pipeline/validate/bulk`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ questions }),
        cache: "no-store",
        signal: AbortSignal.timeout(600000),
      }
    );
    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Bulk business query assurance error:", error);
    return NextResponse.json(
      { detail: "Unable to contact the HEAAP bulk assurance pipeline." },
      { status: 502 }
    );
  }
}
