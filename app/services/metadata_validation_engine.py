from __future__ import annotations

from typing import Any
import re


# Curated starter rules. A business owner must approve these definitions
# before their results are treated as production semantic certification.
BUSINESS_GLOSSARY = [
    {
        "rule_id": "LOAN_OVERDUE_CUSTOMERS",
        "patterns": [
            r"\boverdue\b.*\bloan\b.*\binstallment",
            r"\bloan\b.*\boverdue\b.*\binstallment",
        ],
        "table": "gold_loan_portfolio_summary",
        "required_columns": [
            "customer_id",
            "loan_id",
            "overdue_installments",
        ],
        "filter": "overdue_installments > 0",
        "join_required": False,
        "relationships": [],
    },
    {
        "rule_id": "LOAN_REPAYMENT_BY_TYPE",
        "patterns": [
            r"\brepayment\b.*\bloan type\b",
        ],
        "table": "gold_loan_portfolio_summary",
        "required_columns": [
            "loan_type",
            "repayment_rate_pct",
        ],
        "filter": None,
        "join_required": False,
        "relationships": [],
    },
    {
        "rule_id": "ACCOUNT_BALANCE_BY_DATE",
        "patterns": [
            r"\bclosing\b.*\baccount\b.*\bbalance\b.*\bdate\b",
        ],
        "table": "gold_account_balance_trends",
        "required_columns": [
            "snapshot_date",
            "closing_balance_inr",
        ],
        "filter": None,
        "join_required": False,
        "relationships": [],
    },
    {
        "rule_id": "KYC_OVERDUE_REVIEWS",
        "patterns": [
            r"\boverdue\b.*\bkyc\b.*\breviews?\b",
            r"\bkyc\b.*\boverdue\b.*\breviews?\b",
        ],
        "table": "gold_kyc_compliance",
        "required_columns": [
            "customer_id",
            "review_due_date",
            "review_overdue",
        ],
        "filter": "review_overdue = TRUE",
        "join_required": False,
        "relationships": [],
    },
]

REFERENCE_RULES = BUSINESS_GLOSSARY
REFERENCE_AUTHORITY = "in_code_curated_rules_pending_business_owner_signoff"


def normalize_columns(raw: Any) -> set[str]:
    """Accept common metadata-service response shapes."""
    if isinstance(raw, dict):
        for key in ("columns", "data", "results"):
            if key in raw:
                return normalize_columns(raw[key])
        return set()

    if not isinstance(raw, list):
        return set()

    names = set()

    for item in raw:
        if isinstance(item, str):
            names.add(item.lower())
        elif isinstance(item, dict):
            name = item.get("column_name") or item.get("name")
            if isinstance(name, str):
                names.add(name.lower())

    return names


def match_reference(question: str):
    normalized = re.sub(r"\s+", " ", question.lower()).strip()

    matches = [
        rule
        for rule in BUSINESS_GLOSSARY
        if any(
            re.search(pattern, normalized)
            for pattern in rule["patterns"]
        )
    ]

    # Multiple matching definitions are ambiguous.
    if len(matches) != 1:
        return None

    return matches[0]


def validate_metadata(
    question: str,
    selection: dict,
    live_columns: Any = None,
) -> dict:
    """
    Validate a proposed metadata selection against independently
    curated reference rules and, when supplied, live schema data.

    No LLM judgment is treated as independent proof.
    """
    rule = match_reference(question)

    actual_table = selection.get("primary_table")
    actual_columns = {
        str(c).lower()
        for c in selection.get("selected_columns", [])
    }

    checks = {}
    evidence = []

    if rule is None:
        return {
            "question": question,
            "primary_table": actual_table,
            "expected_table": None,
            "expected_columns": [],
            "selected_columns": sorted(actual_columns),
            "missing_columns": [],
            "extra_columns": [],
            "expected_filter": None,
            "expected_relationships": [],
            "reference_authority": REFERENCE_AUTHORITY,
            "validation_status": "REVIEW",
            "checks": {
                "reference_definition": "UNAVAILABLE",
                "business_glossary": "UNAVAILABLE",
                "table_correct": "NOT_VERIFIED",
                "required_columns": "NOT_VERIFIED",
                "column_minimality": "NOT_VERIFIED",
                "live_schema": "NOT_VERIFIED",
                "relationship_metadata": "UNAVAILABLE",
                "filter_requirement": "NOT_TESTED",
                "filter_application": "NOT_TESTED",
                "result_validation": "NOT_TESTED",
            },
            "evidence": [
                "No unique trusted business rule matched this question."
            ],
            "sql_execution_allowed": False,
        }

    expected_table = rule["table"]
    expected_columns = set(rule["required_columns"])

    checks["reference_definition"] = "PASS"
    checks["business_glossary"] = "PASS"
    table_correct = (
        isinstance(actual_table, str)
        and actual_table.lower() == expected_table
    )

    missing_columns = sorted(expected_columns - actual_columns)
    extra_columns = sorted(actual_columns - expected_columns)

    checks["table_correct"] = (
        "PASS" if table_correct else "FAIL"
    )
    checks["required_columns"] = (
        "PASS" if not missing_columns else "FAIL"
    )

    # Extra columns are reported but do not automatically fail.
    checks["column_minimality"] = (
        "PASS" if not extra_columns else "REVIEW"
    )

    evidence.append(
        f"Reference rule: {rule['rule_id']}"
    )
    evidence.append(
        f"Expected table: {expected_table}"
    )
    evidence.append(
        f"Missing required columns: {missing_columns}"
    )
    evidence.append(
        f"Additional selected columns: {extra_columns}"
    )

    if live_columns is None:
        checks["live_schema"] = "NOT_VERIFIED"
    else:
        available = normalize_columns(live_columns)

        if not available:
            checks["live_schema"] = "NOT_VERIFIED"
            evidence.append(
                "Live schema response could not be interpreted."
            )
        else:
            missing_in_schema = sorted(
                expected_columns - available
            )
            checks["live_schema"] = (
                "PASS" if not missing_in_schema else "FAIL"
            )
            evidence.append(
                f"Required columns missing from live schema: "
                f"{missing_in_schema}"
            )

    expected_filter = rule["filter"]
    selected_filter = selection.get("expected_filter")
    if expected_filter:
        normalize_filter = lambda value: re.sub(
            r"\s+", "", str(value or "").lower()
        )
        checks["filter_requirement"] = (
            "PASS"
            if normalize_filter(selected_filter)
            == normalize_filter(expected_filter)
            else "FAIL"
        )
    else:
        checks["filter_requirement"] = "NOT_REQUIRED"
    checks["filter_application"] = "NOT_TESTED"

    expected_relationships = rule.get("relationships", [])
    if not rule.get("join_required"):
        checks["relationship_metadata"] = "NOT_REQUIRED"
    elif expected_relationships and selection.get("relationships") == expected_relationships:
        checks["relationship_metadata"] = "PASS"
    else:
        checks["relationship_metadata"] = "NOT_VERIFIED"

    checks["result_validation"] = "NOT_TESTED"

    failures = any(
        value == "FAIL"
        for value in checks.values()
    )

    if failures:
        status = "FAIL"
    elif (
        checks["live_schema"] != "PASS"
        or checks["column_minimality"] != "PASS"
        or checks["relationship_metadata"] == "NOT_VERIFIED"
    ):
        status = "REVIEW"
    else:
        status = "PASS"

    return {
        "question": question,
        "primary_table": actual_table,
        "expected_table": expected_table,
        "expected_columns": rule["required_columns"],
        "expected_relationships": expected_relationships,
        "join_required": rule.get("join_required", False),
        "selected_columns": sorted(actual_columns),
        "missing_columns": missing_columns,
        "extra_columns": extra_columns,
        "expected_filter": expected_filter,
        "reference_authority": REFERENCE_AUTHORITY,
        "checks": checks,
        "validation_status": status,
        "evidence": evidence,
        "sql_execution_allowed": False,
    }
