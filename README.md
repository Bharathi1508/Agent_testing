# HEAAP

HEAAP (Hybrid Enterprise Agent Assurance Platform) is a local POC for testing
banking business questions against Databricks Gold-table metadata. It checks
metadata and business semantics before generating bounded SQL, independently
assures the SQL, and validates results when execution is approved.

## Banking question assurance flow

1. Interpret the business question and select a Gold table and columns.
2. Validate the selection against live Unity Catalog metadata and available
   business references.
3. Return a `PASS`, `REVIEW`, or `FAIL` decision.
4. On `PASS`, generate SQL only for supported question templates.
5. Check the SQL template and independently gate execution.
6. Validate query results when execution is allowed.

The local specialist roles are coordinated by the assurance pipeline; they are
not separate hosted model services. Unsupported or ambiguous questions remain
in review. SQL execution is read-only, template constrained, and gated; a
generated query does not by itself mean it was executed.

Current schema-derived query templates include row counts, grouped counts,
averages, grouped averages, and minimum/maximum aggregates. A curated overdue
loan question is also supported for SQL generation. Other banking questions
may require an approved business reference and a tested SQL template.

## Project layout

- `app/` — FastAPI backend, metadata and SQL assurance services.
- `frontend/` — Next.js business-question testbench and pipeline report.
- `tests/` — focused metadata, SQL, and result-validation tests.
- `start_heaap.ps1` — Windows helper that checks and starts the local app.

## Local setup (Windows)

1. Configure Databricks access in a root `.env` file. Start from
   [`.env.example`](./.env.example), then set the workspace hostname, access
   token, SQL warehouse HTTP path, catalog, and schema. Never commit `.env`.
2. Use a Python environment with the backend dependencies installed and a
   Node.js environment for the frontend. Install frontend packages with:

   ```powershell
   cd frontend
   npm ci
   cd ..
   ```

3. Start HEAAP from the repository root:

   ```powershell
   .\start_heaap.ps1
   ```

   The helper expects the backend virtual environment at `.venv` and starts
   the backend on port `8001` and frontend on port `3000`.

4. Open [http://localhost:3000](http://localhost:3000), enter a supported
   question, and select **Run metadata + SQL tests**. The report shows the
   specialist-agent outcomes and generated SQL. **Metadata-only (no SQL)**
   intentionally stops after metadata checks.

The detailed pipeline report is at
[http://localhost:3000/business-query-assurance](http://localhost:3000/business-query-assurance).
The backend API docs are at [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs).

## Validation

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_business_question_metadata_validation.py -q
Set-Location frontend
npm.cmd exec -- tsc --noEmit
```
