
import json
import traceback

from app.services.functional_assurance_service import (
    FunctionalAssuranceService,
)


def main():

    print("====================================", flush=True)
    print("HEAAP PHASE 13 - STEP 8", flush=True)
    print("FUNCTIONAL ASSURANCE TESTING", flush=True)
    print("====================================", flush=True)

    agent_id = "metadata_agent_001"

    try:
        print("\n1. Initializing assurance service...", flush=True)

        service = FunctionalAssuranceService()

        print("2. Starting functional tests...", flush=True)

        summary = service.run_assurance(agent_id)

        print("\n3. Functional tests completed!", flush=True)

        print("\nASSURANCE SUMMARY")
        print("------------------------------------")
        print(json.dumps(summary, indent=4), flush=True)

        report_id = summary["report_id"]

        print("\n4. Retrieving saved report...", flush=True)

        saved_report = service.get_report(
            agent_id,
            report_id,
        )

        print("\nCOMPLETE SAVED REPORT")
        print("------------------------------------")
        print(json.dumps(saved_report, indent=4), flush=True)

        print("\n5. Retrieving report history...", flush=True)

        history = service.list_reports(agent_id)

        print("\nREPORT HISTORY")
        print("------------------------------------")
        print("Total Reports:", len(history))

        for report in history[:5]:
            print(
                "Report ID:", report["report_id"],
                "| Status:", report["status"],
                "| Created:", report["created_at"],
            )

        print("\nPHASE 13 STEP 8 EXECUTION COMPLETED")

    except Exception as exc:

        print("\nERROR OCCURRED:", str(exc), flush=True)
        traceback.print_exc()


if __name__ == "__main__":
    main()
