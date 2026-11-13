import { NextResponse } from "next/server";
import fs from "node:fs";
import path from "node:path";

export const dynamic = "force-dynamic";

export async function GET() {
  const locations = [
    path.resolve(
      process.cwd(),
      "..",
      "reports",
      "metadata_76_actual_results.json"
    ),
    path.resolve(
      process.cwd(),
      "reports",
      "metadata_76_actual_results.json"
    ),
  ];

  const file = locations.find((item) => fs.existsSync(item));

  if (!file) {
    return NextResponse.json(
      { error: "Metadata assurance report not found" },
      { status: 404 }
    );
  }

  try {
    const report = JSON.parse(fs.readFileSync(file, "utf8"));

    return NextResponse.json(
      {
        agent_id: report.agent_id,
        total_tests: report.total_tests,
        passed_tests: report.passed_tests,
        failed_tests: report.failed_tests,
        score: report.score,
        status: report.status,
        executed_at: report.executed_at,
        results: report.results,
      },
      {
        headers: { "Cache-Control": "no-store" },
      }
    );
  } catch {
    return NextResponse.json(
      { error: "Unable to read assurance report" },
      { status: 500 }
    );
  }
}