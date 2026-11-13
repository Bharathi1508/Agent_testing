
"""
HEAAP - Agent Assurance Test Cases

Defines test cases for registered agents.
"""

TEST_CASES = {

    # Metadata Agent
    "metadata_agent_001": [
        {
            "test_id": "META_001",
            "name": "List Gold Layer Tables",
            "capability": "list_tables",
            "input": {
                "action": "list_tables"
            },
            "required_keys": [
                "status",
                "result"
            ],
            "expected_status": "success",
            "max_latency_ms": 30000
        }
    ],

    # SQL Agent
    "sql_agent": [
        {
            "test_id": "SQL_001",
            "name": "Reject Unsupported SQL Operation",
            "capability": "top_loans",
            "input": {
                "action": "invalid_action"
            },
            "required_keys": [
                "status",
                "result"
            ],
            "expected_status": "unsupported",
            "max_latency_ms": 30000
        }
    ]
}
