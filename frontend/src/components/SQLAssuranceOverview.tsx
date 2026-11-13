"use client";

import { useEffect, useState } from "react";

type TestResult = {
  question: string;
  test_type: string;
  status: string;
  expected_sql?: string;
  expected_behavior?: string;
  actual_sql?: string;
  error_code?: string | null;
};

type SQLReport = {
  agent_id: string;
  assurance_type: string;
  tested_at: string;
  total_tests: number;
  passed: number;
  failed: number;
  score: number;
  database_executed: boolean;
  validation_scope: string;
  results: TestResult[];
};

export default function SQLAssuranceOverview() {
  const [report, setReport] = useState<SQLReport | null>(null);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const response = await fetch("/api/sql-assurance", {
          cache: "no-store"
        });

        if (!response.ok) {
          throw new Error(`Report API returned ${response.status}`);
        }

        const data: SQLReport = await response.json();

        if (active) {
          setReport(data);
          setError("");
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error ? err.message : "Unable to load report"
          );
        }
      }
    }

    void load();

    return () => {
      active = false;
    };
  }, []);

  const passed = report !== null &&
    report.total_tests > 0 &&
    report.passed === report.total_tests &&
    report.failed === 0;

  return (
    <section className="mb-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-900">
            SQL Agent - Functional Assurance
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Automated SQL template behavior validation
          </p>
        </div>

        {report && (
          <span className={`rounded-full px-3 py-1 text-sm font-semibold ${
            passed
              ? "bg-green-100 text-green-700"
              : "bg-red-100 text-red-700"
          }`}>
            {passed ? "PASSED" : "FAILED"}
          </span>
        )}
      </div>

      {!report && !error && <p>Loading SQL assurance report...</p>}

      {error && (
        <p className="text-sm text-red-600">
          SQL assurance report unavailable: {error}
        </p>
      )}

      {report && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {[
              ["Total Tests", report.total_tests, "bg-slate-50 text-slate-900"],
              ["Passed", report.passed, "bg-green-50 text-green-700"],
              ["Failed", report.failed, "bg-red-50 text-red-700"],
              ["Assurance Score", `${report.score}%`, "bg-indigo-50 text-indigo-700"]
            ].map(([label, value, color]) => (
              <div key={String(label)} className={`rounded-xl p-4 ${color}`}>
                <p className="text-sm">{label}</p>
                <p className="mt-2 text-3xl font-bold">{value}</p>
              </div>
            ))}
          </div>

          <div className="mt-5">
            <div className="mb-2 flex justify-between text-sm">
              <span>Functional Test Completion</span>
              <span className="font-bold">
                {report.passed}/{report.total_tests} Passed
              </span>
            </div>

            <div className="h-3 overflow-hidden rounded-full bg-red-100">
              <div
                className="h-full rounded-full bg-green-500"
                style={{
                  width: `${
                    report.total_tests
                      ? (report.passed / report.total_tests) * 100
                      : 0
                  }%`
                }}
              />
            </div>
          </div>

          <div className="mt-5 space-y-1 text-xs text-slate-500">
            <p>Agent: {report.agent_id}</p>
            <p>Executed: {new Date(report.tested_at).toLocaleString()}</p>
            <p>Validation scope: {report.validation_scope}</p>
            <p>Database executed: {report.database_executed ? "Yes" : "No"}</p>
          </div>

          <button
            onClick={() => setExpanded(!expanded)}
            className="mt-5 rounded-lg bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700"
          >
            {expanded ? "Hide Test Results" : "View All Test Results"}
          </button>

          {expanded && (
            <div className="mt-5 space-y-3">
              {report.results.map((test, index) => (
                <div key={index} className="rounded-lg border border-slate-200 p-4">
                  <div className="flex justify-between gap-3">
                    <p className="font-semibold text-sm">{test.question}</p>
                    <span className={
                      test.status === "passed"
                        ? "text-green-700"
                        : "text-red-700"
                    }>
                      {test.status}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    {test.test_type}
                  </p>
                  {test.actual_sql && (
                    <pre className="mt-2 overflow-x-auto rounded bg-slate-50 p-3 text-xs">
                      {test.actual_sql}
                    </pre>
                  )}
                  {test.error_code && (
                    <p className="mt-2 text-xs">
                      Error code: {test.error_code}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}
