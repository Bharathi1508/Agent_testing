import json
from pathlib import Path
from datetime import datetime, timezone

AGENT_ID = "metadata_agent_001"
REPORT_DIR = Path("reports/phase23_3")

PHASES = {
    "23.3.6": "metadata_execution_*.json",
    "23.3.7": "check_column_assurance_*.json",
    "23.3.8": "metadata_negative_assurance_*.json",
}

def latest_report(pattern):
    files = sorted(
        REPORT_DIR.glob(pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    return files[0] if files else None

def load_phase(phase, pattern):
    path = latest_report(pattern)

    if path is None:
        return {
            "phase": phase,
            "status": "missing",
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "inconclusive": 0,
            "report_file": None,
            "issues": [],
        }

    data = json.loads(path.read_text(encoding="utf-8"))

    if data.get("agent_id") != AGENT_ID:
        raise ValueError(
            f"Agent mismatch in report: {path}"
        )

    total = data.get(
        "total_tests",
        data.get("generated_tests", 0)
    )

    passed = data.get(
        "passed",
        data.get("passed_tests", 0)
    )

    failed = data.get(
        "failed",
        data.get("failed_tests", 0)
    )

    errors = data.get("errors", 0)

    inconclusive = data.get(
        "inconclusive",
        data.get("inconclusive_tests", 0)
    )

    issues = [
        result
        for result in data.get("results", [])
        if result.get("status") not in ("passed", "pass")
    ]

    accounted = passed + failed + errors + inconclusive

    if accounted != total:
        raise ValueError(
            f"Count mismatch in {path}: "
            f"total={total}, accounted={accounted}"
        )

    if total == 0:
        status = "incomplete"
    elif failed or errors:
        status = "failed"
    elif inconclusive:
        status = "incomplete"
    else:
        status = "passed"

    return {
        "phase": phase,
        "status": status,
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "inconclusive": inconclusive,
        "report_file": str(path),
        "issues": issues,
    }

def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    phases = [
        load_phase(phase, pattern)
        for phase, pattern in PHASES.items()
    ]

    totals = {
        key: sum(phase[key] for phase in phases)
        for key in (
            "total", "passed", "failed",
            "errors", "inconclusive"
        )
    }

    pass_rate = (
        round(100 * totals["passed"] / totals["total"], 2)
        if totals["total"]
        else 0
    )

    missing = [
        phase["phase"]
        for phase in phases
        if phase["status"] == "missing"
    ]

    if missing:
        recommendation = "INCOMPLETE_EVIDENCE"
    elif totals["failed"] or totals["errors"]:
        recommendation = "REVIEW_REQUIRED"
    elif totals["inconclusive"]:
        recommendation = "FURTHER_VALIDATION_REQUIRED"
    elif totals["total"] > 0:
        recommendation = "ELIGIBLE_FOR_HUMAN_REVIEW"
    else:
        recommendation = "INCOMPLETE_EVIDENCE"

    report = {
        "platform": "HEAAP",
        "phase": "23.3.9",
        "agent_id": AGENT_ID,
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "total_test_assertions": totals["total"],
        "passed": totals["passed"],
        "failed": totals["failed"],
        "errors": totals["errors"],
        "inconclusive": totals["inconclusive"],
        "pass_rate_pct": pass_rate,
        "missing_phases": missing,
        "recommendation": recommendation,
        "phases": phases,
        "note": (
            "Counts represent assertions from individual "
            "phase reports. Some checks may overlap. "
            "This report does not grant governance approval."
        ),
    }

    path = REPORT_DIR / (
        "consolidated_assurance_"
        + datetime.now(timezone.utc).strftime(
            "%Y%m%d_%H%M%S_%f"
        )
        + ".json"
    )

    with path.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n=== HEAAP CONSOLIDATED ASSURANCE ===")
    print("Agent:", AGENT_ID)
    print("Total assertions:", totals["total"])
    print("Passed:", totals["passed"])
    print("Failed:", totals["failed"])
    print("Errors:", totals["errors"])
    print("Inconclusive:", totals["inconclusive"])
    print("Pass rate:", str(pass_rate) + "%")
    print("Missing phases:", missing)
    print("Recommendation:", recommendation)
    print("Report:", path)

if __name__ == "__main__":
    main()
