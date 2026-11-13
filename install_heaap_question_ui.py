from pathlib import Path
import shutil

ROOT = Path.cwd()
MAIN = ROOT / 'app/main.py'
PAGE = ROOT / 'frontend/src/app/page.tsx'
PROXY = ROOT / 'frontend/src/app/api/heaap/[...path]/route.ts'
SERVICE = ROOT / 'app/services/dynamic_business_metadata.py'
for path in (MAIN, PAGE, PROXY, SERVICE):
    if not path.is_file():
        raise SystemExit(f'Missing required file: {path}. Run from HEAAP project root.')

def backup_and_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_name(path.name + '.before_question_ui')
        if not backup.exists():
            shutil.copy2(path, backup)
    path.write_text(value, encoding='utf-8')

route_path = ROOT / 'app/api/routes/business_question_routes.py'
route_text = '''from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.dynamic_business_metadata import retrieve_metadata, normalize_rows
from app.services.metadata_service import list_tables, get_columns

router = APIRouter(prefix="/api/business-metadata", tags=["Business Metadata"])

class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)

class BulkRequest(BaseModel):
    limit: int = Field(default=25, ge=1, le=100)


def validate_candidate(candidate):
    # Schema check against current Unity Catalog metadata; NOT independent semantic assurance.
    table = candidate["table_name"]
    reference = normalize_rows(get_columns(table), ["column_name", "data_type", "comment"])
    indexed = {str(row["column_name"]).lower(): str(row.get("data_type", "")).upper() for row in reference}
    checks = []
    for col in candidate.get("columns", []):
        name = str(col["column_name"])
        expected_type = indexed.get(name.lower())
        valid = expected_type is not None and expected_type == str(col.get("data_type", "")).upper()
        checks.append({"column": name, "valid": valid})
    return {
        **candidate,
        "schema_status": "PASS" if checks and all(c["valid"] for c in checks) else "INCONCLUSIVE" if not checks else "FAIL",
        "semantic_status": "INCONCLUSIVE",
        "checks": checks,
    }


def evaluate(question):
    result = retrieve_metadata(question)
    validated = []
    for candidate in result.get("relevant_metadata", []):
        try:
            validated.append(validate_candidate(candidate))
        except Exception as exc:
            validated.append({**candidate, "schema_status": "ERROR", "semantic_status": "INCONCLUSIVE", "checks": [], "error": str(exc)})
    return {
        "question": question,
        "status": result["status"],
        "total_candidates": result["total_candidates"],
        "relevant_metadata": validated,
        "assurance_status": "INCONCLUSIVE",
        "assurance_note": "Schema checks use current catalog metadata. Semantic relevance and completeness are not independently verified; SQL execution is not authorized by this result.",
    }


@router.post("/ask")
def ask(request: QuestionRequest):
    try:
        return evaluate(request.question)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Metadata lookup failed: {exc}") from exc


def generate_questions(limit):
    tables = normalize_rows(list_tables(), ["table_name", "table_type"])
    questions = []
    seen = set()
    def add(q):
        if q not in seen and len(questions) < limit:
            questions.append(q)
            seen.add(q)
    for row in tables:
        table = str(row["table_name"])
        if not table.startswith("gold_"):
            continue
        add(f"Show the schema of {table}")
        columns = normalize_rows(get_columns(table), ["column_name", "data_type", "comment"])
        for col in columns:
            name = str(col["column_name"])
            if name.endswith("_id"):
                add(f"Show {name} from {table}")
            elif name.endswith("_date") or name in ("snapshot_date",):
                add(f"Show records by {name} in {table}")
            elif any(t in name for t in ("amount", "balance", "total_", "rate", "score", "count", "installment")):
                add(f"What is the total {name} in {table}?")
            elif name.endswith("_status") or name.endswith("_type"):
                add(f"Show records grouped by {name} in {table}")
            if len(questions) >= limit:
                break
        if len(questions) >= limit:
            break
    return questions


@router.post("/bulk")
def bulk(request: BulkRequest):
    try:
        questions = generate_questions(request.limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Question generation failed: {exc}") from exc
    results = []
    for question in questions:
        try:
            results.append(evaluate(question))
        except Exception as exc:
            results.append({"question": question, "status": "ERROR", "assurance_status": "ERROR", "relevant_metadata": [], "error": str(exc)})
    return {"generated": len(questions), "results": results,
            "note": "These are schema-derived test prompts, not all possible business questions or verified expected answers."}
'''
backup_and_write(route_path, route_text)

component_path = ROOT / 'frontend/src/components/BusinessQuestionAssurance.tsx'
component_text = '''"use client";
import { useState } from "react";

type Column = { column_name: string; data_type?: string; matched_terms?: string[] };
type Candidate = { table_name: string; score: number; columns: Column[]; schema_status: string; semantic_status: string; checks?: {column: string; valid: boolean}[]; error?: string };
type Result = { question: string; status: string; total_candidates?: number; relevant_metadata: Candidate[]; assurance_status: string; assurance_note?: string; error?: string };
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
  const [bulk, setBulk] = useState<Result[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function ask() {
    setBusy(true); setError(""); setSingle(null);
    try { setSingle(await post<Result>("/ask", {question})); }
    catch(e) {setError(e instanceof Error ? e.message : "Request failed");}
    finally {setBusy(false);}
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
    {tab==="ask" ? <div className="space-y-3"><textarea aria-label="Business question" className="w-full rounded-lg border p-3 text-sm" rows={2} value={question} onChange={e=>setQuestion(e.target.value)} /><div className="flex flex-wrap gap-2">{EXAMPLES.map(q=><button key={q} onClick={()=>setQuestion(q)} className="rounded border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50">{q}</button>)}</div><button disabled={busy || question.trim().length<3} onClick={()=>void ask()} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{busy?"Retrieving...":"Retrieve & Validate Metadata"}</button>{single && <Mapping result={single}/>}</div> : <div className="space-y-3"><label className="block text-sm">Generated questions (1–100) <input type="number" min={1} max={100} value={limit} onChange={e=>setLimit(Math.max(1,Math.min(100,Number(e.target.value)||1)))} className="ml-2 w-24 rounded border p-2" /></label><button disabled={busy} onClick={()=>void runBulk()} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{busy?"Testing...":"Generate & Test Questions"}</button>{bulk.length>0 && <><p className="text-sm">{bulk.length} generated questions · {bulk.filter(r=>r.status==="ERROR").length} errors · semantic verification pending for all</p><div className="max-h-[620px] space-y-3 overflow-y-auto">{bulk.map((r,i)=><Mapping key={i} result={r}/>)}</div></>}</div>}
    {error && <p role="alert" className="mt-3 rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
  </section>;
}
'''
backup_and_write(component_path, component_text)

source = MAIN.read_text(encoding='utf-8-sig')
registration = '\nfrom app.api.routes.business_question_routes import router as business_question_router\napp.include_router(business_question_router)\n'
if 'app.include_router(business_question_router)' not in source:
    if 'app = FastAPI(' not in source and 'app=FastAPI(' not in source:
        raise SystemExit('Cannot identify FastAPI app declaration. Route and component created; main.py not modified.')
    backup_and_write(MAIN, source.rstrip() + '\n' + registration)

source = PROXY.read_text(encoding='utf-8-sig')
if 'path === "api/business-metadata/ask"' not in source:
    marker = 'if (method === "POST") return '
    if marker not in source:
        raise SystemExit('Proxy POST allowlist format unexpected; manual change needed.')
    source = source.replace(marker, marker + '(path === "api/business-metadata/ask" || path === "api/business-metadata/bulk") || ', 1)
    backup_and_write(PROXY, source)

source = PAGE.read_text(encoding='utf-8-sig')
if 'import BusinessQuestionAssurance from ' not in source:
    marker = 'import DynamicMetadataAssurance from "../components/DynamicMetadataAssurance";'
    if marker not in source:
        raise SystemExit('Dashboard import marker not found; manual insertion needed.')
    source = source.replace(marker, marker + '\nimport BusinessQuestionAssurance from "../components/BusinessQuestionAssurance";', 1)
if '<BusinessQuestionAssurance />' not in source:
    marker = '<DynamicMetadataAssurance />'
    if marker not in source:
        raise SystemExit('Dashboard insertion marker not found; manual insertion needed.')
    source = source.replace(marker, marker + '\n<BusinessQuestionAssurance />', 1)
backup_and_write(PAGE, source)
print('Installed Business Question Assurance routes and dashboard component.')
print('Restart FastAPI and Next.js, then test /api/business-metadata/ask.')
