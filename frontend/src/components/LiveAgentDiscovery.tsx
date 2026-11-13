"use client";

import { useState } from "react";

type Agent = {
  agent_id: string;
  name?: string;
  status?: string;
  framework?: string;
  environment?: string;
  capabilities?: string[];
};

function extractAgents(data: unknown): Agent[] {
  if (Array.isArray(data)) return data as Agent[];

  if (data && typeof data === "object") {
    const obj = data as Record<string, unknown>;

    for (const key of ["agents", "value", "results", "matches"]) {
      if (Array.isArray(obj[key])) return obj[key] as Agent[];
    }
  }

  return [];
}

export default function LiveAgentDiscovery() {
  const [capability, setCapability] = useState("generate_sql");
  const [registered, setRegistered] = useState<Agent[]>([]);
  const [eligible, setEligible] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");

  async function discover() {
    const cap = capability.trim();
    if (!cap) return;

    setLoading(true);
    setError("");
    setSearched(false);

    try {
      const [registryResponse, supervisorResponse] =
        await Promise.all([
          fetch("/api/heaap/registry/agents", {
            cache: "no-store",
          }),
          fetch(
            `/api/heaap/supervisor/capabilities/${encodeURIComponent(cap)}/agents`,
            { cache: "no-store" }
          ),
        ]);

      if (!registryResponse.ok) {
        throw new Error("Agent Registry API failed");
      }

      if (!supervisorResponse.ok) {
        throw new Error("Supervisor capability lookup failed");
      }

      const registryData = await registryResponse.json();
      const supervisorData = await supervisorResponse.json();

      const matches = extractAgents(registryData).filter(agent =>
        agent.capabilities?.some(
          value => value.toLowerCase() === cap.toLowerCase()
        )
      );

      setRegistered(matches);
      setEligible(extractAgents(supervisorData));
      setSearched(true);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Discovery failed"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <p className="mb-3 text-sm text-slate-500">
          Discover registered agents and check supervisor execution
          eligibility by capability.
        </p>

        <div className="flex flex-wrap gap-3">
          <input
            value={capability}
            onChange={e => setCapability(e.target.value)}
            placeholder="generate_sql"
            className="min-w-0 flex-1 rounded-lg border border-slate-200 p-3"
          />

          <button
            onClick={() => void discover()}
            disabled={loading || !capability.trim()}
            className="rounded-lg bg-indigo-600 px-5 py-3 text-sm font-semibold text-white disabled:opacity-50"
          >
            {loading ? "Searching..." : "Discover Agents"}
          </button>
        </div>
      </div>

      {error && (
        <p role="alert" className="text-sm text-red-600">{error}</p>
      )}

      {searched && !error && (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg bg-slate-50 p-4">
              <p className="text-sm text-slate-500">
                Registered matches
              </p>
              <p className="text-3xl font-bold">{registered.length}</p>
            </div>

            <div className="rounded-lg bg-slate-50 p-4">
              <p className="text-sm text-slate-500">
                Supervisor eligible
              </p>
              <p className="text-3xl font-bold">{eligible.length}</p>
            </div>
          </div>

          <div className="space-y-3">
            {registered.map(agent => {
              const approved = eligible.some(
                item => item.agent_id === agent.agent_id
              );

              return (
                <div
                  key={agent.agent_id}
                  className="rounded-lg border border-slate-200 p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <strong>
                      {agent.name || agent.agent_id}
                    </strong>

                    <span className={`rounded-full px-2 py-1 text-xs font-semibold ${
                      approved
                        ? "bg-green-100 text-green-700"
                        : "bg-amber-100 text-amber-700"
                    }`}>
                      {approved
                        ? "Supervisor eligible"
                        : "Not supervisor eligible"}
                    </span>
                  </div>

                  <p className="mt-2 text-xs text-slate-500">
                    ID: {agent.agent_id}
                  </p>

                  <p className="mt-1 text-xs text-slate-500">
                    Status: {agent.status || "Unknown"}
                  </p>

                  <p className="mt-1 text-xs text-slate-500">
                    Capabilities: {agent.capabilities?.join(", ") || "None"}
                  </p>
                </div>
              );
            })}

            {registered.length === 0 && (
              <p className="text-sm text-slate-500">
                No registered agents support this capability.
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
}