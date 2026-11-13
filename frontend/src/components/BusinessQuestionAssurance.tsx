"use client";
import { useState } from "react";

type Column = { column_name: string; data_type?: string; matched_terms?: string[] };
type Candidate = { table_name: string; score: number; columns: Column[]; schema_status: string; semantic_status: string; checks?: {column: string; valid: boolean}[]; error?: string };
type Result = { question: string; status: string; total_candidates?: number; relevant_metadata: Candidate[]; assurance_status: string; assurance_note?: string; error?: string };

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
  note?: string;
};

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

function SupervisorPanel({result}: {result: SupervisorResult}) {
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
    </div>
  );
}

function Mapping({result}: {result: Result}) {
  return <div className="space-y-3 rounded-lg border border-slate-200 p-3">
    <div className="flex flex-wrap items-center justify-between gap-2"><strong className="text-sm text-slate-900">{result.question}</strong><span className="rounded bg-amber-100 px-2 py-1 text-xs text-amber-800">Semantic: {result.assurance_status}</span></div>
    {result.error && <p className="text-sm text-red-700">{result.error}</p>}
    {!result.relevant_metadata?.length && <p className="text-sm text-slate-500">No matching metadata found.</p>}
    {result.relevant_metadata?.map((item, i) => <details key={`${item.table_name}-${i}`} open={i===0} className="rounded border border-slate-200 bg-slate-50 p-3">
      <summary className="cursor-pointer text-sm font-semibold">{item.table_name} · score {item.score} · schema {item.schema_status}</summary>
      {item.error && <p className="text-xs text-red-700">{item.error}</p>}
      <div className="mt-2 flex flex-wrap gap-2">{item.columns?.map(col => <span key={col.column_name} title={col.matched_terms?.join(", ")} className="rounded bg-white px-2 py-1 text-xs text-slate-700 ring-1 ring-slate-200">{col.column_name} <span className="text-slate-400">{col.data_type}</span></span>)}</div>
      {!item.columns?.length && <p className="mt-2 text-xs text-amber-700">No columns selected by the lexical retriever.</p>}
    </details>)}
    <p className="text-xs text-slate-500">{result.assurance_note || "Schema checks do not prove semantic correctness."}</p>
  </div>;
}
export default function BusinessQuestionAssurance() {
  const [tab, setTab] = useState<"ask" | "bulk">("ask");
  const [question, setQuestion] = useState(EXAMPLES[0]);
  const [limit, setLimit] = useState(20);
  const [single, setSingle] = useState<Result | null>(null);
  const [supervisor, setSupervisor] = useState<SupervisorResult | null>(null);
  const [supervisorError, setSupervisorError] = useState("");
  const [bulk, setBulk] = useState<Result[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function ask() {
    setBusy(true);
    setError("");
    setSingle(null);
    setSupervisor(null);
    setSupervisorError("");

    try {
      const metadata = await post<Result>("/ask", {question});
      setSingle(metadata);

      try {
        const response = await fetch(
          "/api/heaap/api/supervisor-metadata/select",
          {
            method: "POST",
            headers: {"content-type": "application/json"},
            body: JSON.stringify({question})
          }
        );

        if (!response.ok) {
          throw new Error(`Supervisor API HTTP ${response.status}`);
        }

        const selected = await response.json() as SupervisorResult;
        setSupervisor(selected);
      } catch (e) {
        setSupervisorError(
          e instanceof Error ? e.message : "Supervisor request failed"
        );
      }
    } catch(e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  async function runBulk() {
    setBusy(true); setError(""); setBulk([]);
    try { const data = await post<{results: Result[]}>("/bulk", {limit}); setBulk(data.results); }
    catch(e) {setError(e instanceof Error ? e.message : "Request failed");}
    finally {setBusy(false);}
  }
  return <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
    <div className="mb-4"><h3 className="text-lg font-bold text-slate-900">Business Question → Relevant Metadata</h3><p className="text-sm text-slate-500">Dynamic Databricks Gold metadata matching and schema checks. Semantic approval is not yet implemented.</p></div>
    <div className="mb-4 flex gap-2"><button onClick={()=>setTab("ask")} className={`rounded-lg px-4 py-2 text-sm ${tab==="ask"?"bg-indigo-600 text-white":"bg-slate-100"}`}>Ask Business Question</button><button onClick={()=>setTab("bulk")} className={`rounded-lg px-4 py-2 text-sm ${tab==="bulk"?"bg-indigo-600 text-white":"bg-slate-100"}`}>Bulk Question Testing</button></div>
    {tab==="ask" ? <div className="space-y-3"><textarea aria-label="Business question" className="w-full rounded-lg border p-3 text-sm" rows={2} value={question} onChange={e=>setQuestion(e.target.value)} /><div className="flex flex-wrap gap-2">{EXAMPLES.map(q=><button key={q} onClick={()=>setQuestion(q)} className="rounded border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50">{q}</button>)}</div><button disabled={busy || question.trim().length<3} onClick={()=>void ask()} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{busy?"Retrieving...":"Retrieve & Validate Metadata"}</button>{single && <Mapping result={single}/>}
    {supervisor && <SupervisorPanel result={supervisor}/>}
    {supervisorError && (
      <p className="text-sm text-red-700">
        Supervisor: {supervisorError}
      </p>
    )}</div> : <div className="space-y-3"><label className="block text-sm">Generated questions (1–100) <input type="number" min={1} max={100} value={limit} onChange={e=>setLimit(Math.max(1,Math.min(100,Number(e.target.value)||1)))} className="ml-2 w-24 rounded border p-2" /></label><button disabled={busy} onClick={()=>void runBulk()} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{busy?"Testing...":"Generate & Test Questions"}</button>{bulk.length>0 && <><p className="text-sm">{bulk.length} generated questions · {bulk.filter(r=>r.status==="ERROR").length} errors · semantic verification pending for all</p><div className="max-h-[620px] space-y-3 overflow-y-auto">{bulk.map((r,i)=><Mapping key={i} result={r}/>)}</div></>}</div>}
    {error && <p role="alert" className="mt-3 rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
  </section>;
}
