"""HEAAP Phase 19.8 - LangGraph supervisor."""

import json
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import StateGraph, START, END

from app.services.external_test_plan_validator import (
    validate_external_test_plan,
)

from app.services.external_test_plan_supervisor import (
    supervise_external_test_plan,
)


class SupervisorState(TypedDict, total=False):
    plan: dict[str, Any]
    review: dict[str, Any]
    validation: dict[str, Any]
    decision: dict[str, Any]
    workflow_trace: list[str]
    final_report: dict[str, Any]


def validate_plan_node(state: SupervisorState):
    plan = state["plan"]

    validation = validate_external_test_plan(plan)

    return {
        "validation": validation,
        "workflow_trace": (
            state.get("workflow_trace", [])
            + ["validate_test_plan"]
        ),
    }


def review_approval_node(state: SupervisorState):
    plan = state["plan"]
    review = state["review"]

    decision = supervise_external_test_plan(
        plan,
        review,
    )

    return {
        "decision": decision,
        "workflow_trace": (
            state.get("workflow_trace", [])
            + ["review_agent_approval"]
        ),
    }


def supervisor_decision_node(state: SupervisorState):
    decision = state["decision"]

    if state["validation"]["valid"] is not True:
        decision = {
            **decision,
            "decision": "blocked",
            "ready_for_separate_run_approval": False,
            "execution_authorized_by_supervisor": False,
        }

    return {
        "decision": decision,
        "workflow_trace": (
            state.get("workflow_trace", [])
            + ["supervisor_decision"]
        ),
    }


def generate_report_node(state: SupervisorState):
    decision = state["decision"]

    report = {
        "report_id": uuid.uuid4().hex,
        "phase": "19.8",
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "agent_id": state["plan"].get("agent_id"),
        "plan_id": state["plan"].get("plan_id"),
        "plan_validation": state["validation"],
        "supervisor_decision": decision,
        "workflow_trace": (
            state.get("workflow_trace", [])
            + ["generate_supervisor_report"]
        ),
        "governance": {
            "execution_authorized": False,
            "live_endpoint_invoked": False,
            "database_executed": False,
            "production_approved": False,
        },
    }

    return {
        "final_report": report,
        "workflow_trace": report["workflow_trace"],
    }


def build_supervisor_graph():
    graph = StateGraph(SupervisorState)

    graph.add_node(
        "validate_plan",
        validate_plan_node,
    )

    graph.add_node(
        "review_approval",
        review_approval_node,
    )

    graph.add_node(
        "supervisor_decision",
        supervisor_decision_node,
    )

    graph.add_node(
        "generate_report",
        generate_report_node,
    )

    graph.add_edge(START, "validate_plan")
    graph.add_edge("validate_plan", "review_approval")
    graph.add_edge("review_approval", "supervisor_decision")
    graph.add_edge("supervisor_decision", "generate_report")
    graph.add_edge("generate_report", END)

    return graph.compile()


def run_langgraph_supervisor(plan, review):
    if not isinstance(plan, dict):
        raise ValueError("Plan must be an object")

    if not isinstance(review, dict):
        raise ValueError("Review must be an object")

    graph = build_supervisor_graph()

    result = graph.invoke({
        "plan": plan,
        "review": review,
        "workflow_trace": [],
    })

    return result["final_report"]


def save_supervisor_report(report, output_dir=None):
    if output_dir is None:
        output_dir = Path(
            "reports/phase19_8_langgraph_supervisor"
        )

    output_dir = Path(output_dir)
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_file = output_dir / (
        report["report_id"] + ".json"
    )

    with report_file.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    return str(report_file)
