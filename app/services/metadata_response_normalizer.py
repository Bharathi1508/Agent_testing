"""
HEAAP Phase 22.14
Metadata Agent Response Normalizer.

Converts explicitly supported response contracts
into canonical evaluation results.

Unknown response formats raise an error.
"""


class MetadataResponseNormalizer:

    @staticmethod
    def normalize(test_case, response):

        if not isinstance(test_case, dict):
            raise ValueError("Invalid test case")

        if not isinstance(response, dict):
            raise ValueError("Invalid agent response")

        test_type = test_case.get("test_type")

        # Support a flat response or a nested result object.
        result = response.get("result", response)

        if not isinstance(result, dict):
            raise ValueError(
                "Agent result must be a JSON object"
            )

        if test_type == "exact_boolean":

            if "exists" in result:
                value = result["exists"]
            elif "column_exists" in result:
                value = result["column_exists"]
            else:
                raise ValueError(
                    "Column existence result is missing"
                )

            if type(value) is not bool:
                raise ValueError(
                    "Column existence must be boolean"
                )

            return {"exists": value}

        if test_type == "exact_type":

            if "data_type" in result:
                value = result["data_type"]
            elif "column_type" in result:
                value = result["column_type"]
            else:
                raise ValueError(
                    "Column data type result is missing"
                )

            if not isinstance(value, str):
                raise ValueError(
                    "Column data type must be a string"
                )

            if not value.strip():
                raise ValueError(
                    "Column data type cannot be empty"
                )

            return {
                "data_type": value.strip().lower()
            }

        raise ValueError(
            f"Unsupported test type: {test_type}"
        )
