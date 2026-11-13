import { NextResponse } from "next/server";
import { promises as fs } from "node:fs";
import path from "node:path";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const directory = path.resolve(
      process.cwd(),
      "..",
      "reports",
      "sql_functional_assurance"
    );

    const files = (await fs.readdir(directory))
      .filter((name) =>
        /^sql_functional_[\w-]+\.json$/.test(name)
      );

    if (files.length === 0) {
      return NextResponse.json(
        { error: "No SQL functional assurance reports found" },
        { status: 404 }
      );
    }

    const entries = await Promise.all(
      files.map(async (name) => ({
        name,
        modified: (await fs.stat(path.join(directory, name))).mtimeMs
      }))
    );

    entries.sort((a, b) => b.modified - a.modified);

    const raw = await fs.readFile(
      path.join(directory, entries[0].name),
      "utf8"
    );

    const report = JSON.parse(raw);

    if (
      typeof report.total_tests !== "number" ||
      typeof report.passed !== "number" ||
      typeof report.failed !== "number" ||
      !Array.isArray(report.results)
    ) {
      throw new Error("Invalid SQL assurance report format");
    }

    return NextResponse.json(
      {
        agent_id: report.agent_id,
        assurance_type: report.assurance_type,
        tested_at: report.tested_at,
        total_tests: report.total_tests,
        passed: report.passed,
        failed: report.failed,
        score: report.score,
        database_executed: report.database_executed,
        validation_scope: report.validation_scope,
        results: report.results
      },
      { headers: { "Cache-Control": "no-store" } }
    );
  } catch (error) {
    console.error("SQL assurance report loading failed:", error);

    return NextResponse.json(
      { error: "Unable to load SQL assurance report" },
      { status: 500 }
    );
  }
}
