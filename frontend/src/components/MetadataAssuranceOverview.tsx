"use client";

import { useEffect, useState } from "react";

type AssuranceReport = {
  agent_id: string;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  score: number;
  status: string;
  executed_at?: string;
};

export default function MetadataAssuranceOverview() {
  const [report, setReport] = useState<AssuranceReport | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const response = await fetch("/api/metadata-assurance", {
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error(`Report API returned ${response.status}`);
        }

        const data = (await response.json()) as AssuranceReport;

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

  return (
    <section className="mb-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-900">
            Metadata Agent - Functional Assurance
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Automated metadata validation against the approved baseline
          </p>
        </div>

        {report && (
          <span
            className={`rounded-full px-3 py-1 text-sm font-semibold ${
              report.status === "passed"
                ? "bg-green-100 text-green-700"
                : "bg-red-100 text-red-700"
            }`}
          >
            {report.status === "passed" ? "PASSED" : "FAILED"}
          </span>
        )}
      </div>

      {!report && !error && (
        <p className="text-sm text-slate-500">
          Loading functional assurance report...
        </p>
      )}

      {error && (
        <p className="text-sm text-red-600">
          Functional assurance report unavailable: {error}
        </p>
      )}

      {report && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div className="rounded-xl bg-slate-50 p-4">
              <p className="text-sm text-slate-500">Total Tests</p>
              <p className="mt-2 text-3xl font-bold text-slate-900">
                {report.total_tests}
              </p>
            </div>

            <div className="rounded-xl bg-green-50 p-4">
              <p className="text-sm text-green-700">Passed</p>
              <p className="mt-2 text-3xl font-bold text-green-700">
                {report.passed_tests}
              </p>
            </div>

            <div className="rounded-xl bg-red-50 p-4">
              <p className="text-sm text-red-700">Failed</p>
              <p className="mt-2 text-3xl font-bold text-red-700">
                {report.failed_tests}
              </p>
            </div>

            <div className="rounded-xl bg-indigo-50 p-4">
              <p className="text-sm text-indigo-700">Assurance Score</p>
              <p className="mt-2 text-3xl font-bold text-indigo-700">
                {report.score}%
              </p>
            </div>
          </div>

          <div className="mt-5">
            <div className="mb-2 flex justify-between text-sm">
              <span className="font-medium text-slate-700">
                Functional Test Completion
              </span>
              <span className="font-bold text-green-700">
                {report.passed_tests}/{report.total_tests} Passed
              </span>
            </div>

            <div className="h-3 overflow-hidden rounded-full bg-red-100">
              <div
                className="h-full rounded-full bg-green-500 transition-all"
                style={{
                  width: `${
                    report.total_tests
                      ? (report.passed_tests / report.total_tests) * 100
                      : 0
                  }%`,
                }}
              />
            </div>
          </div>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            <div className="text-xs text-slate-500">
              <p>Agent: {report.agent_id}</p>
              {report.executed_at && (
                <p>
                  Executed:{" "}
                  {new Date(report.executed_at).toLocaleString()}
                </p>
              )}
              <p>Source: Recorded functional assurance test results</p>
            </div>

            <a
              href="/metadata-assurance"
              className="rounded-lg bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700"
            >
              View All Test Results
            </a>
          </div>
        </>
      )}
    </section>
  );
}