"use client";
import { useState } from "react";
import { getBankingAgentRuns } from "../lib/bankingAgentRuns";

type Column = { column_name: string; data_type?: string; matched_terms?: string[] };
type Candidate = { table_name: string; score: number; columns: Column[]; schema_status: string; semantic_status: string; checks?: {column: string; valid: boolean}[]; error?: string };
type Validation = {
  validation_status: string;
  expected_table?: string | null;
  expected_columns?: string[];
  missing_columns?: string[];
  extra_columns?: string[];
  expected_filter?: string | null;
  checks?: Record<string, string>;
  evidence?: string[];
  sql_execution_allowed: boolean;
};
type Result = { question: string; status: string; total_candidates?: number; relevant_metadata: Candidate[]; assurance_status: string; assurance_note?: string; error?: string; selection?: SupervisorResult; validation?: Validation };
type CatalogColumn = { column_name: string; data_type?: string; comment?: string | null };
type GoldTable = { table_name: string; table_type?: string | null; columns: CatalogColumn[] };
type GoldCatalog = { catalog: string; schema: string; source: string; tables: GoldTable[] };
type FullPipelineResult = {
  question: string;
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
  sql_supervisor_status?: string;
  sql_execution_status?: string;
  result_validation_status?: string;
  selection?: {
    primary_table?: string;
    selected_columns?: string[];
  };
  metadata_validation?: {
    validation_status?: string;
    checks?: Record<string, string>;
  };
  independent_evaluation?: {
    validation_status?: string;
    checks?: Record<string, string>;
  };
  sql_assurance?: {
    status?: string;
    checks?: Record<string, boolean>;
    note?: string;
  };
  sql_supervisor?: {
    status?: string;
    checks?: Record<string, boolean>;
    note?: string;
  };
  sql_generation?: {
    sql?: string | null;
    reason?: string;
  };
  sql_execution?: {
    status?: string;
    row_count?: number;
    rows?: Record<string, unknown>[];
    result_validation?: {
      validation_status?: string;
      checks?: Record<string, string>;
      preview_truncated?: boolean;
    };
  };
  error?: string;
};
type BulkPipelineResult = {
  question: string;
  metadata_assurance_status?: string;
  metadata_decision?: string;
  sql_generation_status?: string;
  sql_execution_status?: string;
  result_validation_status?: string;
  sql_execution?: {
    row_count?: number;
    rows?: Record<string, unknown>[];
    result_validation?: {
      validation_status?: string;
      checks?: Record<string, string>;
      preview_truncated?: boolean;
    };
  };
  sql_generation?: { sql?: string | null; reason?: string };
  error?: string;
};
type BulkPipelineResponse = {
  total: number;
  summary: {
    PASS: number;
    REVIEW: number;
    FAIL: number;
    ERROR: number;
    EXECUTED: number;
  };
  results: BulkPipelineResult[];
};

type SupervisorResult = {
  question: string;
  primary_table: string | null;
  selected_columns: string[];
  supporting_tables: string[];
  rejected_candidates: {table_name: string; reason: string}[];
  selection_status: string;
  schema_status?: string;
  coverage?: number;
  sql_execution_allowed: boolean;
  selection_source?: string;
  reference_rule_id?: string | null;
  expected_filter?: string | null;
  note?: string;
};

function PipelineBadge({ status }: { status?: string }) {
  const value = status || "NOT_TESTED";
  const tone = ["PASS", "SUCCEEDED", "GENERATED", "COMPLETE"].includes(value)
    ? "border-emerald-200 bg-emerald-50 text-emerald-700"
    : value === "REVIEW"
      ? "border-amber-200 bg-amber-50 text-amber-800"
      : ["FAIL", "ERROR", "BLOCKED"].includes(value)
        ? "border-rose-200 bg-rose-50 text-rose-700"
        : "border-slate-200 bg-slate-50 text-slate-600";
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-bold ${tone}`}>{value.replaceAll("_", " ")}</span>;
}

function PipelineChecks({ checks }: { checks?: Record<string, string | boolean> }) {
  if (!checks || Object.keys(checks).length === 0) {
    return <p className="text-xs text-slate-500">No checks available.</p>;
  }
  return <div className="grid gap-2 sm:grid-cols-2">
    {Object.entries(checks).map(([name, value]) => (
      <div key={name} className="flex items-center justify-between gap-2 rounded-lg bg-white px-3 py-2 text-xs">
        <span className="text-slate-600">{name.replaceAll("_", " ")}</span>
        <PipelineBadge status={typeof value === "boolean" ? value ? "PASS" : "FAIL" : value} />
      </div>
    ))}
  </div>;
}

const BASE = "/api/heaap/api/business-metadata";
async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {method: "POST", headers: {"content-type": "application/json"}, body: JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : `HTTP ${response.status}`);
  return data as T;
}
const EXAMPLES = [
  "Which customers have overdue loan installments?",
  "Show loan repayment rate by loan type",
  "What is the closing account balance by snapshot date?",
  "Show fraud score by customer segment",
  "Which customers have overdue KYC reviews?"
];

function questionStarters(table: GoldTable): string[] {
  const dimensions = table.columns.filter(column =>
    /STRING|CHAR|VARCHAR|BOOLEAN|DATE|TIMESTAMP/.test(
      (column.data_type || "").toUpperCase()
    )
  );
  const measures = table.columns.filter(column =>
    /TINYINT|SMALLINT|INT|INTEGER|BIGINT|LONG|FLOAT|DOUBLE|DECIMAL|NUMERIC/.test(
      (column.data_type || "").toUpperCase()
    )
  );
  const questions = new Set<string>([
    `How many records are in ${table.table_name}?`
  ]);

  for (const dimension of dimensions) {
    questions.add(
      `How many records are there by ${dimension.column_name} in ${table.table_name}?`
    );
    questions.add(
      `Show records by ${dimension.column_name} in ${table.table_name}`
    );
  }

  for (const measure of measures) {
    questions.add(
      `What is the average ${measure.column_name} in ${table.table_name}?`
    );
    questions.add(
      `What is the minimum and maximum ${measure.column_name} in ${table.table_name}?`
    );
    for (const dimension of dimensions) {
      questions.add(
        `What is the average ${measure.column_name} by ${dimension.column_name} in ${table.table_name}?`
      );
    }
  }

  return Array.from(questions);
}

function SupervisorPanel({result, validation}: {result: SupervisorResult; validation: Validation}) {
  return (
    <div className="mt-4 space-y-3 rounded-lg border border-indigo-200 bg-indigo-50 p-4">
      <h4 className="font-bold text-indigo-900">
        Supervisor Metadata Selection
      </h4>

      <div className="text-sm">
        <strong>Primary Table:</strong>{" "}
        {result.primary_table || "No table selected"}
      </div>

      <div className="text-sm">
        <strong>Selection Status:</strong>{" "}
        {result.selection_status}
      </div>

      <div className="text-sm">
        <strong>Validation Status:</strong>{" "}
        {validation.validation_status}
      </div>

      <div className="text-sm">
        <strong>Reference:</strong>{" "}
        {result.reference_rule_id || "No curated rule matched"}
      </div>

      <div className="text-sm">
        <strong>Keyword Coverage:</strong>{" "}
        {typeof result.coverage === "number"
          ? `${(result.coverage * 100).toFixed(0)}%`
          : "Unavailable"}
      </div>

      <div className="text-sm">
        <strong>SQL Execution:</strong>{" "}
        {result.sql_execution_allowed ? "Allowed" : "Blocked"}
      </div>

      <div>
        <strong className="text-sm">Selected Columns</strong>
        <div className="mt-2 flex flex-wrap gap-2">
          {result.selected_columns?.map(column => (
            <span
              key={column}
              className="rounded bg-white px-2 py-1 text-xs text-indigo-900"
            >
              {column}
            </span>
          ))}
        </div>
      </div>

      <div className="space-y-1 text-sm">
        <p><strong>Expected table:</strong> {validation.expected_table || "Not independently defined"}</p>
        <p><strong>Required columns:</strong> {validation.expected_columns?.join(", ") || "Not independently defined"}</p>
        <p><strong>Missing required columns:</strong> {validation.missing_columns?.join(", ") || "None"}</p>
        <p><strong>Additional selected columns:</strong> {validation.extra_columns?.join(", ") || "None"}</p>
        <p><strong>Expected filter:</strong> {validation.expected_filter || result.expected_filter || "None defined"}</p>
      </div>

      <div>
        <strong className="text-sm">Validation checks</strong>
        <ul className="mt-1 list-disc pl-5 text-xs text-slate-700">
          {Object.entries(validation.checks || {}).map(([name, status]) => (
            <li key={name}>{name}: {status}</li>
          ))}
        </ul>
      </div>

      {validation.evidence?.length ? (
        <div>
          <strong className="text-sm">Evidence</strong>
          <ul className="mt-1 list-disc pl-5 text-xs text-slate-700">
            {validation.evidence.map(item => <li key={item}>{item}</li>)}
          </ul>
        </div>
      ) : null}

      <div>
        <strong className="text-sm">Alternative Candidates</strong>
        <ul className="mt-1 list-disc pl-5 text-xs text-slate-700">
          {result.rejected_candidates?.map(candidate => (
            <li key={candidate.table_name}>
              {candidate.table_name} - {candidate.reason}
            </li>
          ))}
        </ul>
      </div>

      {result.note && (
        <p className="text-xs text-slate-600">{result.note}</p>
      )}
      {!validation.sql_execution_allowed && (
        <p className="text-xs font-semibold text-amber-800">
          SQL execution remains blocked until all required checks pass.
        </p>
      )}
    </div>
  );
}

function Mapping({result}: {result: Result}) {
  return <div className="space-y-3 rounded-lg border border-slate-200 p-3">
    <div className="flex flex-wrap items-center justify-between gap-2"><strong className="text-sm text-slate-900">{result.question}</strong><span className="rounded bg-amber-100 px-2 py-1 text-xs text-amber-800">Metadata validation: {result.assurance_status}</span></div>
    {result.error && <p className="text-sm text-red-700">{result.error}</p>}
    {!result.relevant_metadata?.length && <p className="text-sm text-slate-500">No matching metadata found.</p>}
    {result.relevant_metadata?.map((item, i) => <details key={`${item.table_name}-${i}`} open={i===0} className="rounded border border-slate-200 bg-slate-50 p-3">
      <summary className="cursor-pointer text-sm font-semibold">{item.table_name} · score {item.score} · schema {item.schema_status}</summary>
      {item.error && <p className="text-xs text-red-700">{item.error}</p>}
      <div className="mt-2 flex flex-wrap gap-2">{item.columns?.map(col => <span key={col.column_name} title={col.matched_terms?.join(", ")} className="rounded bg-white px-2 py-1 text-xs text-slate-700 ring-1 ring-slate-200">{col.column_name} <span className="text-slate-400">{col.data_type}</span></span>)}</div>
      {!item.columns?.length && <p className="mt-2 text-xs text-amber-700">No columns selected by the lexical retriever.</p>}
    </details>)}
    <p className="text-xs text-slate-500">{result.assurance_note || "Schema checks do not prove semantic correctness."}</p>
    {result.validation && <details className="rounded border border-amber-200 bg-amber-50 p-3">
      <summary className="cursor-pointer text-sm font-semibold">Validation details</summary>
      <p className="mt-2 text-xs">Reference: {result.selection?.reference_rule_id || "No approved rule matched"}</p>
      <p className="text-xs">Expected filter: {result.validation.expected_filter || "None defined"}</p>
      <ul className="mt-1 list-disc pl-5 text-xs text-slate-700">
        {Object.entries(result.validation.checks || {}).map(([name, status]) => (
          <li key={name}>{name}: {status}</li>
        ))}
      </ul>
    </details>}
  </div>;
}
export default function BusinessQuestionAssurance() {
  const [tab, setTab] = useState<"ask" | "bulk" | "catalog">("ask");
  const [question, setQuestion] = useState(EXAMPLES[0]);
  const [limit, setLimit] = useState(20);
  const [single, setSingle] = useState<Result | null>(null);
  const [supervisor, setSupervisor] = useState<SupervisorResult | null>(null);
  const [fullPipeline, setFullPipeline] = useState<FullPipelineResult | null>(null);
  const [fullPipelineLoading, setFullPipelineLoading] = useState(false);
  const [bulk, setBulk] = useState<Result[]>([]);
  const [catalog, setCatalog] = useState<GoldCatalog | null>(null);
  const [selectedTableName, setSelectedTableName] = useState("");
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [catalogError, setCatalogError] = useState("");
  const [bulkPipeline, setBulkPipeline] = useState<BulkPipelineResponse | null>(null);
  const [bulkPipelineLoading, setBulkPipelineLoading] = useState(false);
  const [bulkPipelineError, setBulkPipelineError] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function loadCatalog() {
    setCatalogLoading(true);
    setCatalogError("");
    try {
      const response = await fetch(`${BASE}/catalog`, {cache: "no-store"});
      const data = await response.json();
      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : `Catalog request failed (HTTP ${response.status})`
        );
      }
      const result = data as GoldCatalog;
      setCatalog(result);
      setSelectedTableName(current =>
        result.tables.some(table => table.table_name === current)
          ? current
          : result.tables[0]?.table_name || ""
      );
    } catch (e) {
      setCatalogError(e instanceof Error ? e.message : "Catalog request failed");
    } finally {
      setCatalogLoading(false);
    }
  }
  async function ask(questionToAsk = question) {
    if (!questionToAsk.trim()) return;
    setQuestion(questionToAsk);
    setBusy(true);
    setError("");
    setSingle(null);
    setSupervisor(null);

    try {
      const metadata = await post<Result>("/ask", {question: questionToAsk});
      setSingle(metadata);
      setSupervisor(metadata.selection || null);
    } catch(e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  async function runFullPipeline(questionToRun = question) {
    if (!questionToRun.trim()) return;
    setQuestion(questionToRun);
    setFullPipelineLoading(true);
    setFullPipeline(null);
    setSingle(null);
    setSupervisor(null);
    setError("");

    try {
      const response = await fetch("/api/business-query-assurance", {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({question: questionToRun}),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : `Full assurance failed (HTTP ${response.status})`
        );
      }
      setFullPipeline(data as FullPipelineResult);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Full assurance failed");
    } finally {
      setFullPipelineLoading(false);
    }
  }

  const selectedTable = catalog?.tables.find(
    table => table.table_name === selectedTableName
  );
  const starters = selectedTable ? questionStarters(selectedTable) : [];
  const specialistAgentRuns = fullPipeline
    ? getBankingAgentRuns(fullPipeline)
    : [];

  async function runBulk() {
    setBusy(true); setError(""); setBulk([]);
    try { const data = await post<{results: Result[]}>("/bulk", {limit}); setBulk(data.results); }
    catch(e) {setError(e instanceof Error ? e.message : "Request failed");}
    finally {setBusy(false);}
  }
  async function runFullAssuranceForAll() {
    if (!starters.length || !selectedTable) return;
    setBulkPipelineLoading(true);
    setBulkPipelineError("");
    setBulkPipeline(null);
    try {
      const response = await fetch("/api/business-query-assurance/bulk", {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify({questions: starters}),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : `Bulk assurance failed (HTTP ${response.status})`
        );
      }
      setBulkPipeline(data as BulkPipelineResponse);
    } catch (e) {
      setBulkPipelineError(
        e instanceof Error ? e.message : "Bulk assurance failed"
      );
    } finally {
      setBulkPipelineLoading(false);
    }
  }
  return <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
    <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div>
        <div className="text-xs font-bold uppercase tracking-wider text-indigo-700">HEAAP · Banking AI testing team</div>
        <h2 className="mt-1 text-xl font-bold text-slate-950">Business Question Testbench</h2>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">Ask in business language. HEAAP selects Gold metadata, independently checks it against Unity Catalog and available business rules, then gates SQL generation and result validation.</p>
      </div>
      <a href="/business-query-assurance" className="rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm font-semibold text-indigo-800 hover:bg-indigo-100">Open detailed pipeline</a>
    </div>
    <div className="mb-5 grid gap-2 rounded-xl bg-slate-50 p-3 sm:grid-cols-3 lg:grid-cols-6" aria-label="Assurance process">
      {["Banking question agent", "Gold metadata agent", "Banking semantics agent", "PASS / REVIEW / FAIL", "SQL generation + safety agents", "Result validation agent"].map((stage, index) => (
        <div key={stage} className="flex items-center gap-2 text-xs font-medium text-slate-700">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white text-[10px] font-bold text-indigo-700 ring-1 ring-slate-200">{index + 1}</span>
          <span>{stage}</span>
        </div>
      ))}
    </div>
    <div className="mb-4 flex flex-wrap gap-2"><button onClick={()=>setTab("ask")} className={`rounded-lg px-4 py-2 text-sm ${tab==="ask"?"bg-indigo-600 text-white":"bg-slate-100"}`}>Ask Business Question</button><button onClick={()=>setTab("bulk")} className={`rounded-lg px-4 py-2 text-sm ${tab==="bulk"?"bg-indigo-600 text-white":"bg-slate-100"}`}>Bulk Question Testing</button><button onClick={()=>{setTab("catalog"); if (!catalog && !catalogLoading) void loadCatalog();}} className={`rounded-lg px-4 py-2 text-sm ${tab==="catalog"?"bg-indigo-600 text-white":"bg-slate-100"}`}>Gold Table Explorer</button></div>
    {tab==="ask" ? <div className="space-y-4">
      <div>
        <label htmlFor="business-question" className="mb-2 block text-sm font-semibold text-slate-800">Business question to test</label>
        <textarea id="business-question" aria-label="Business question" className="w-full rounded-xl border border-slate-300 bg-slate-50 p-3 text-sm outline-none focus:border-indigo-500 focus:bg-white focus:ring-4 focus:ring-indigo-100" rows={3} value={question} onChange={e=>{setQuestion(e.target.value); setFullPipeline(null);}} placeholder="e.g. What is the average closing balance by snapshot date?" />
      </div>
      <div className="flex flex-wrap gap-2">{EXAMPLES.map(q=><button key={q} onClick={()=>{setQuestion(q); setFullPipeline(null);}} className="rounded-full border border-slate-200 px-3 py-1.5 text-left text-xs text-slate-600 hover:border-indigo-300 hover:bg-indigo-50">{q}</button>)}</div>
      <div className="flex flex-wrap items-center gap-3">
        <button disabled={fullPipelineLoading || busy || question.trim().length<3} onClick={()=>void runFullPipeline()} className="rounded-lg bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:cursor-wait disabled:opacity-50">{fullPipelineLoading?"Running metadata + SQL tests…":"Run metadata + SQL tests"}</button>
        <button disabled={fullPipelineLoading || busy || question.trim().length<3} onClick={()=>void ask()} className="rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50">{busy?"Checking metadata…":"Metadata-only (no SQL)"}</button>
        <span className="text-xs text-slate-500">On a metadata PASS, the full run automatically starts the SQL generation test and displays the generated SQL. REVIEW or FAIL stops before SQL.</span>
      </div>
      {fullPipeline && <section className="rounded-xl border border-slate-200 bg-slate-50 p-4 sm:p-5" aria-live="polite">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-indigo-700">Full assurance result</div>
            <h4 className="mt-1 text-lg font-bold text-slate-950">{fullPipeline.metadata_assurance_status === "PASS" ? "Metadata passed validation" : fullPipeline.metadata_assurance_status === "REVIEW" ? "Human review required" : fullPipeline.metadata_assurance_status === "FAIL" ? "Validation failed" : "Pipeline result"}</h4>
            <p className="mt-1 text-sm text-slate-600">{fullPipeline.question}</p>
          </div>
          <PipelineBadge status={fullPipeline.metadata_assurance_status || "ERROR"} />
        </div>
        <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Independent checks", fullPipeline.independent_evaluation?.validation_status],
            ["SQL generation test", fullPipeline.sql_generation_status],
            ["SQL supervisor", fullPipeline.sql_supervisor_status],
            ["Result validation", fullPipeline.result_validation_status || fullPipeline.sql_execution?.status],
          ].map(([label, status]) => <div key={label} className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2"><span className="text-xs text-slate-600">{label}</span><PipelineBadge status={status} /></div>)}
        </div>
        {specialistAgentRuns.length ? <section className="mt-4 rounded-lg border border-indigo-100 bg-indigo-50/50 p-4">
          <h5 className="font-semibold text-slate-900">Banking specialist agent runs</h5>
          <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="w-full min-w-[700px] text-left text-xs">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  {["Agent", "Responsibility", "Run status", "Evidence"].map(label => (
                    <th key={label} className="px-3 py-2 font-semibold">{label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {specialistAgentRuns.map(agent => (
                  <tr key={agent.agent_id} className="border-t border-slate-100 align-top">
                    <td className="px-3 py-3 font-semibold text-slate-900">{agent.name}</td>
                    <td className="px-3 py-3 text-slate-600">{agent.role}</td>
                    <td className="px-3 py-3"><PipelineBadge status={agent.status} /></td>
                    <td className="px-3 py-3 text-slate-600">{agent.summary}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section> : null}
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <h5 className="font-semibold text-slate-900">Selected metadata</h5>
            <p className="mt-2 break-all font-mono text-sm text-indigo-800">{fullPipeline.selection?.primary_table || "No table selected"}</p>
            <div className="mt-2 flex flex-wrap gap-1.5">{fullPipeline.selection?.selected_columns?.map(column=><span key={column} className="rounded bg-indigo-50 px-2 py-1 font-mono text-xs text-indigo-800">{column}</span>)}</div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <h5 className="font-semibold text-slate-900">Decision and execution</h5>
            <p className="mt-2 text-xs text-slate-600">{fullPipeline.metadata_decision?.replaceAll("_", " ") || "No decision returned"} · {fullPipeline.sql_execution?.status || "NOT_EXECUTED"} · {fullPipeline.sql_execution?.row_count ?? 0} rows</p>
            {fullPipeline.sql_execution?.result_validation?.preview_truncated && <p className="mt-2 text-xs font-medium text-amber-800">100-row preview cap reached; grouped results may be incomplete.</p>}
          </div>
        </div>
        {fullPipeline.sql_generation?.sql ? <div className="mt-4">
          <h5 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Generated SQL · read-only template</h5>
          <pre className="overflow-x-auto rounded-lg bg-slate-950 p-3 font-mono text-xs leading-5 text-emerald-200">{fullPipeline.sql_generation.sql}</pre>
        </div> : fullPipeline.metadata_assurance_status === "PASS" ? <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          Metadata passed. SQL generation test: {fullPipeline.sql_generation_status || "NOT_STARTED"}.
          {fullPipeline.sql_generation?.reason ? ` ${fullPipeline.sql_generation.reason}` : " No SQL was returned; review the generation status before proceeding."}
        </p> : null}
        {fullPipeline.sql_execution?.rows?.length ? <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="w-full min-w-max text-left text-sm">
            <thead className="bg-white text-xs uppercase text-slate-500"><tr>{Object.keys(fullPipeline.sql_execution.rows[0]).map(column=><th key={column} className="px-3 py-2">{column}</th>)}</tr></thead>
            <tbody className="divide-y divide-slate-100">{fullPipeline.sql_execution.rows.map((row,index)=><tr key={index}>{Object.values(row).map((value,columnIndex)=><td key={columnIndex} className="px-3 py-2 text-slate-700">{value == null ? "NULL" : String(value)}</td>)}</tr>)}</tbody>
          </table>
        </div> : null}
        <details className="mt-4 rounded-lg border border-slate-200 bg-white p-3">
          <summary className="cursor-pointer text-sm font-semibold text-slate-700">Inspect validation evidence</summary>
          <div className="mt-3 space-y-4">
            <div><h5 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Metadata checks</h5><PipelineChecks checks={fullPipeline.metadata_validation?.checks} /></div>
            <div><h5 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Independent semantic checks</h5><PipelineChecks checks={fullPipeline.independent_evaluation?.checks} /></div>
            <div><h5 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">SQL template assurance</h5><PipelineChecks checks={fullPipeline.sql_assurance?.checks} /></div>
            <div><h5 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Result validation</h5><PipelineChecks checks={fullPipeline.sql_execution?.result_validation?.checks} /></div>
          </div>
        </details>
        <a href={`/business-query-assurance?run=1&question=${encodeURIComponent(fullPipeline.question)}`} className="mt-4 inline-flex text-sm font-semibold text-indigo-700 hover:text-indigo-900">Open detailed assurance report →</a>
      </section>}
      {single && <Mapping result={single}/>}
    {supervisor && single?.validation && <SupervisorPanel result={supervisor} validation={single.validation}/>}
    </div> : tab==="bulk" ? <div className="space-y-3"><label className="block text-sm">Generated questions (1–100) <input type="number" min={1} max={100} value={limit} onChange={e=>setLimit(Math.max(1,Math.min(100,Number(e.target.value)||1)))} className="ml-2 w-24 rounded border p-2" /></label><button disabled={busy} onClick={()=>void runBulk()} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{busy?"Testing...":"Generate & Test Questions"}</button>{bulk.length>0 && <><p className="text-sm">{bulk.length} generated questions · {bulk.filter(r=>r.status==="ERROR").length} errors · review required where no approved reference matches</p><div className="max-h-[620px] space-y-3 overflow-y-auto">{bulk.map((r,i)=><Mapping key={i} result={r}/>)}</div></>}</div> : <div className="space-y-4">
      {catalogLoading && <p className="text-sm text-slate-600">Loading live Unity Catalog metadata...</p>}
      {catalogError && <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{catalogError}</p>}
      {catalog && <>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
          <strong>Live source:</strong> {catalog.source} · <strong>Catalog:</strong> {catalog.catalog} · <strong>Schema:</strong> {catalog.schema} · <strong>Gold tables:</strong> {catalog.tables.length}
          <button onClick={()=>void loadCatalog()} disabled={catalogLoading} className="ml-3 text-indigo-700 underline disabled:opacity-50">Refresh metadata</button>
        </div>
        {catalog.tables.length === 0 ? <p className="text-sm text-amber-800">No gold_* tables were found in this configured catalog and schema.</p> : <>
          <label className="block text-sm font-medium">Gold table
            <select aria-label="Gold table" value={selectedTableName} onChange={event=>{setSelectedTableName(event.target.value); setBulkPipeline(null); setBulkPipelineError("");}} className="mt-1 block w-full rounded-lg border border-slate-300 bg-white p-2">
              {catalog.tables.map(table=><option key={table.table_name} value={table.table_name}>{table.table_name}</option>)}
            </select>
          </label>
          {selectedTable && <>
            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-3 py-2">Column</th><th className="px-3 py-2">Data type</th><th className="px-3 py-2">Business description</th></tr></thead>
                <tbody>{selectedTable.columns.map(column=><tr key={column.column_name} className="border-t border-slate-100"><td className="px-3 py-2 font-medium">{column.column_name}</td><td className="px-3 py-2 text-slate-600">{column.data_type || "Unknown"}</td><td className="px-3 py-2 text-slate-600">{column.comment || "No Unity Catalog comment"}</td></tr>)}</tbody>
              </table>
            </div>
            <div className="space-y-2">
              <div><h4 className="font-semibold text-slate-900">Schema-based analytical question starters ({starters.length})</h4><p className="text-xs text-slate-500">Generated from available column types. This is not an exhaustive list of business questions or proof of metric definitions.</p></div>
              <button
                onClick={()=>void runFullAssuranceForAll()}
                disabled={bulkPipelineLoading || busy || starters.length === 0 || starters.length > 100}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
              >
                {bulkPipelineLoading
                  ? `Running assurance for ${starters.length} questions...`
                  : `Run full assurance for all ${starters.length} questions`}
              </button>
              <p className="text-xs text-slate-500">The selected table’s questions are checked in one batch, up to four at a time. Only supported, validated read-only query templates return data; other questions are reported as REVIEW.</p>
              {starters.length > 100 && <p className="text-xs text-amber-800">This batch exceeds the 100-question limit; select a table with fewer generated questions.</p>}
              {bulkPipelineError && <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">{bulkPipelineError}</p>}
              {bulkPipeline && <>
                <div className="flex flex-wrap gap-3 rounded-lg bg-slate-50 p-3 text-sm">
                  <strong>{bulkPipeline.total} checked</strong>
                  <span className="text-green-700">PASS: {bulkPipeline.summary.PASS}</span>
                  <span className="text-amber-700">REVIEW: {bulkPipeline.summary.REVIEW}</span>
                  <span className="text-red-700">FAIL: {bulkPipeline.summary.FAIL}</span>
                  <span className="text-red-700">ERROR: {bulkPipeline.summary.ERROR}</span>
                  <span className="text-indigo-700">Executed: {bulkPipeline.summary.EXECUTED}</span>
                </div>
                <div className="max-h-[600px] space-y-2 overflow-y-auto">
                  {bulkPipeline.results.map((result, index)=><details key={`${result.question}-${index}`} className="rounded border border-slate-200 p-3">
                    <summary className="cursor-pointer text-sm">
                      <span className="font-medium">{result.question}</span>
                      <span className="ml-2 text-xs text-slate-600">
                        Metadata {result.metadata_assurance_status || "ERROR"} · SQL {result.sql_generation_status || "NOT_STARTED"} · Execution {result.sql_execution_status || "NOT_EXECUTED"} · Results {result.result_validation_status || "NOT_TESTED"}
                      </span>
                    </summary>
                    {result.error && <p className="mt-2 text-sm text-red-700">{result.error}</p>}
                    {result.sql_generation?.reason && <p className="mt-2 text-sm text-slate-600">{result.sql_generation.reason}</p>}
                    {result.sql_generation?.sql && <pre className="mt-2 overflow-x-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-xs">{result.sql_generation.sql}</pre>}
                    {Object.entries(result.sql_execution?.result_validation?.checks || {}).map(([name, status]) => <p key={name} className="mt-1 text-xs text-slate-600">{name.replace(/_/g, " ")}: {status}</p>)}
                    {result.sql_execution?.result_validation?.preview_truncated && <p className="mt-2 text-sm text-amber-800">This preview reached the 100-row limit and may be incomplete.</p>}
                    {result.sql_execution?.rows?.length ? <pre className="mt-2 overflow-x-auto rounded bg-slate-50 p-2 text-xs">{JSON.stringify(result.sql_execution.rows, null, 2)}</pre> : null}
                  </details>)}
                </div>
              </>}
              <div className="max-h-80 space-y-2 overflow-y-auto">{starters.map(starter=><div key={starter} className="flex flex-wrap items-center justify-between gap-2 rounded border border-slate-200 px-3 py-2">
                <span className="min-w-0 flex-1 text-sm text-slate-800">{starter}</span>
                <div className="flex gap-2">
                  <button disabled={busy} onClick={()=>{setTab("ask"); void ask(starter);}} className="rounded border border-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-50">Metadata check</button>
                  <a href={`/business-query-assurance?run=1&question=${encodeURIComponent(starter)}`} className="rounded bg-indigo-600 px-2 py-1 text-xs font-semibold text-white hover:bg-indigo-700">Run full assurance</a>
                </div>
              </div>)}</div>
            </div>
          </>}
        </>}
      </>}
    </div>}
    {error && <p role="alert" className="mt-3 rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
  </section>;
}
