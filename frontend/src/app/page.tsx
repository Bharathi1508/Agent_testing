"use client";

import DynamicMetadataAssurance from "../components/DynamicMetadataAssurance";
import BusinessQuestionAssurance from "../components/BusinessQuestionAssurance";
import SQLAssuranceOverview from "../components/SQLAssuranceOverview";
import LiveAgentDiscovery from "../components/LiveAgentDiscovery";
import AgentLastAssurance from "../components/AgentLastAssurance";
import FunctionalAssuranceStatus from "../components/FunctionalAssuranceStatus";
import MetadataAssuranceOverview from "../components/MetadataAssuranceOverview";

import { useCallback, useEffect, useState } from "react";
import DetailedAssuranceReport from "../components/DetailedAssuranceReport";

type Agent = { agent_id: string; agent_name?: string; name?: string; status?: string; capabilities?: string[]; execution_type?: string; environment?: string };
type LiveSummary = {
  total_tests: number;
  passed: number;
  failed: number;
  other: number;
  unique_agents: number;
  average_score: number | null;
};

type LiveRun = {
  id: number;
  agent_id: string;
  status: string;
  created_at: string;
  score: number | null;
  assurance_type: string | null;
  report?: {
    checks?: Array<{
      name: string;
      passed: boolean;
      message?: string;
    }>;
    results?: Array<{
      name: string;
      passed: boolean;
      errors?: string[];
    }>;
  };
};

type LiveTrend = {
  date: string;
  passed: number;
  failed: number;
  other: number;
};
type Screen = "Overview" | "Agent Registry" | "Agent Discovery" | "Assurance Testing" | "Governance" | "Dynamic Supervisor" | "Audit Logs" | "Reports & Analytics";
const screens: { name: Screen; icon: string }[] = [
  { name: "Overview", icon: "⌂" }, { name: "Agent Registry", icon: "☷" },
  { name: "Agent Discovery", icon: "◎" }, { name: "Assurance Testing", icon: "✓" },
  { name: "Governance", icon: "♙" }, { name: "Dynamic Supervisor", icon: "◇" },
  { name: "Audit Logs", icon: "▤" }, { name: "Reports & Analytics", icon: "▥" },
];
const API = "/api/heaap";
async function call(path: string, method = "GET") {
  const res = await fetch(`${API}${path}`, { method, cache: "no-store" });
  const raw = await res.text();
  let data: unknown;
  try { data = JSON.parse(raw); } catch { data = { message: raw }; }
  if (!res.ok) {
    const obj = data as Record<string, unknown>;
    throw new Error(String(obj.detail ?? obj.error ?? obj.message ?? `HTTP ${res.status}`));
  }
  return data;
}
function Card({ title, children, action }: { title: string; children: React.ReactNode; action?: React.ReactNode }) {
  return <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-[0_3px_14px_rgba(25,39,80,0.06)]">
    <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-3"><h3 className="font-bold text-slate-900">{title}</h3>{action}</div>
    <div className="p-4">{children}</div>
  </section>;
}
function Empty({ text }: { text: string }) { return <div className="flex min-h-28 items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50 p-4 text-center text-sm text-slate-500">{text}</div>; }
export default function Home() {
  const [screen, setScreen] = useState<Screen>("Overview");
  const [agents, setAgents] = useState<Agent[]>([]);
  const [health, setHealth] = useState("Checking");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updated, setUpdated] = useState("");
  const [selected, setSelected] = useState("metadata_agent_001");
  const [capability, setCapability] = useState("generate_sql");
  const [result, setResult] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [liveSummary, setLiveSummary] =
    useState<LiveSummary | null>(null);

  const [liveReports, setLiveReports] =
    useState<LiveRun[]>([]);

  const [liveTrend, setLiveTrend] =
    useState<LiveTrend[]>([]);

  const [liveError, setLiveError] = useState("");

  const refreshLive = useCallback(async () => {
    try {
      const [s, r, t] = await Promise.all([
        call("/api/assurance/live/summary"),
        call("/api/assurance/live/reports"),
        call("/api/assurance/live/trend")
      ]);

      setLiveSummary(s as LiveSummary);

      setLiveReports(
        ((r as { reports: LiveRun[] }).reports ?? [])
          .slice()
          .sort((a, b) => b.id - a.id)
      );

      setLiveTrend(
        (t as { trend: LiveTrend[] }).trend ?? []
      );

      setLiveError("");
    } catch (e) {
      setLiveError(
        e instanceof Error
          ? e.message
          : "Live reporting unavailable"
      );
    }
  }, []);

  useEffect(() => {
    void refreshLive();

    const timer = setInterval(
      () => void refreshLive(),
      30000
    );

    return () => clearInterval(timer);
  }, [refreshLive]);

  const statusBadge = (status: string) => (
    <span className={`rounded-full px-2 py-1 text-xs font-semibold ${
      status === "passed"
        ? "bg-green-100 text-green-700"
        : status === "failed"
          ? "bg-red-100 text-red-700"
          : "bg-slate-100 text-slate-700"
    }`}>
      {status.toUpperCase()}
    </span>
  );

  const recentAssurance = (
    <div className="space-y-3">
      {liveReports.length === 0 &&
        <Empty text={liveError || "No assurance runs"} />}

      {liveReports.slice(0, 5).map(run => (
        <div
          key={run.id}
          className="flex items-center justify-between gap-3 border-b py-2"
        >
          <div>
            <div className="text-xs font-semibold">
              {run.agent_id}
            </div>

            <div className="text-xs text-slate-500">
              Run #{run.id} - {new Date(run.created_at).toLocaleString()}
            </div>

            <div className="text-xs text-slate-500">
              {run.assurance_type ?? "Agent execution test"}
            </div>
          </div>

          <div className="text-right">
            {statusBadge(run.status)}

            <div className="mt-1 text-xs">
              {run.score == null
                ? "Not scored"
                : `${run.score}% checks passed`}
            </div>
          </div>
        </div>
      ))}
    </div>
  );

  const assuranceTrend = (
    <div className="space-y-3">
      {liveTrend.length === 0 &&
        <Empty text={liveError || "No trend data"} />}

      {liveTrend.map(day => {
        const total =
          day.passed + day.failed + day.other;

        return (
          <div key={day.date}>
            <div className="flex justify-between text-xs">
              <span>{day.date}</span>
              <span>{total} runs</span>
            </div>

            <div className="mt-1 flex h-4 overflow-hidden rounded bg-slate-100">
              <div
                className="bg-green-500"
                style={{
                  width: `${total ? day.passed / total * 100 : 0}%`
                }}
              />

              <div
                className="bg-red-500"
                style={{
                  width: `${total ? day.failed / total * 100 : 0}%`
                }}
              />
            </div>

            <div className="mt-1 text-xs text-slate-500">
              {day.passed} passed - {day.failed} failed
            </div>
          </div>
        );
      })}
    </div>
  );

  const assuranceRuns = (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-xs">
        <thead>
          <tr>
            {["Run", "Agent", "Score", "Status"].map(h => (
              <th key={h} className="p-2">{h}</th>
            ))}
          </tr>
        </thead>

        <tbody>
          {liveReports.slice(0, 10).map(run => (
            <tr key={run.id} className="border-t">
              <td className="p-2">#{run.id}</td>
              <td className="p-2">{run.agent_id}</td>
              <td className="p-2">
                {run.score == null ? "N/A" : `${run.score}%`}
              </td>
              <td className="p-2">
                {statusBadge(run.status)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const assuranceDetails = (
    <div className="space-y-3">
      {liveReports.map(run => (
        <details key={run.id} className="rounded-lg border p-3">
          <summary className="cursor-pointer text-sm font-semibold">
            Run #{run.id} - {run.agent_id} - {run.status}
          </summary>

          <p className="my-2 text-xs text-slate-500">
            {run.assurance_type ?? "Execution test"} -
            {run.score == null ? " Not scored" : ` ${run.score}%`}
          </p>

          {(run.report?.checks ?? run.report?.results ?? [])
            .map((check, index) => (
              <div
                key={index}
                className="my-1 rounded bg-slate-50 p-2 text-xs"
              >
                <strong className={
                  check.passed ? "text-green-700" : "text-red-700"
                }>
                  {check.passed ? "PASS" : "FAIL"} - {check.name}
                </strong>

                <div>
                  {"message" in check
                    ? check.message
                    : "errors" in check
                      ? check.errors?.join(", ")
                      : ""}
                </div>
              </div>
            ))}
        </details>
      ))}
    </div>
  );
  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [h, a] = await Promise.all([call("/health"), call("/registry/agents")]);
      const hv = h as Record<string, unknown>;
      const av = a as Record<string, unknown>;
      const list = Array.isArray(a) ? a : (av.agents ?? av.value ?? av.data ?? []);
      if (!Array.isArray(list)) throw new Error("Unexpected registry response format");
      setAgents(list as Agent[]);
      setHealth(String(hv.status ?? "Connected"));
      setUpdated(new Date().toLocaleTimeString());
      setError("");
    } catch (e) { setHealth("Unavailable"); setError(e instanceof Error ? e.message : "Connection failed"); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  const active = agents.filter(a => a.status?.toLowerCase() === "active").length;
  const inactive = agents.filter(a => a.status?.toLowerCase() === "inactive").length;
  const other = agents.length - active - inactive;
  const pct = (n: number) => agents.length ? Math.round(n / agents.length * 100) : 0;
  const nav = (name: Screen) => { setScreen(name); setResult(null); setError(""); };
  async function run(path: string, method = "GET") {
    setBusy(true); setResult(null); setError("");
    try { setResult(await call(path, method)); await refresh(); await refreshLive(); }
    catch (e) { setError(e instanceof Error ? e.message : "Request failed"); }
    finally { setBusy(false); }
  }
  const agentTable = <div className="overflow-x-auto"><table className="w-full min-w-[570px] text-left text-xs">
    <thead className="bg-slate-50 text-slate-500"><tr>{["Agent ID / Name", "Capabilities", "Status", "Last Assurance"].map(h => <th key={h} className="px-3 py-3 font-semibold">{h}</th>)}</tr></thead>
    <tbody>{agents.map(a => <tr key={a.agent_id} className="border-t border-slate-100">
      <td className="px-3 py-3"><div className="font-semibold text-slate-900">{a.agent_name ?? a.name ?? a.agent_id}</div><div className="mt-1 text-[11px] text-slate-500">{a.agent_id}</div></td>
      <td className="max-w-56 px-3 py-3"><div className="flex flex-wrap gap-1">{(a.capabilities ?? []).map(c => <span key={c} className="rounded bg-indigo-50 px-2 py-1 text-[10px] text-indigo-700">{c.replaceAll("_", " ")}</span>)}</div></td>
      <td className="px-3 py-3"><span className={`rounded-full px-2 py-1 font-semibold ${a.status === "active" ? "bg-green-100 text-green-700" : "bg-orange-100 text-orange-700"}`}>{a.status ?? "unknown"}</span></td>
      <td className="px-3 py-3">
  <AgentLastAssurance
    agentId={a.agent_id}
    fallback={(() => {
      const latest = liveReports.find(r => r.agent_id === a.agent_id);
      return latest
        ? statusBadge(latest.status)
        : <span className="text-slate-400">No runs</span>;
    })()}
  />
</td>
    </tr>)}</tbody></table>{agents.length === 0 && <Empty text={loading ? "Loading agents..." : "No registered agents returned"} />}</div>;
  const action = (label: string, destination: Screen, symbol: string) => <button key={label} onClick={() => nav(destination)} className="flex min-h-12 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-left text-xs font-semibold text-slate-800 hover:border-indigo-300 hover:bg-indigo-50"><span className="text-lg text-indigo-600">{symbol}</span>{label}</button>;
  return <div className="flex min-h-screen bg-[#f5f7fc] text-slate-900">
    <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col bg-[#07142f] text-white">
      <div className="border-b border-slate-700/40 px-5 py-6"><div className="flex items-center gap-3"><span className="text-3xl text-cyan-400">HEAAP:</span><div><div className="text-xl font-extrabold tracking-wide">HEAAP</div><div className="text-[10px] leading-4 text-slate-300">Hybrid Enterprise<br/>Agent Assurance Platform</div></div></div></div>
      <nav className="flex-1 space-y-1 overflow-y-auto p-3">{screens.map(s => <button key={s.name} onClick={() => nav(s.name)} className={`flex w-full items-center gap-3 rounded-lg px-4 py-3 text-left text-sm ${screen === s.name ? "bg-gradient-to-r from-indigo-600 to-violet-600 font-semibold text-white" : "text-slate-300 hover:bg-slate-800"}`}><span className="w-5 text-lg">{s.icon}</span>{s.name}</button>)}</nav>
      <div className="m-3 rounded-lg border border-slate-700 px-3 py-3 text-xs"><div className="font-semibold"><span className={health.toLowerCase() === "healthy" ? "text-green-400" : "text-amber-400"}>Online:</span> Backend: {health}</div><div className="mt-2 text-slate-400">FastAPI - Local POC</div></div>
    </aside>
    <main className="min-w-0 flex-1"><header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-6 py-5"><div><h1 className="text-2xl font-bold">{screen}</h1><p className="text-sm text-slate-500">Monitor agents, testing, approvals and supervisor operations.</p></div><div className="flex items-center gap-2"><span className="hidden text-xs text-slate-500 lg:block">{updated ? `Last updated: ${updated}` : "Connecting..."}</span><button onClick={() => { void refresh(); void refreshLive(); }} className="rounded-lg border border-slate-200 px-3 py-2 text-sm hover:bg-slate-50">Refresh: Refresh</button><button onClick={() => nav("Dynamic Supervisor")} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">Run: Run Supervisor</button></div></header>
      <div className="mx-auto max-w-[1500px] space-y-4 p-5">{error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
{liveError && <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">Live assurance: {liveError}</div>}
        {screen === "Overview" && <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{[
            { label: "Registered Agents", value: agents.length, icon: "♙", color: "text-indigo-600", sub: "Live registry" },
            { label: "Active Agents", value: active, icon: "✓", color: "text-green-600", sub: `${pct(active)}% of registered` },
            { label: "Assurance Tests", value: <FunctionalAssuranceStatus variant="card" />, icon: "✓", color: "text-green-600", sub: "Latest functional metadata assurance" },
            { label: "Pending Approvals", value: "-", icon: "▤", color: "text-orange-600", sub: "Queue API not connected" },
            { label: "Platform Health", value: health, icon: "⬡", color: "text-green-600", sub: "FastAPI health endpoint" },
          ].map(k => <div key={k.label} className="min-h-32 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex items-center gap-2"><span className={`text-2xl ${k.color}`}>{k.icon}</span><span className="text-xs font-semibold">{k.label}</span></div><div className="mt-2 text-2xl font-bold">{loading ? "..." : k.value}</div><div className="mt-1 text-[11px] text-slate-500">{k.sub}</div></div>)}</div>
          <div className="mb-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
  <h3 className="mb-3 text-sm font-semibold text-slate-900">
    Functional Assurance Tests
  </h3>
  <FunctionalAssuranceStatus variant="card" />
</div>
<MetadataAssuranceOverview />
<DynamicMetadataAssurance />
<BusinessQuestionAssurance />
<SQLAssuranceOverview />
<div className="grid gap-4 xl:grid-cols-[1.35fr_1fr]"><Card title={`Registered Agents (${agents.length})`} action={<button onClick={() => nav("Agent Registry")} className="text-xs font-semibold text-indigo-600">View All â†’</button>}>{agentTable}</Card><Card title="Recent Assurance Results" action={<button onClick={() => nav("Reports & Analytics")} className="text-xs font-semibold text-indigo-600">View Reports â†’</button>}><div className="space-y-3">
  <FunctionalAssuranceStatus variant="recent" />
  <details className="border-t border-slate-200 pt-3">
  <summary className="cursor-pointer text-xs font-semibold text-slate-600">
    View Historical Assurance Runs
  </summary>
  <div className="mt-3">
    {recentAssurance}
  </div>
</details>
</div></Card></div>
          <div className="grid gap-4 lg:grid-cols-3"><Card title="Assurance Test Trend">
  <div className="space-y-4">
    <FunctionalAssuranceStatus variant="recent" />
    <details className="border-t border-slate-200 pt-3">
      <summary className="cursor-pointer text-xs font-semibold text-indigo-600">
        View Historical Trend
      </summary>
      <div className="mt-3">
        {assuranceTrend}
      </div>
    </details>
  </div>
</Card><Card title="Agent Status Distribution"><div className="flex flex-wrap items-center justify-center gap-5 py-3"><div className="relative flex h-40 w-40 items-center justify-center rounded-full" style={{ background: agents.length ? `conic-gradient(#16a34a 0 ${pct(active)}%, #fb923c ${pct(active)}% ${pct(active)+pct(inactive)}%, #94a3b8 ${pct(active)+pct(inactive)}% 100%)` : "#e2e8f0" }}><div className="flex h-28 w-28 flex-col items-center justify-center rounded-full bg-white"><span className="text-3xl font-bold">{agents.length}</span><span className="text-xs">Agents</span></div></div><div className="space-y-2 text-xs"><div>ðŸŸ¢ Active ({active}) - {pct(active)}%</div><div>ðŸŸ  Inactive ({inactive}) - {pct(inactive)}%</div><div>âšª Other ({other}) - {pct(other)}%</div></div></div></Card><Card title="Quick Actions"><div className="grid grid-cols-2 gap-2">{action("Run Assurance Test", "Assurance Testing", "Run:")}{action("Register Agent", "Agent Registry", "+")}{action("Discover Agents", "Agent Discovery", "Agents:")}{action("Run Supervisor", "Dynamic Supervisor", "â—‡")}{action("Review Governance", "Governance", "HEAAP:")}{action("View Reports", "Reports & Analytics", "Queue:")}</div></Card></div>
          <div className="grid gap-4 xl:grid-cols-[1.35fr_1fr]"><Card title="Latest Assurance Runs">
  <div className="space-y-4">
    <FunctionalAssuranceStatus variant="recent" />
    <details className="border-t border-slate-200 pt-3">
  <summary className="cursor-pointer text-xs font-semibold text-slate-600">
    View Previous Assurance Runs
  </summary>
  <div className="mt-3">
    {assuranceRuns}
  </div>
</details>
  </div>
</Card><Card title="Supervisor Execution (Multi-Agent)"><div className="space-y-2 text-sm text-slate-700"><p>OK Select a business-query test suite</p><p>OK Run checks across registered agents</p><p>OK Validate metadata, SQL and results</p><p>OK Generate a QA report and recommendations</p></div><button onClick={() => nav("Dynamic Supervisor")} className="mt-5 w-full rounded-lg bg-indigo-600 px-4 py-3 text-sm font-semibold text-white">Run: Open Supervisor</button><p className="mt-2 text-xs text-slate-500">Full multi-agent execution requires a verified backend endpoint.</p></Card></div>
        </>}
        {screen === "Agent Registry" && <Card title="Live Agent Registry">{agentTable}</Card>}
        {screen === "Agent Discovery" && (
  <Card title="Agent Discovery">
    <LiveAgentDiscovery />
  </Card>
)}
{screen === "Assurance Testing" && <Card title="Run Assurance Test"><p className="mb-4 text-sm text-slate-500">This explicitly invokes the backend assurance endpoint. Its existing HTTP 500 error must be fixed before results can be shown.</p><select value={selected} onChange={e => setSelected(e.target.value)} className="w-full rounded-lg border p-3">{agents.map(a => <option key={a.agent_id} value={a.agent_id}>{a.agent_name ?? a.name ?? a.agent_id}</option>)}</select><button disabled={busy || !selected} onClick={() => void run(`/assurance/test/${encodeURIComponent(selected)}`, "POST")} className="mt-4 rounded-lg bg-indigo-600 px-5 py-3 text-sm text-white disabled:opacity-50">{busy ? "Running..." : "Run Assurance Test"}</button><p className="mt-3 text-xs text-slate-500">Running a test does not approve or activate an agent.</p></Card>}
        {screen === "Governance" && <Card title="Governance Status & History"><select value={selected} onChange={e => setSelected(e.target.value)} className="w-full rounded-lg border p-3">{agents.map(a => <option key={a.agent_id} value={a.agent_id}>{a.agent_id}</option>)}</select><div className="mt-4 flex gap-3"><button onClick={() => void run(`/governance/status/${encodeURIComponent(selected)}`)} className="rounded-lg bg-indigo-600 px-4 py-3 text-sm text-white">Check Status</button><button onClick={() => void run(`/governance/history/${encodeURIComponent(selected)}`)} className="rounded-lg border px-4 py-3 text-sm">View History</button></div><p className="mt-3 text-xs text-slate-500">Approval and rejection require a separate authorized human-review workflow.</p></Card>}
        {screen === "Dynamic Supervisor" && <Card title="Dynamic Supervisor"><p className="mb-3 text-sm text-slate-500">Explore agents with a requested capability. Supervisor batch execution is not yet connected.</p><input value={capability} onChange={e => setCapability(e.target.value)} className="w-full rounded-lg border p-3"/><div className="mt-4 space-y-2">{agents.filter(a => a.capabilities?.some(c => c.toLowerCase().includes(capability.toLowerCase()))).map(a => <div key={a.agent_id} className="rounded-lg border p-3 text-sm">{a.agent_id} - {a.status}</div>)}</div></Card>}
        {screen === "Audit Logs" && <Card title="Governance Audit History"><select value={selected} onChange={e => setSelected(e.target.value)} className="w-full rounded-lg border p-3">{agents.map(a => <option key={a.agent_id} value={a.agent_id}>{a.agent_id}</option>)}</select><button onClick={() => void run(`/governance/history/${encodeURIComponent(selected)}`)} className="mt-4 rounded-lg bg-indigo-600 px-5 py-3 text-sm text-white">Load History</button></Card>}
        {screen === "Reports & Analytics" && <Card title="Reports & Analytics"><div className="space-y-4">
  <p className="text-sm text-slate-500">
    Live SQLite assurance reporting
  </p>

  <div className="grid grid-cols-3 gap-3">
    {[
      ["Tests", liveSummary?.total_tests ?? "-"],
      ["Passed", liveSummary?.passed ?? "-"],
      ["Failed", liveSummary?.failed ?? "-"]
    ].map(([label, value]) => (
      <div
        key={String(label)}
        className="rounded-lg bg-slate-50 p-4 text-center"
      >
        <div className="text-xs">{label}</div>
        <div className="text-2xl font-bold">{value}</div>
      </div>
    ))}
  </div>

  <h3 className="font-semibold">Assurance Trend</h3>
  {assuranceTrend}

  <h3 className="font-semibold">Latest Runs</h3>
  {assuranceRuns}

  <h3 className="font-semibold">Detailed Reports</h3>
  {assuranceDetails}
</div><div className="grid grid-cols-3 gap-3">{[["Registered",agents.length],["Active",active],["Inactive",inactive]].map(([k,v]) => <div key={k} className="rounded-lg bg-slate-50 p-4 text-center"><div className="text-xs text-slate-500">{k}</div><div className="mt-2 text-2xl font-bold">{v}</div></div>)}</div></Card>}
        {screen === "Reports & Analytics" && <DetailedAssuranceReport />}
        {result !== null && <Card title="Backend Response"><pre className="max-h-96 overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-green-300">{JSON.stringify(result,null,2)}</pre></Card>}
      </div>
    </main>
  </div>;
}


