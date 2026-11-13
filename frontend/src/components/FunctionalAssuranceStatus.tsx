"use client";

import { useEffect, useState } from "react";

type Report = {
  agent_id: string;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  score: number;
  status: string;
};

export default function FunctionalAssuranceStatus({
  variant = "card",
}: {
  variant?: "card" | "recent";
}) {
  const [report, setReport] = useState<Report | null>(null);

  useEffect(() => {
    fetch("/api/metadata-assurance", { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error("Report unavailable");
        return response.json();
      })
      .then((data: Report) => setReport(data))
      .catch(() => setReport(null));
  }, []);

  if (variant === "recent") {
    if (!report) return null;

    return (
      <div className="flex items-center justify-between gap-3 rounded-lg border border-green-200 bg-green-50 p-4">
        <div>
          <p className="font-semibold text-slate-900">
            {report.agent_id}
          </p>
          <p className="text-xs text-slate-600">
            Latest functional metadata assurance
          </p>
          <p className="mt-1 text-sm font-semibold text-green-700">
            {report.passed_tests}/{report.total_tests} tests passed
          </p>
        </div>

        <div className="text-right">
          <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-bold text-green-700">
            {report.status.toUpperCase()}
          </span>
          <p className="mt-2 text-sm font-semibold">
            {report.score}% score
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <p className="text-3xl font-bold text-green-700">
        {report
          ? `${report.passed_tests}/${report.total_tests}`
          : "--"}
      </p>
      <p className="mt-1 text-xs text-slate-500">
        {report
          ? `${report.score}% score - ${report.failed_tests} failed`
          : "Loading functional tests"}
      </p>
    </div>
  );
}