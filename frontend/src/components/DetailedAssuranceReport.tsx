"use client";

import { useCallback, useEffect, useState } from "react";

type Check = {
  name?: string;
  test_id?: string;
  capability?: string;
  passed?: boolean;
  message?: string;
  errors?: string[];
  latency_ms?: number;
};

type Evidence = {
  assurance_type?: string;
  evaluation_context?: string;
  registry_status?: string;
  total_checks?: number;
  passed_checks?: number;
  total_tests?: number;
  passed_tests?: number;
  failed_tests?: number;
  checks?: Check[];
  results?: Check[];
};

type Run = {
  id: number;
  agent_id: string;
  status: string;
  created_at: string;
  score: number | null;
  assurance_type: string | null;
  passed_checks?: number | null;
  total_checks?: number | null;
  report?: Evidence;
};

function dateText(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString("en-IN", {
        timeZone: "Asia/Kolkata",
        dateStyle: "medium",
        timeStyle: "medium"
      });
}

function suggestedAction(check: Check, run: Run) {
  if (check.passed === true) return "No corrective action indicated.";

  if (
    check.name === "inactive_status" &&
    run.report?.evaluation_context === "existing_active_agent"
  ) {
    return "Review whether this active agent should use a periodic assurance suite instead of a pre-activation suite. Do not automatically deactivate the agent.";
  }

  if (check.name === "manifest_validation")
    return "Review the manifest validation errors and required fields.";

  if (check.name === "capability_declaration")
    return "Verify that the declared capabilities match the implementation.";

  if (check.name === "execution_configuration")
    return "Review the execution settings and recorded errors.";

  return "Investigate the recorded failure and verify the agent behavior.";
}

export default function DetailedAssuranceReport() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(
        "/api/heaap/api/assurance/live/reports",
        { cache: "no-store" }
      );

      if (!response.ok) {
        throw new Error(`Reports API returned HTTP ${response.status}`);
      }

      const data: unknown = await response.json();

      if (
        !data ||
        typeof data !== "object" ||
        !("reports" in data) ||
        !Array.isArray(data.reports)
      ) {
        throw new Error("Invalid reports API response");
      }

      const list = (data.reports as Run[])
        .slice()
        .sort((a, b) => b.id - a.id);

      setRuns(list);
      setSelected(previous =>
        list.some(r => r.id === previous)
          ? previous
          : list[0]?.id ?? null
      );
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load reports");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const run = runs.find(r => r.id === selected);
  const checks = run?.report?.checks ?? run?.report?.results ?? [];
  const passed = checks.filter(c => c.passed === true).length;
  const failed = checks.filter(c => c.passed === false).length;
  const failedChecks = checks.filter(c => c.passed === false);

  const exportReport = () => {
    if (!run) return;
    const blob = new Blob(
      [JSON.stringify(run, null, 2)],
      { type: "application/json" }
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `HEAAP_Actual_Report_${run.id}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mt-6 space-y-5 rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">
            Detailed Assurance Report - Actual Results
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Actual evidence retrieved from persisted HEAAP assurance runs
          </p>
        </div>
        <button
          onClick={() => void load()}
          disabled={loading}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          Refresh Actual Results
        </button>
      </div>

      {loading && <p className="text-sm">Loading actual results...</p>}
      {error && <p className="text-sm text-red-700">{error}</p>}

      {runs.length === 0 && !loading && !error && (
        <p className="text-sm text-slate-500">No stored assurance runs.</p>
      )}

      {runs.length > 0 && (
        <div>
          <label className="mb-2 block text-sm font-semibold">
            Select Test Run
          </label>
          <select
            className="w-full rounded-lg border border-slate-300 p-3 text-sm"
            value={selected ?? ""}
            onChange={e => setSelected(Number(e.target.value))}
          >
            {runs.map(r => (
              <option key={r.id} value={r.id}>
                Run #{r.id} | {r.agent_id} | {r.status.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
      )}

      {run && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["Run ID", `#${run.id}`],
              ["Overall Result", run.status.toUpperCase()],
              ["Checks Passed", `${passed}/${checks.length}`],
              ["Recorded Score", run.score == null ? "Not recorded" : `${run.score}%`]
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg bg-slate-50 p-4">
                <p className="text-xs text-slate-500">{label}</p>
                <p className="mt-2 break-words text-lg font-bold">{value}</p>
              </div>
            ))}
          </div>

          <section className="rounded-lg border p-4">
            <h3 className="mb-3 text-lg font-bold">1. Execution Summary</h3>
            <div className="space-y-2 text-sm">
              <p><strong>Agent:</strong> {run.agent_id}</p>
              <p><strong>Executed:</strong> {dateText(run.created_at)}</p>
              <p><strong>Test Type:</strong> {run.assurance_type ?? "Agent execution test"}</p>
              <p><strong>Registry Status:</strong> {run.report?.registry_status ?? "Not recorded"}</p>
              <p><strong>Evaluation Context:</strong> {run.report?.evaluation_context ?? "Not recorded"}</p>
              <p><strong>Overall Status:</strong> {run.status.toUpperCase()}</p>
            </div>
          </section>

          <section className="rounded-lg border p-4">
            <h3 className="mb-3 text-lg font-bold">
              2. Actual Individual Test Results
            </h3>

            <div className="mb-4 flex flex-wrap gap-3 text-sm">
              <span className="rounded bg-green-100 px-3 py-2 text-green-800">
                Passed: {passed}
              </span>
              <span className="rounded bg-red-100 px-3 py-2 text-red-800">
                Failed: {failed}
              </span>
              <span className="rounded bg-slate-100 px-3 py-2">
                Total recorded checks: {checks.length}
              </span>
            </div>

            {checks.length === 0 && (
              <p className="text-sm text-slate-500">
                Individual test evidence was not recorded for this run.
              </p>
            )}

            <div className="space-y-3">
              {checks.map((check, index) => (
                <div key={index} className="rounded-lg border p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h4 className="font-semibold">
                      {index + 1}. {check.name ?? check.test_id ?? "Unnamed test"}
                    </h4>
                    <span className={`rounded-full px-3 py-1 text-xs font-bold ${
                      check.passed === true
                        ? "bg-green-100 text-green-800"
                        : check.passed === false
                          ? "bg-red-100 text-red-800"
                          : "bg-slate-100 text-slate-700"
                    }`}>
                      {check.passed === true
                        ? "PASSED"
                        : check.passed === false
                          ? "FAILED"
                          : "UNKNOWN"}
                    </span>
                  </div>

                  {check.test_id && (
                    <p className="mt-2 text-xs">Test ID: {check.test_id}</p>
                  )}

                  {check.capability && (
                    <p className="mt-2 text-xs">
                      Capability: {check.capability}
                    </p>
                  )}

                  <div className="mt-3 rounded bg-slate-50 p-3 text-sm">
                    <p className="font-semibold">Actual Recorded Evidence</p>
                    <p className="mt-1">
                      {check.message ?? (
                        check.errors?.length
                          ? check.errors.join("; ")
                          : "No detailed response evidence was recorded."
                      )}
                    </p>

                    <p className="mt-2 text-xs text-slate-500">
                      Recorded errors: {check.errors?.length
                        ? check.errors.join("; ")
                        : "None recorded"}
                    </p>

                    {check.latency_ms != null && (
                      <p className="mt-2 text-xs">
                        Execution latency: {check.latency_ms.toFixed(2)} ms
                      </p>
                    )}
                  </div>

                  <div className="mt-3 rounded border border-slate-200 p-3 text-sm">
                    <p className="font-semibold">
                      Suggested Corrective Action
                    </p>
                    <p className="mt-1 text-slate-600">
                      {suggestedAction(check, run)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-lg border p-4">
            <h3 className="mb-3 text-lg font-bold">
              3. Actual Failure Analysis
            </h3>

            {failedChecks.length === 0 ? (
              <p className="text-sm text-green-700">
                No failed checks were recorded in this run.
              </p>
            ) : (
              <div className="space-y-3">
                {failedChecks.map((check, index) => (
                  <div key={index} className="rounded-lg bg-red-50 p-3">
                    <p className="text-sm font-bold text-red-800">
                      {check.name ?? check.test_id ?? "Failed test"}
                    </p>
                    <p className="mt-1 text-sm text-red-700">
                      {check.message ??
                        check.errors?.join("; ") ??
                        "No failure explanation recorded"}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="rounded-lg border p-4">
            <h3 className="mb-3 text-lg font-bold">
              4. Report Interpretation
            </h3>
            <p className="text-sm text-slate-700">
              This report shows recorded assurance results and test evidence.
              A configuration-check score is not a measurement of SQL accuracy,
              metadata correctness or business-query accuracy.
            </p>
            <p className="mt-2 text-xs text-slate-500">
              Corrective recommendations are advisory and do not modify
              agent configuration, status or governance approval.
            </p>
          </section>

          <button
            onClick={exportReport}
            className="rounded-lg bg-indigo-600 px-5 py-3 text-sm font-semibold text-white"
          >
            Export Actual Report JSON
          </button>
        </>
      )}
    </div>
  );
}