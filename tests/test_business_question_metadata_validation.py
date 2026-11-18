import pytest

from app.services import live_metadata_validator
from app.services.supervisor_metadata_selector import select_metadata
from app.api.routes import business_question_routes


def test_curated_loan_question_selects_only_required_metadata():
    question = "Which customers have overdue loan installments?"
    retrieval = {
        "relevant_metadata": [
            {
                "table_name": "gold_loan_portfolio_summary",
                "score": 29,
                "columns": [
                    {
                        "column_name": "overdue_installments",
                        "matched_terms": ["overdue", "installment"],
                    },
                    {
                        "column_name": "loan_type",
                        "matched_terms": ["loan"],
                    },
                ],
            }
        ]
    }

    selection = select_metadata(question, retrieval=retrieval)

    assert selection["primary_table"] == "gold_loan_portfolio_summary"
    assert selection["selection_source"] == "curated_reference"
    assert selection["reference_rule_id"] == "LOAN_OVERDUE_CUSTOMERS"
    assert set(selection["selected_columns"]) == {
        "customer_id",
        "loan_id",
        "overdue_installments",
    }
    assert selection["expected_filter"] == "overdue_installments > 0"


def test_curated_kyc_question_includes_overdue_flag_and_filter():
    selection = select_metadata(
        "Which customers have overdue KYC reviews?",
        retrieval={"relevant_metadata": []},
    )

    assert selection["primary_table"] == "gold_kyc_compliance"
    assert selection["selected_columns"] == [
        "customer_id",
        "review_due_date",
        "review_overdue",
    ]
    assert selection["expected_filter"] == "review_overdue = TRUE"


def test_live_validation_rejects_missing_required_filter(monkeypatch):
    question = "Which customers have overdue loan installments?"
    selection = {
        "primary_table": "gold_loan_portfolio_summary",
        "selected_columns": [
            "customer_id",
            "loan_id",
            "overdue_installments",
        ],
    }
    columns = [
        {"column_name": "customer_id", "data_type": "STRING"},
        {"column_name": "loan_id", "data_type": "STRING"},
        {"column_name": "overdue_installments", "data_type": "LONG"},
    ]
    monkeypatch.setattr(
        live_metadata_validator,
        "list_tables",
        lambda: [{"table_name": "gold_loan_portfolio_summary"}],
    )
    monkeypatch.setattr(
        live_metadata_validator,
        "get_columns",
        lambda table: columns,
    )

    result = live_metadata_validator.validate_with_live_schema(
        question,
        selection,
    )

    assert result["validation_status"] == "FAIL"
    assert result["checks"]["table_correct"] == "PASS"
    assert result["checks"]["required_columns"] == "PASS"
    assert result["checks"]["live_schema"] == "PASS"
    assert result["checks"]["filter_requirement"] == "FAIL"
    assert result["expected_filter"] == "overdue_installments > 0"
    assert result["sql_execution_allowed"] is False


def test_complete_supported_metadata_passes_reference_and_schema_checks(monkeypatch):
    question = "Which customers have overdue loan installments?"
    selection = select_metadata(question, retrieval={"relevant_metadata": []})
    monkeypatch.setattr(
        live_metadata_validator,
        "list_tables",
        lambda: [{"table_name": "gold_loan_portfolio_summary"}],
    )
    monkeypatch.setattr(
        live_metadata_validator,
        "get_columns",
        lambda table: [
            {"column_name": "customer_id", "data_type": "STRING"},
            {"column_name": "loan_id", "data_type": "STRING"},
            {"column_name": "overdue_installments", "data_type": "LONG"},
        ],
    )

    result = live_metadata_validator.validate_with_live_schema(
        question,
        selection,
    )

    assert result["validation_status"] == "PASS"
    assert result["checks"]["filter_requirement"] == "PASS"
    assert result["checks"]["filter_application"] == "NOT_TESTED"
    assert result["checks"]["relationship_metadata"] == "NOT_REQUIRED"


def test_schema_bound_independent_evaluation_checks_measure_type(monkeypatch):
    from app.services import metadata_evaluation_integration

    selection = {
        "primary_table": "gold_account_balance_trends",
        "selected_columns": ["snapshot_date", "closing_balance_inr"],
    }
    validation = {
        "expected_table": "gold_account_balance_trends",
        "expected_columns": ["snapshot_date", "closing_balance_inr"],
        "reference_authority": "schema_bound_analytical_query_template",
        "schema_analytical_intent": {
            "query_type": "average_by_dimension",
            "dimension": "snapshot_date",
            "measure": "closing_balance_inr",
            "required_columns": ["snapshot_date", "closing_balance_inr"],
        },
    }
    monkeypatch.setattr(
        metadata_evaluation_integration,
        "get_columns",
        lambda table: [
            {"column_name": "snapshot_date", "data_type": "DATE"},
            {"column_name": "closing_balance_inr", "data_type": "STRING"},
        ],
    )

    result = metadata_evaluation_integration.run_independent_evaluation(
        selection,
        validation,
    )

    assert result["validation_status"] == "FAIL"
    assert result["checks"]["supported_dimension_type"] == "PASS"
    assert result["checks"]["numeric_measure_type"] == "FAIL"


def test_schema_valid_query_without_reference_stays_in_review(monkeypatch):
    question = "Show customers with an unusual relationship"
    selection = {
        "primary_table": "gold_customer_360",
        "selected_columns": ["customer_id"],
    }
    monkeypatch.setattr(
        live_metadata_validator,
        "list_tables",
        lambda: [{"table_name": "gold_customer_360"}],
    )
    monkeypatch.setattr(
        live_metadata_validator,
        "get_columns",
        lambda table: [{"column_name": "customer_id", "data_type": "STRING"}],
    )

    result = live_metadata_validator.validate_with_live_schema(
        question,
        selection,
    )

    assert result["validation_status"] == "REVIEW"
    assert result["checks"]["reference_definition"] == "UNAVAILABLE"
    assert result["checks"]["selected_columns_exist"] == "PASS"
    assert result["sql_execution_allowed"] is False


def test_unavailable_live_schema_is_an_error_not_a_pass(monkeypatch):
    question = "Which customers have overdue loan installments?"
    selection = select_metadata(question, retrieval={"relevant_metadata": []})

    def unavailable():
        raise RuntimeError("Unity Catalog unavailable")

    monkeypatch.setattr(live_metadata_validator, "list_tables", unavailable)

    result = live_metadata_validator.validate_with_live_schema(
        question,
        selection,
    )

    assert result["validation_status"] == "ERROR"
    assert result["checks"]["live_schema_query"] == "ERROR"
    assert result["sql_execution_allowed"] is False


def test_unfiltered_curated_question_can_pass_live_metadata_checks(monkeypatch):
    question = "Show loan repayment rate by loan type"
    selection = {
        "primary_table": "gold_loan_portfolio_summary",
        "selected_columns": ["loan_type", "repayment_rate_pct"],
    }
    monkeypatch.setattr(
        live_metadata_validator,
        "list_tables",
        lambda: [{"table_name": "gold_loan_portfolio_summary"}],
    )
    monkeypatch.setattr(
        live_metadata_validator,
        "get_columns",
        lambda table: [
            {"column_name": "loan_type", "data_type": "STRING"},
            {"column_name": "repayment_rate_pct", "data_type": "DOUBLE"},
        ],
    )

    result = live_metadata_validator.validate_with_live_schema(
        question,
        selection,
    )

    assert result["validation_status"] == "PASS"
    assert result["checks"]["live_schema_query"] == "PASS"
    assert result["sql_execution_allowed"] is False


def test_business_question_response_includes_selection_and_validation(monkeypatch):
    question = "Which customers have overdue loan installments?"
    retrieval = {
        "status": "MATCHED",
        "total_candidates": 1,
        "relevant_metadata": [{"table_name": "gold_loan_portfolio_summary"}],
    }
    selection = {
        "primary_table": "gold_loan_portfolio_summary",
        "selected_columns": ["customer_id", "loan_id", "overdue_installments"],
        "expected_filter": "overdue_installments > 0",
    }
    validation = {
        "validation_status": "REVIEW",
        "checks": {"filter_validation": "NOT_TESTED"},
        "sql_execution_allowed": False,
    }
    monkeypatch.setattr(
        business_question_routes,
        "retrieve_metadata",
        lambda value: retrieval,
    )
    monkeypatch.setattr(
        business_question_routes,
        "validate_candidate",
        lambda candidate: candidate,
    )
    monkeypatch.setattr(
        business_question_routes,
        "select_metadata",
        lambda value, retrieval: selection,
    )
    monkeypatch.setattr(
        business_question_routes,
        "validate_with_live_schema",
        lambda value, selected: validation,
    )

    result = business_question_routes.evaluate(question)

    assert result["selection"] == selection
    assert result["validation"] == validation
    assert result["assurance_status"] == "REVIEW"
    assert result["sql_execution_allowed"] is False


def test_gold_catalog_returns_live_gold_tables_and_column_descriptions(monkeypatch):
    monkeypatch.setattr(
        business_question_routes,
        "list_tables",
        lambda: [
            {"table_name": "gold_customer_360", "table_type": "MANAGED"},
            {"table_name": "silver_customer", "table_type": "MANAGED"},
        ],
    )
    monkeypatch.setattr(
        business_question_routes,
        "get_columns",
        lambda table: [
            {
                "column_name": "customer_id",
                "data_type": "STRING",
                "comment": "Unique customer identifier",
            }
        ],
    )

    result = business_question_routes.gold_catalog()

    assert result["source"] == "Databricks Unity Catalog"
    assert [table["table_name"] for table in result["tables"]] == [
        "gold_customer_360"
    ]
    assert result["tables"][0]["columns"][0]["comment"] == (
        "Unique customer identifier"
    )


def test_gold_catalog_reports_databricks_lookup_errors(monkeypatch):
    from fastapi import HTTPException

    def unavailable():
        raise RuntimeError("Unity Catalog unavailable")

    monkeypatch.setattr(business_question_routes, "list_tables", unavailable)

    with pytest.raises(HTTPException) as exc_info:
        business_question_routes.gold_catalog()
    assert exc_info.value.status_code == 500
    assert "Unity Catalog unavailable" in exc_info.value.detail


def test_schema_count_question_generates_only_bounded_grouped_select(monkeypatch):
    from app.services import heaap_sql_assurance

    question = (
        "How many records are there by snapshot_date "
        "in gold_account_balance_trends?"
    )
    monkeypatch.setenv("DATABRICKS_CATALOG", "agent_testing")
    monkeypatch.setenv("DATABRICKS_SCHEMA", "gold")
    monkeypatch.setattr(
        heaap_sql_assurance,
        "get_columns",
        lambda table: [
            {"column_name": "snapshot_date", "data_type": "DATE"}
        ],
    )

    intent = heaap_sql_assurance.parse_schema_count_question(question)
    generated = heaap_sql_assurance.generate_sql(
        question,
        {
            "primary_table": "gold_account_balance_trends",
            "selected_columns": ["snapshot_date"],
        },
    )

    assert intent == {
        "query_type": "count_by_dimension",
        "dimension": "snapshot_date",
        "table": "gold_account_balance_trends",
    }
    assert generated["status"] == "GENERATED"
    assert "COUNT(*) AS `record_count`" in generated["sql"]
    assert "GROUP BY `snapshot_date`" in generated["sql"]
    assert generated["sql"].endswith("LIMIT 100")
    assert heaap_sql_assurance.validate_generated_sql(generated)[
        "status"
    ] == "PASS"
    assert (
        heaap_sql_assurance.parse_schema_count_question(
            "Show customers with an unusual relationship"
        )
        is None
    )


def test_explorer_average_question_is_structured_without_claiming_approval(
    monkeypatch,
    tmp_path,
):
    from app.services import heaap_pipeline, heaap_sql_assurance

    question = (
        "What is the average closing_balance_inr by snapshot_date "
        "in gold_account_balance_trends?"
    )
    intent = heaap_sql_assurance.parse_schema_explorer_question(question)
    assert intent == {
        "query_type": "average_by_dimension",
        "table": "gold_account_balance_trends",
        "required_columns": ["snapshot_date", "closing_balance_inr"],
        "dimension": "snapshot_date",
        "measure": "closing_balance_inr",
    }

    monkeypatch.setattr(heaap_pipeline, "REPORT_DIR", tmp_path)
    monkeypatch.setattr(
        heaap_pipeline,
        "select_metadata",
        lambda value: (_ for _ in ()).throw(
            AssertionError("Explicit Explorer questions should not be re-retrieved")
        ),
    )
    monkeypatch.setattr(
        heaap_pipeline,
        "validate_with_live_schema",
        lambda value, selection: {"validation_status": "REVIEW", "checks": {}},
    )
    monkeypatch.setattr(
        heaap_pipeline,
        "run_independent_evaluation",
        lambda selection, validation: {"validation_status": "REVIEW"},
    )

    result = heaap_pipeline.run_pipeline(question)

    assert result["selection"]["primary_table"] == "gold_account_balance_trends"
    assert result["selection"]["selected_columns"] == [
        "snapshot_date",
        "closing_balance_inr",
    ]
    assert result["metadata_assurance_status"] == "REVIEW"
    assert result["sql_generation_status"] == "NOT_STARTED"


def test_bulk_pipeline_returns_each_result_and_reports_individual_errors(
    monkeypatch,
):
    from app.api.routes import heaap_pipeline_routes

    def run(question):
        if question == "bad":
            raise RuntimeError("pipeline unavailable")
        return {
            "question": question,
            "metadata_assurance_status": "PASS",
            "sql_execution_status": "SUCCEEDED",
        }

    monkeypatch.setattr(heaap_pipeline_routes, "run_pipeline", run)
    result = heaap_pipeline_routes.validate_pipeline_bulk(
        heaap_pipeline_routes.BulkPipelineRequest(
            questions=["good", "bad"]
        )
    )

    assert result["total"] == 2
    assert result["summary"] == {
        "PASS": 1,
        "REVIEW": 0,
        "FAIL": 0,
        "ERROR": 1,
        "EXECUTED": 1,
    }
    assert result["results"][1]["error"] == (
        "RuntimeError: pipeline unavailable"
    )


def test_schema_count_pipeline_returns_rows_only_after_independent_pass(
    monkeypatch,
    tmp_path,
):
    from app.services import heaap_pipeline, heaap_sql_assurance

    question = (
        "How many records are there by snapshot_date "
        "in gold_account_balance_trends?"
    )
    monkeypatch.setattr(heaap_pipeline, "REPORT_DIR", tmp_path)
    monkeypatch.setenv("DATABRICKS_CATALOG", "agent_testing")
    monkeypatch.setenv("DATABRICKS_SCHEMA", "gold")
    monkeypatch.setattr(
        heaap_pipeline,
        "select_metadata",
        lambda value: {
            "primary_table": "gold_account_balance_trends",
            "selected_columns": ["snapshot_date"],
        },
    )
    monkeypatch.setattr(
        heaap_pipeline,
        "validate_with_live_schema",
        lambda value, selection: {
            "validation_status": "PASS",
            "checks": {
                "table_exists": "PASS",
                "selected_columns_exist": "PASS",
                "live_schema": "PASS",
                "live_schema_query": "PASS",
            },
            "evidence": [],
        },
    )
    monkeypatch.setattr(
        heaap_pipeline,
        "run_independent_evaluation",
        lambda selection, validation: {
            "validation_status": "PASS",
            "checks": {},
        },
    )
    monkeypatch.setattr(
        heaap_sql_assurance,
        "get_columns",
        lambda table: [
            {"column_name": "snapshot_date", "data_type": "DATE"}
        ],
    )
    monkeypatch.setattr(
        heaap_pipeline,
        "supervise_sql",
        lambda question, sql, selection: {
            "status": "PASS",
            "execution_allowed": True,
            "checks": {},
        },
    )
    monkeypatch.setattr(
        heaap_pipeline,
        "execute_query",
        lambda sql: [
            {"snapshot_date": "2026-01-01", "record_count": 42}
        ],
    )

    result = heaap_pipeline.run_pipeline(question)

    assert result["metadata_assurance_status"] == "PASS"
    assert result["sql_execution_allowed"] is True
    assert result["sql_execution_status"] == "SUCCEEDED"
    assert result["sql_execution"]["rows"] == [
        {"snapshot_date": "2026-01-01", "record_count": 42}
    ]
    agent_statuses = {
        agent["agent_id"]: agent["status"]
        for agent in result["agent_runs"]
    }
    assert agent_statuses == {
        "banking_assurance_orchestrator": "PASS",
        "banking_question_agent": "PASS",
        "gold_metadata_assurance_agent": "PASS",
        "banking_semantics_agent": "PASS",
        "banking_sql_generation_agent": "GENERATED",
        "banking_sql_assurance_agent": "PASS",
        "independent_sql_supervisor": "PASS",
        "banking_result_validation_agent": "PASS",
    }


def test_pipeline_only_generates_sql_after_metadata_pass(monkeypatch, tmp_path):
    from app.services import heaap_pipeline

    monkeypatch.setattr(heaap_pipeline, "REPORT_DIR", tmp_path)
    monkeypatch.setattr(heaap_pipeline, "select_metadata", lambda question: {})
    monkeypatch.setattr(
        heaap_pipeline,
        "validate_with_live_schema",
        lambda question, selection: {"validation_status": "REVIEW"},
    )
    monkeypatch.setattr(
        heaap_pipeline,
        "run_independent_evaluation",
        lambda selection, validation: {"validation_status": "REVIEW"},
    )
    monkeypatch.setattr(
        heaap_pipeline,
        "generate_sql",
        lambda question, selection: (_ for _ in ()).throw(
            AssertionError("SQL must not be generated for REVIEW")
        ),
    )

    result = heaap_pipeline.run_pipeline("Unsupported business question")

    assert result["metadata_assurance_status"] == "REVIEW"
    assert result["metadata_decision"] == "HUMAN_REVIEW"
    assert result["sql_generation_status"] == "NOT_STARTED"
    agent_statuses = {
        agent["agent_id"]: agent["status"]
        for agent in result["agent_runs"]
    }
    assert agent_statuses["banking_sql_generation_agent"] == "BLOCKED"
    assert agent_statuses["banking_result_validation_agent"] == "BLOCKED"


def test_pipeline_advances_to_sql_only_when_both_metadata_checks_pass(
    monkeypatch,
    tmp_path,
):
    from app.services import heaap_pipeline

    generated = []
    monkeypatch.setattr(heaap_pipeline, "REPORT_DIR", tmp_path)
    monkeypatch.setattr(heaap_pipeline, "select_metadata", lambda question: {})
    monkeypatch.setattr(
        heaap_pipeline,
        "validate_with_live_schema",
        lambda question, selection: {"validation_status": "PASS"},
    )
    monkeypatch.setattr(
        heaap_pipeline,
        "run_independent_evaluation",
        lambda selection, validation: {"validation_status": "PASS"},
    )

    def generate(question, selection):
        generated.append(question)
        return {"status": "GENERATED", "sql": "SELECT 1"}

    monkeypatch.setattr(heaap_pipeline, "generate_sql", generate)
    monkeypatch.setattr(
        heaap_pipeline,
        "validate_generated_sql",
        lambda generation: {"status": "PASS", "checks": {}},
    )
    monkeypatch.setattr(
        heaap_pipeline,
        "supervise_sql",
        lambda question, sql, selection: {"status": "PASS", "checks": {}},
    )

    result = heaap_pipeline.run_pipeline("Approved question")

    assert generated == ["Approved question"]
    assert result["metadata_assurance_status"] == "PASS"
    assert result["metadata_decision"] == "PROCEED_TO_SQL_GENERATION"
    assert result["sql_generation_status"] == "GENERATED"
    assert result["sql_execution_allowed"] is False


def test_independent_evaluation_uses_separately_fetched_schema(monkeypatch):
    from app.services import metadata_evaluation_integration

    selection = {
        "primary_table": "gold_loan_portfolio_summary",
        "selected_columns": [
            "customer_id",
            "loan_id",
            "overdue_installments",
        ],
        "expected_filter": "overdue_installments > 0",
    }
    validation = {
        "expected_table": "gold_loan_portfolio_summary",
        "expected_columns": [
            "customer_id",
            "loan_id",
            "overdue_installments",
        ],
        "expected_filter": "overdue_installments > 0",
        "expected_relationships": [],
        "join_required": False,
    }
    monkeypatch.setattr(
        metadata_evaluation_integration,
        "get_columns",
        lambda table: [
            {"column_name": "customer_id"},
            {"column_name": "loan_id"},
            {"column_name": "overdue_installments"},
        ],
    )

    result = metadata_evaluation_integration.run_independent_evaluation(
        selection,
        validation,
    )

    assert result["validation_status"] == "PASS"
    assert result["independent_schema_fetch"] is True
    assert result["checks"]["filter_requirement"] == "PASS"


@pytest.mark.parametrize(
    ("question", "query_type"),
    [
        (
            "How many records are in gold_account_balance_trends?",
            "count_all",
        ),
        (
            "How many records are there by snapshot_date "
            "in gold_account_balance_trends?",
            "count_by_dimension",
        ),
        (
            "What is the average closing_balance_inr "
            "in gold_account_balance_trends?",
            "average",
        ),
        (
            "What is the average closing_balance_inr by snapshot_date "
            "in gold_account_balance_trends?",
            "average_by_dimension",
        ),
        (
            "What is the minimum and maximum closing_balance_inr "
            "in gold_account_balance_trends?",
            "min_max",
        ),
    ],
)
def test_schema_analytics_templates_pass_independent_supervision(
    question,
    query_type,
    monkeypatch,
):
    from app.services import (
        heaap_sql_assurance,
        independent_sql_supervisor,
    )

    monkeypatch.setenv("DATABRICKS_CATALOG", "agent_testing")
    monkeypatch.setenv("DATABRICKS_SCHEMA", "gold")
    live_columns = [
        {"column_name": "snapshot_date", "data_type": "DATE"},
        {"column_name": "closing_balance_inr", "data_type": "DECIMAL(18,2)"},
    ]
    monkeypatch.setattr(
        heaap_sql_assurance,
        "get_columns",
        lambda table: live_columns,
    )
    monkeypatch.setattr(
        independent_sql_supervisor,
        "list_tables",
        lambda: [{"table_name": "gold_account_balance_trends"}],
    )
    monkeypatch.setattr(
        independent_sql_supervisor,
        "get_columns",
        lambda table: live_columns,
    )

    intent = heaap_sql_assurance.parse_schema_explorer_question(question)
    assert intent["query_type"] == query_type
    generation = heaap_sql_assurance.generate_sql(
        question,
        {
            "primary_table": intent["table"],
            "selected_columns": intent["required_columns"],
        },
    )

    assert generation["status"] == "GENERATED"
    assert heaap_sql_assurance.validate_generated_sql(generation)[
        "status"
    ] == "PASS"
    supervision = independent_sql_supervisor.supervise_sql(
        question,
        generation["sql"],
        {
            "primary_table": intent["table"],
            "selected_columns": intent["required_columns"],
        },
    )
    assert supervision["status"] == "PASS"
    assert supervision["execution_allowed"] is True


def test_schema_analytics_rejects_non_numeric_measures(monkeypatch):
    from app.services import heaap_sql_assurance

    question = (
        "What is the average closing_balance_inr "
        "in gold_account_balance_trends?"
    )
    monkeypatch.setattr(
        heaap_sql_assurance,
        "get_columns",
        lambda table: [
            {"column_name": "closing_balance_inr", "data_type": "STRING"}
        ],
    )

    generation = heaap_sql_assurance.generate_sql(
        question,
        {
            "primary_table": "gold_account_balance_trends",
            "selected_columns": ["closing_balance_inr"],
        },
    )

    assert generation["status"] == "FAIL"
    assert "numeric type" in generation["reason"]


def test_query_result_validation_checks_shape_values_and_preview_limit():
    from app.services.heaap_sql_assurance import validate_query_results

    empty_aggregate = validate_query_results(
        "count_all",
        {"required_columns": []},
        [],
    )
    assert empty_aggregate["validation_status"] == "FAIL"
    assert empty_aggregate["checks"]["aggregate_row_shape"] == "FAIL"

    malformed = validate_query_results(
        "count_all",
        {"required_columns": []},
        [{"record_count": "not-a-count", "unexpected": 1}],
    )
    assert malformed["validation_status"] == "FAIL"
    assert malformed["checks"]["result_columns"] == "FAIL"

    invalid_value = validate_query_results(
        "count_all",
        {"required_columns": []},
        [{"record_count": "not-a-count"}],
    )
    assert invalid_value["validation_status"] == "FAIL"
    assert invalid_value["checks"]["aggregate_values"] == "FAIL"

    intent = {
        "query_type": "min_max",
        "table": "gold_account_balance_trends",
        "required_columns": ["closing_balance_inr"],
        "measure": "closing_balance_inr",
    }

    invalid = validate_query_results(
        "min_max",
        intent,
        [
            {
                "minimum_closing_balance_inr": 20,
                "maximum_closing_balance_inr": 10,
            }
        ],
    )
    assert invalid["validation_status"] == "FAIL"

    valid = validate_query_results(
        "count_by_dimension",
        {
            "dimension": "snapshot_date",
            "required_columns": ["snapshot_date"],
        },
        [
            {"snapshot_date": f"2026-01-{index:02d}", "record_count": index}
            for index in range(1, 101)
        ],
    )
    assert valid["validation_status"] == "REVIEW"
    assert valid["preview_truncated"] is True


def test_pipeline_executes_average_only_after_assurance_and_validates_result(
    monkeypatch,
    tmp_path,
):
    from app.services import heaap_pipeline, heaap_sql_assurance

    question = (
        "What is the average closing_balance_inr "
        "in gold_account_balance_trends?"
    )
    monkeypatch.setattr(heaap_pipeline, "REPORT_DIR", tmp_path)
    monkeypatch.setenv("DATABRICKS_CATALOG", "agent_testing")
    monkeypatch.setenv("DATABRICKS_SCHEMA", "gold")
    monkeypatch.setattr(
        heaap_pipeline,
        "validate_with_live_schema",
        lambda value, selection: {
            "validation_status": "PASS",
            "checks": {
                "table_exists": "PASS",
                "selected_columns_exist": "PASS",
                "live_schema": "PASS",
                "live_schema_query": "PASS",
            },
            "evidence": [],
        },
    )
    monkeypatch.setattr(
        heaap_pipeline,
        "run_independent_evaluation",
        lambda selection, validation: {"validation_status": "PASS"},
    )
    monkeypatch.setattr(
        heaap_sql_assurance,
        "get_columns",
        lambda table: [
            {"column_name": "closing_balance_inr", "data_type": "DOUBLE"}
        ],
    )
    monkeypatch.setattr(
        heaap_pipeline,
        "supervise_sql",
        lambda question, sql, selection: {
            "status": "PASS",
            "execution_allowed": True,
            "checks": {},
        },
    )
    monkeypatch.setattr(
        heaap_pipeline,
        "execute_query",
        lambda sql: [{"average_closing_balance_inr": 12.5}],
    )

    result = heaap_pipeline.run_pipeline(question)

    assert result["sql_execution_allowed"] is True
    assert result["sql_execution_status"] == "SUCCEEDED"
    assert result["result_validation_status"] == "PASS"
