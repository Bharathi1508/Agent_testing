export type BankingAgentRun = {
  agent_id: string;
  name: string;
  role: string;
  status: string;
  summary: string;
};

type PipelineSnapshot = {
  agent_runs?: BankingAgentRun[];
  metadata_assurance_status?: string;
  metadata_validation?: {
    validation_status?: string;
  };
  independent_evaluation?: {
    validation_status?: string;
    reason?: string;
    evidence_source?: string;
  };
  selection?: {
    primary_table?: string;
    selected_columns?: string[];
  };
  sql_generation_status?: string;
  sql_generation?: {
    status?: string;
    sql?: string | null;
    reason?: string;
  };
  sql_assurance_status?: string;
  sql_assurance?: {
    status?: string;
    note?: string;
  };
  sql_supervisor_status?: string;
  sql_supervisor?: {
    status?: string;
    note?: string;
  };
  sql_execution_status?: string;
  sql_execution?: {
    status?: string;
    error?: string;
    result_validation?: {
      validation_status?: string;
    };
  };
  result_validation_status?: string;
};

export function getBankingAgentRuns(
  result: PipelineSnapshot,
): BankingAgentRun[] {
  if (result.agent_runs?.length) {
    return result.agent_runs.filter(
      agent => agent.agent_id !== "banking_assurance_orchestrator",
    );
  }

  const metadataStatus = result.metadata_assurance_status || "NOT_TESTED";
  const metadataPassed = metadataStatus === "PASS";
  const generationStatus =
    result.sql_generation_status ||
    result.sql_generation?.status ||
    (metadataPassed ? "NOT_STARTED" : "BLOCKED");
  const sqlAssuranceStatus =
    result.sql_assurance_status ||
    result.sql_assurance?.status ||
    (metadataPassed ? "NOT_TESTED" : "BLOCKED");
  const supervisorStatus =
    result.sql_supervisor_status ||
    result.sql_supervisor?.status ||
    (metadataPassed ? "NOT_TESTED" : "BLOCKED");
  const executionStatus =
    result.sql_execution_status || result.sql_execution?.status;
  const resultStatus =
    result.result_validation_status ||
    result.sql_execution?.result_validation?.validation_status ||
    (executionStatus === "ERROR" ? "ERROR" : "BLOCKED");

  return [
    {
      agent_id: "banking_question_agent",
      name: "Banking Question Agent",
      role: "Map the business question to a candidate Gold table and columns.",
      status: result.selection?.primary_table ? "PASS" : "REVIEW",
      summary: result.selection?.primary_table
        ? `Selected ${result.selection.primary_table}.`
        : "No Gold table was selected.",
    },
    {
      agent_id: "gold_metadata_assurance_agent",
      name: "Gold Metadata Assurance Agent",
      role: "Validate selected tables and columns against live metadata.",
      status:
        result.metadata_validation?.validation_status ||
        metadataStatus,
      summary: "Live metadata and expected-column checks.",
    },
    {
      agent_id: "banking_semantics_agent",
      name: "Banking Semantics Agent",
      role: "Independently review business meaning and schema alignment.",
      status:
        result.independent_evaluation?.validation_status ||
        metadataStatus,
      summary:
        result.independent_evaluation?.reason ||
        result.independent_evaluation?.evidence_source ||
        "Independent semantic and schema checks.",
    },
    {
      agent_id: "banking_sql_generation_agent",
      name: "Banking SQL Generation Agent",
      role: "Generate a bounded read-only query after metadata passes.",
      status: generationStatus,
      summary:
        result.sql_generation?.reason ||
        (generationStatus === "GENERATED"
          ? "Generated SQL from a supported banking query template."
          : "Waiting for metadata assurance to pass."),
    },
    {
      agent_id: "banking_sql_assurance_agent",
      name: "SQL Assurance Agent",
      role: "Check generated SQL against the approved safe template.",
      status: sqlAssuranceStatus,
      summary:
        result.sql_assurance?.note ||
        "SQL template checks run only after metadata passes.",
    },
    {
      agent_id: "independent_sql_supervisor",
      name: "Independent SQL Supervisor",
      role: "Independently gate SQL execution.",
      status: supervisorStatus,
      summary:
        result.sql_supervisor?.note ||
        "Execution is allowed only after independent SQL checks pass.",
    },
    {
      agent_id: "banking_result_validation_agent",
      name: "Banking Result Validation Agent",
      role: "Validate query result shape, values, and row limits.",
      status: resultStatus,
      summary:
        executionStatus === "SUCCEEDED"
          ? "Validated query output."
          : executionStatus === "ERROR"
            ? result.sql_execution?.error || "Query execution failed."
            : "Waiting for approved SQL execution.",
    },
  ];
}
