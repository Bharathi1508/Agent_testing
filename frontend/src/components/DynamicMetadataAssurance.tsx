"use client";

import { useCallback, useEffect, useState } from "react";

type TableResult = {
  table: string;
  status: string;
  column_count: number;
  error?: string | null;
  checks?: {
    missing_columns?: string[];
    unexpected_columns?: string[];
    type_mismatches?: unknown[];
  };
};

type Report = {
  catalog: string;
  schema: string;
  tested_at: string;
  total_tables: number;
  passed: number;
  failed: number;
  inconclusive: number;
  results: TableResult[];
};

const API = "/api/heaap/api/dynamic-metadata";

export default function DynamicMetadataAssurance() {
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      const response = await fetch(`${API}/latest`, { cache: "no-store" });
      if (!response.ok) throw new Error(`Report request failed (${response.status})`);
      setReport(await response.json());
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load report");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function runAll() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API}/run`, { method: "POST" });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : "Assurance failed"
        );
      }

      setReport(data as Report);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to run assurance");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-900">
            Dynamic Gold Metadata Assurance
          </h2>
          <p className="text-xs text-slate-500">
            All discovered business Gold tables · Schema consistency
          </p>
        </div>
        <button
          type="button"
          disabled={loading}
          onClick={runAll}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          {loading ? "Running assurance..." : "Run All Tables"}
        </button>
      </div>

      {error && (
        <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">
          {error}
        </p>
      )}

      {report && (
        <>
          <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
            {[
              ["Total Tables", report.total_tables],
              ["Passed", report.passed],
              ["Failed", report.failed],
              ["Inconclusive", report.inconclusive],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg bg-slate-50 p-3">
                <div className="text-xs text-slate-500">{label}</div>
                <div className="text-2xl font-bold text-slate-900">{value}</div>
              </div>
            ))}
          </div>

          <p className="mt-3 text-xs text-slate-500">
            {report.catalog}.{report.schema} · Last run:{" "}
            {new Date(report.tested_at).toLocaleString()}
          </p>

          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-3 py-2">Gold Table</th>
                  <th className="px-3 py-2">Columns</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Details</th>
                </tr>
              </thead>
              <tbody>
                {report.results.map((item) => (
                  <tr key={item.table} className="border-t border-slate-100">
                    <td className="px-3 py-3 font-medium">{item.table}</td>
                    <td className="px-3 py-3">{item.column_count}</td>
                    <td className="px-3 py-3">
                      <span className={
                        item.status === "PASS"
                          ? "font-semibold text-green-700"
                          : item.status === "FAIL"
                          ? "font-semibold text-red-700"
                          : "font-semibold text-amber-700"
                      }>
                        {item.status}
                      </span>
                    </td>
                    <td className="px-3 py-3">
                      <details>
                        <summary className="cursor-pointer text-indigo-600">
                          View
                        </summary>
                        <pre className="mt-2 max-w-lg overflow-auto whitespace-pre-wrap text-xs">
                          {JSON.stringify(
                            { error: item.error, checks: item.checks },
                            null,
                            2
                          )}
                        </pre>
                      </details>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="mt-4 text-xs text-amber-700">
            Schema checks passed does not mean business-question relevance
            has been independently verified.
          </p>
        </>
      )}
    </section>
  );
}
