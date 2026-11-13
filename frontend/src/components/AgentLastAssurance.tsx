"use client";

import { useEffect, useState } from "react";

type Report = {
  agent_id: string;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  status: string;
  score: number;
};

export default function AgentLastAssurance({
  agentId,
  fallback,
}: {
  agentId: string;
  fallback?: React.ReactNode;
}) {
  const [report, setReport] = useState<Report | null>(null);

  useEffect(() => {
    if (agentId !== "metadata_agent_001") return;

    fetch("/api/metadata-assurance", { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error("Report unavailable");
        return response.json();
      })
      .then((data: Report) => {
        if (data.agent_id === agentId) setReport(data);
      })
      .catch(() => {});
  }, [agentId]);

  if (!report) {
    return <>{fallback ?? <span className="text-slate-400">No runs</span>}</>;
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <span
        className={`rounded-full px-3 py-1 text-xs font-bold ${
          report.status === "passed"
            ? "bg-green-100 text-green-700"
            : "bg-red-100 text-red-700"
        }`}
      >
        {report.status.toUpperCase()}
      </span>
      <span className="text-xs font-semibold text-green-700">
        {report.passed_tests}/{report.total_tests} tests passed
      </span>
    </div>
  );
}