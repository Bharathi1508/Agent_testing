"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getBankingAgentRuns } from "../../lib/bankingAgentRuns";

type PipelineResult = {
  question?: string;
  agent_runs?: {
    agent_id: string;
    name: string;
    role: string;
    status: string;
    summary: string;
  }[];
  metadata_assurance_status?: string;
  metadata_decision?: string;
  sql_generation_status?: string;
  sql_assurance_status?: string;
  sql_execution_status?: string;
  sql_execution_allowed?: boolean;
  result_validation_status?: string;
  sql_execution?: {
    status?: string;
    row_count?: number;
    rows?: Record<string, unknown>[];
    error?: string;
    result_validation?: {
      validation_status?: string;
      checks?: Record<string, string>;
      row_count?: number;
      preview_truncated?: boolean;
    };
  };
  report_path?: string;
  selection?: {
    primary_table?: string;
    selected_columns?: string[];
    supporting_tables?: string[];
    selection_source?: string;
    reference_rule_id?: string | null;
    expected_filter?: string | null;
    relationships?: string[];
    join_required?: boolean;
  };
  metadata_validation?: {
    validation_status?: string;
    reference_authority?: string;
    expected_table?: string;
    expected_columns?: string[];
    expected_filter?: string | null;
    expected_relationships?: string[];
    checks?: Record<string, string>;
    evidence?: string[];
  };
  independent_evaluation?: {
    validation_status?: string;
    evidence_source?: string;
    reference_authority?: string;
    independent_schema_fetch?: boolean;
    reason?: string;
    checks?: Record<string, string>;
    missing_columns?: string[];
    invalid_columns?: string[];
    extra_columns?: string[];
  };
  sql_generation?: {
    status?: string;
    sql?: string | null;
    reason?: string;
  };
  sql_supervisor_status?: string;
  sql_supervisor?: {
    status?: string;
    checks?: Record<string, boolean>;
    details?: {
      live_schema_columns?: string[];
      schema_error?: string;
    };
    note?: string;
  };
  sql_assurance?: {
    status?: string;
    checks?: Record<string, boolean>;
    note?: string;
  };
};

function formatResultValue(value: unknown): string {
  if (value === null || value === undefined) return "NULL";
  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return String(value);
  }
  return JSON.stringify(value) ?? String(value);
}

function statusTone(value?: string | boolean): string {
  const status = typeof value === "boolean"
    ? value ? "PASS" : "FAIL"
    : (value || "WAITING").toUpperCase();

  if (["PASS", "COMPLETE", "GENERATED", "SUCCEEDED", "RECEIVED"].includes(status)) {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (status === "REVIEW") {
    return "border-amber-200 bg-amber-50 text-amber-800";
  }
  if (["FAIL", "ERROR", "BLOCKED", "NOT_FOUND"].includes(status)) {
    return "border-rose-200 bg-rose-50 text-rose-700";
  }
  if (status.startsWith("NOT_REQUIRED")) {
    return "border-slate-200 bg-slate-100 text-slate-600";
  }
  return "border-slate-200 bg-white text-slate-500";
}

function StatusBadge({ value }: { value?: string | boolean }) {
  const label = typeof value === "boolean"
    ? value ? "PASS" : "FAIL"
    : value || "WAITING";
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${statusTone(value)}`}>
      {label.replace(/_/g, " ")}
    </span>
  );
}
function CheckRows({ checks }: { checks?: Record<string, string | boolean> }) {
  const entries = Object.entries(checks || {});
  if (!entries.length) {
    return <p className="text-sm text-slate-500">Checks are not available yet.</p>;
  }

  return (
    <div className="divide-y divide-slate-100">
      {entries.map(([name, value]) => (
        <div key={name} className="flex items-center justify-between gap-4 py-2.5 text-sm">
          <span className="text-slate-600">{name.replace(/_/g, " ")}</span>
          <StatusBadge value={value} />
        </div>
      ))}
    </div>
  );
}

export default function BusinessQueryAssurancePage() {
  const [question, setQuestion] = useState(
    "Which customers have overdue loan installments?"
  );
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const autoRunStarted = useRef(false);

  const runAssurance = useCallback(async (questionToRun = question) => {
    if (!questionToRun.trim()) return;

    setLoading(true);
    setError("");
    setResult(null);
    setQuestion(questionToRun);

    try {
      const response = await fetch(
        "/api/business-query-assurance",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: questionToRun }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Pipeline request failed"
        );
      }

      setResult(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unexpected error"
      );
    } finally {
      setLoading(false);
    }
  }, [question]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const requestedQuestion = params.get("question");
    if (
      params.get("run") === "1" &&
      requestedQuestion?.trim() &&
      !autoRunStarted.current
    ) {
      autoRunStarted.current = true;
      void runAssurance(requestedQuestion);
    }
  }, [runAssurance]);

  const metadataStatus = result?.metadata_assurance_status || "WAITING";
  const decisionText: Record<string, string> = {
    PASS: "Metadata is validated. The request can proceed to SQL assurance.",
    FAIL: "A validation check failed. Review the evidence, correct the question or metadata, then retest.",
    ERROR: "A required validation service returned an error. Resolve the service issue before retesting.",
    REVIEW: "The question needs human review. HEAAP will not generate or execute SQL for this request.",
  };
  const stages = [
    {
      title: "Business question",
      description: "Intent received",
      status: result?.question ? "RECEIVED" : loading ? "IN_PROGRESS" : "WAITING",
    },
    {
      title: "Metadata agent",
      description: "Tables and columns selected",
      status: result?.selection ? "COMPLETE" : result ? "NOT_FOUND" : "WAITING",
    },
    {
      title: "Independent checks",
      description: "Unity Catalog · glossary · semantics",
      status: result?.independent_evaluation?.validation_status || "WAITING",
    },
    {
      title: "Decision gate",
      description: "PASS · FAIL · human review",
      status: metadataStatus,
    },
    {
      title: "SQL generation test",
      description: "Generate and inspect safe SQL",
      status: result?.sql_assurance_status || result?.sql_generation_status || "WAITING",
    },
    {
      title: "Result validation",
      description: "Execute only after all gates pass",
      status: result?.result_validation_status || result?.sql_execution?.status || "WAITING",
    },
  ];
  const questionExamples = [
    "What is the average closing_balance_inr by snapshot_date in gold_account_balance_trends?",
    "How many records are in gold_account_balance_trends?",
    "Which customers have overdue loan installments?",
  ];
  const specialistAgentRuns = result
    ? getBankingAgentRuns(result)
    : [];

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <a href="/" className="text-sm font-medium text-indigo-700 hover:text-indigo-900">
              ← HEAAP workspace
            </a>
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <span className="rounded-lg bg-indigo-100 px-2.5 py-1 text-xs font-bold uppercase tracking-wider text-indigo-800">
                Testing workbench
              </span>
              <span className="text-xs font-medium text-slate-500">
                Gold metadata · semantic assurance · safe SQL
              </span>
            </div>
            <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">
              Business Query Assurance
            </h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Test whether a business question maps to the right Databricks metadata before any SQL runs.
              Unclear meaning is routed to review; only validated, bounded templates can execute.
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Assurance mode</div>
            <div className="mt-1 flex items-center gap-2 text-sm font-semibold text-slate-800">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              Read-only · gated
            </div>
          </div>
        </header>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7" aria-labelledby="question-title">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-indigo-700">01 · Start a test</p>
              <h2 id="question-title" className="mt-1 text-xl font-bold text-slate-950">What should HEAAP validate?</h2>
              <p className="mt-1 text-sm text-slate-500">Enter a business question or try one of these examples.</p>
            </div>
            {result && <StatusBadge value={metadataStatus} />}
          </div>
          <textarea
            aria-label="Business question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            rows={3}
            placeholder="e.g. What is the average account balance by snapshot date?"
            className="mt-5 w-full resize-y rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-900 outline-none transition focus:border-indigo-500 focus:bg-white focus:ring-4 focus:ring-indigo-100"
          />
          <div className="mt-3 flex flex-wrap gap-2">
            {questionExamples.map((example) => (
              <button
                type="button"
                key={example}
                onClick={() => setQuestion(example)}
                className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-left text-xs text-slate-600 transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-800"
              >
                {example}
              </button>
            ))}
          </div>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <button
              onClick={() => void runAssurance()}
              disabled={loading || !question.trim()}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-wait disabled:opacity-60"
            >
              {loading ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                  Running assurance…
                </>
              ) : result ? "Run test again" : "Run assurance"}
            </button>
            <span className="text-xs text-slate-500">Metadata → independent review → decision gate → SQL → result checks</span>
          </div>
          {error && (
            <p role="alert" className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </p>
          )}
        </section>

        <section className="mt-7" aria-labelledby="pipeline-title">
          <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-indigo-700">02 · Assurance pipeline</p>
              <h2 id="pipeline-title" className="mt-1 text-xl font-bold text-slate-950">Every stage has a gate</h2>
            </div>
            {result?.metadata_decision && (
              <span className="text-xs text-slate-500">Decision: {result.metadata_decision.replace(/_/g, " ")}</span>
            )}
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {stages.map((stage, index) => (
              <article key={stage.title} className="relative rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-start gap-3">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-600">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <div className="min-w-0">
                      <h3 className="font-semibold text-slate-900">{stage.title}</h3>
                      <p className="mt-1 text-xs leading-5 text-slate-500">{stage.description}</p>
                    </div>
                  </div>
                  <StatusBadge value={stage.status} />
                </div>
              </article>
            ))}
          </div>
        </section>

        {result && (
          <>
            <section className={`mt-6 rounded-2xl border p-5 shadow-sm sm:p-6 ${
              metadataStatus === "PASS"
                ? "border-emerald-200 bg-emerald-50"
                : metadataStatus === "REVIEW"
                  ? "border-amber-200 bg-amber-50"
                  : "border-rose-200 bg-rose-50"
            }`} aria-live="polite">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-500">03 · Metadata decision</p>
                  <h2 className="mt-1 text-2xl font-bold text-slate-950">
                    {metadataStatus === "PASS" ? "Validated to proceed" : metadataStatus === "REVIEW" ? "Human review required" : metadataStatus === "FAIL" || metadataStatus === "ERROR" ? "Test did not pass" : "Decision pending"}
                  </h2>
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
                    {decisionText[metadataStatus] || "The pipeline has not returned a metadata decision."}
                  </p>
                </div>
                <StatusBadge value={metadataStatus} />
              </div>
              <div className="mt-5 grid gap-3 sm:grid-cols-3">
                {[
                  ["SQL generation test", result.sql_generation_status || "NOT_STARTED"],
                  ["Independent SQL check", result.sql_supervisor_status || "NOT_TESTED"],
                  ["Result validation", result.result_validation_status || "NOT_TESTED"],
                ].map(([label, status]) => (
                  <div key={label} className="flex items-center justify-between gap-3 rounded-lg border border-white/80 bg-white/80 px-3 py-2.5">
                    <span className="text-sm text-slate-600">{label}</span>
                    <StatusBadge value={status} />
                  </div>
                ))}
              </div>
            </section>

            {specialistAgentRuns.length ? (
              <section className="mt-6 rounded-2xl border border-indigo-100 bg-indigo-50/50 p-5 shadow-sm">
                <h2 className="font-bold text-slate-950">Banking specialist agent runs</h2>
                <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200 bg-white">
                  <table className="w-full min-w-[700px] text-left text-xs">
                    <thead className="bg-slate-50 text-slate-500">
                      <tr>
                        {["Agent", "Responsibility", "Run status", "Evidence"].map(label => (
                          <th key={label} className="px-3 py-3 font-semibold">{label}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {specialistAgentRuns.map(agent => (
                        <tr key={agent.agent_id} className="border-t border-slate-100 align-top">
                          <td className="px-3 py-3 font-semibold text-slate-900">{agent.name}</td>
                          <td className="px-3 py-3 text-slate-600">{agent.role}</td>
                          <td className="px-3 py-3"><StatusBadge value={agent.status} /></td>
                          <td className="px-3 py-3 text-slate-600">{agent.summary}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            ) : null}

            <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-2">
              <section className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wider text-indigo-700">Metadata agent</p>
                    <h2 className="mt-1 text-lg font-bold text-slate-950">Retrieved metadata</h2>
                  </div>
                  <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                    {result.selection?.selection_source?.replace(/_/g, " ") || "source unavailable"}
                  </span>
                </div>
                <dl className="mt-5 grid gap-4 sm:grid-cols-2">
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Gold table</dt>
                    <dd className="mt-1 break-all font-mono text-sm font-semibold text-slate-900">{result.selection?.primary_table || "No table selected"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Glossary rule</dt>
                    <dd className="mt-1 text-sm font-medium text-slate-800">{result.selection?.reference_rule_id || "No curated rule matched"}</dd>
                  </div>
                  <div className="sm:col-span-2">
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Selected columns</dt>
                    <dd className="mt-2 flex flex-wrap gap-2">
                      {result.selection?.selected_columns?.length ? result.selection.selected_columns.map((column) => (
                        <span key={column} className="rounded-md border border-indigo-100 bg-indigo-50 px-2.5 py-1 font-mono text-xs text-indigo-800">{column}</span>
                      )) : <span className="text-sm text-slate-500">No columns selected</span>}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Expected filter</dt>
                    <dd className="mt-1 text-sm text-slate-700">{result.selection?.expected_filter || "None defined"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Relationships</dt>
                    <dd className="mt-1 text-sm text-slate-700">{result.selection?.relationships?.join(", ") || (result.selection?.join_required ? "Required, not defined" : "None required")}</dd>
                  </div>
                </dl>
                <details className="mt-5 rounded-lg border border-slate-200">
                  <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-slate-700">Metadata checks and live schema evidence</summary>
                  <div className="border-t border-slate-100 px-4">
                    <CheckRows checks={result.metadata_validation?.checks} />
                    {result.metadata_validation?.evidence?.length ? (
                      <ul className="space-y-2 border-t border-slate-100 py-3 text-xs leading-5 text-slate-600">
                        {result.metadata_validation.evidence.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
                      </ul>
                    ) : null}
                    <p className="border-t border-slate-100 py-3 text-xs text-slate-500">
                      Reference authority: {result.metadata_validation?.reference_authority || "Not available"}
                    </p>
                  </div>
                </details>
              </section>

              <section className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <p className="text-xs font-bold uppercase tracking-wider text-indigo-700">Independent supervisor</p>
                <div className="mt-1 flex flex-wrap items-center justify-between gap-3">
                  <h2 className="text-lg font-bold text-slate-950">Semantic and catalog checks</h2>
                  <StatusBadge value={result.independent_evaluation?.validation_status} />
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Evidence source: {result.independent_evaluation?.evidence_source || result.independent_evaluation?.reason || "Not available"}
                </p>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {[
                    ["Unity Catalog", result.metadata_validation?.checks?.live_schema || result.metadata_validation?.checks?.selected_columns_exist || "NOT_TESTED"],
                    ["Business glossary", result.metadata_validation?.checks?.business_glossary || result.metadata_validation?.checks?.reference_definition || "NOT_TESTED"],
                    ["Relationships", result.metadata_validation?.checks?.relationship_metadata || "NOT_TESTED"],
                    ["Semantic evaluation", result.independent_evaluation?.validation_status || "NOT_TESTED"],
                  ].map(([label, status]) => (
                    <div key={label} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
                      <div className="mt-2"><StatusBadge value={status} /></div>
                    </div>
                  ))}
                </div>
                <details className="mt-4 rounded-lg border border-slate-200">
                  <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-slate-700">Full independent evaluation</summary>
                  <div className="border-t border-slate-100 px-4">
                    <CheckRows checks={result.independent_evaluation?.checks} />
                  </div>
                </details>
              </section>

              <section className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wider text-indigo-700">SQL generation agent</p>
                    <h2 className="mt-1 text-lg font-bold text-slate-950">Generated query</h2>
                  </div>
                  <StatusBadge value={result.sql_assurance_status || result.sql_generation_status} />
                </div>
                {result.sql_generation?.sql ? (
                  <pre className="mt-4 overflow-x-auto rounded-xl bg-slate-950 p-4 font-mono text-xs leading-6 text-emerald-200">
                    {result.sql_generation.sql}
                  </pre>
                ) : (
                  <p className="mt-4 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-600">
                    {result.sql_generation?.reason || "SQL is not generated until metadata passes the decision gate."}
                  </p>
                )}
                <details className="mt-4 rounded-lg border border-slate-200">
                  <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-slate-700">SQL template and supervisor checks</summary>
                  <div className="border-t border-slate-100 px-4">
                    <h3 className="py-3 text-xs font-bold uppercase tracking-wide text-slate-500">Template assurance</h3>
                    <CheckRows checks={result.sql_assurance?.checks} />
                    <h3 className="border-t border-slate-100 py-3 text-xs font-bold uppercase tracking-wide text-slate-500">Independent SQL supervisor</h3>
                    <CheckRows checks={result.sql_supervisor?.checks} />
                    {result.sql_supervisor?.details?.schema_error && (
                      <p role="alert" className="border-t border-slate-100 py-3 text-sm text-rose-700">{result.sql_supervisor.details.schema_error}</p>
                    )}
                  </div>
                </details>
              </section>

              <section className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wider text-indigo-700">Databricks execution</p>
                    <h2 className="mt-1 text-lg font-bold text-slate-950">Validated results</h2>
                  </div>
                  <StatusBadge value={result.result_validation_status || result.sql_execution?.status} />
                </div>
                <p className="mt-2 text-sm text-slate-600">
                  {result.sql_execution?.status || "NOT_EXECUTED"}
                  {typeof result.sql_execution?.row_count === "number" ? ` · ${result.sql_execution.row_count} row${result.sql_execution.row_count === 1 ? "" : "s"}` : ""}
                  {" · "}
                  {result.sql_execution_allowed ? "Execution authorized by assurance gates" : "Execution blocked"}
                </p>
                {result.sql_execution?.result_validation?.preview_truncated && (
                  <p role="status" className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                    Preview reached the 100-row cap and may be incomplete. Grouped results should be treated as a preview.
                  </p>
                )}
                {result.sql_execution?.error && (
                  <p role="alert" className="mt-3 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{result.sql_execution.error}</p>
                )}
                {result.sql_execution?.rows?.length ? (
                  <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200">
                    <table className="w-full min-w-max text-left text-sm">
                      <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                        <tr>{Object.keys(result.sql_execution.rows[0]).map((column) => <th key={column} className="px-4 py-3 font-semibold">{column}</th>)}</tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {result.sql_execution.rows.map((row, rowIndex) => (
                          <tr key={rowIndex} className="hover:bg-slate-50">
                            {Object.values(row).map((value, columnIndex) => <td key={columnIndex} className="px-4 py-3 text-slate-700">{formatResultValue(value)}</td>)}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : result.sql_execution?.status === "SUCCEEDED" ? (
                  <p className="mt-4 rounded-lg bg-slate-50 p-4 text-sm text-slate-600">The query completed and returned no rows.</p>
                ) : (
                  <p className="mt-4 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-500">
                    Results appear only after metadata, SQL-template, and independent supervisor checks pass.
                  </p>
                )}
                <details className="mt-4 rounded-lg border border-slate-200">
                  <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-slate-700">Result shape and value checks</summary>
                  <div className="border-t border-slate-100 px-4">
                    <CheckRows checks={result.sql_execution?.result_validation?.checks} />
                  </div>
                </details>
              </section>
            </div>

            <footer className="mt-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-5 py-4 text-xs text-slate-500">
              <span>HEAAP POC · Schema evidence does not replace business-owner approval of metric meaning.</span>
              <span className="break-all font-mono">{result.report_path || "Assurance report unavailable"}</span>
            </footer>
          </>
        )}
      </div>
    </main>
  );
}
