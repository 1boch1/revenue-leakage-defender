# Revenue Leakage Defender

> English version. [Versione italiana](README.md).

GenAI agent for compliance checks between supplier invoices and framework contracts.
It compares invoice lines and contract clauses through a hybrid
deterministic/probabilistic pipeline orchestrated with LangGraph.

## Contents

1. [Problem](#problem)
2. [Constraints](#constraints)
3. [Architecture](#architecture)
4. [Observability](#observability)
5. [Quickstart](#quickstart)
6. [Tests](#tests)
7. [Repository layout](#repository-layout)

## Problem

Manual verification of supplier invoices against framework contracts (MSAs)
is slow and sample-based. Rate errors, wrong line totals and non-compliant
payment terms generate overbilling. This project automates the cycle:
it extracts clauses and invoice lines, computes numeric discrepancies and
evaluates contractual justifications, producing a report and a draft dispute email.

## Constraints

| Constraint | Solution |
|---|---|
| Zero cloud cost | 100% local implementation; Mock provider for CI/CD, Gemini free tier optionally |
| Stateless, privacy-first | PDFs processed in RAM (`io.BytesIO`), never written to disk |
| Provider-independent LLM | `BaseLLMProvider` interface; switch via environment variables |
| Safe automation | Read-only dispute draft, mandatory human review |

## Architecture

6-node LangGraph pipeline:

```
parse_documents -> extract_invoice -> extract_contract
  -> deterministic_match -> [llm_contract_reasoning] -> generate_dispute_report
```

1. `parse_documents`: extracts text and tables from in-memory PDFs (pdfplumber).
2. `extract_invoice`: LLM structured output into the Pydantic `Invoice` schema.
3. `extract_contract`: LLM structured output into the `ContractTerms` schema.
4. `deterministic_match`: numeric and rate comparison in pure Python, produces `raw_discrepancies`.
5. `llm_contract_reasoning`: runs only when mismatches exist; evaluates whether deviations are justified by clauses.
6. `generate_dispute_report`: assembles the `FinalReport` and the email draft.

Mapping to the target AWS architecture:

| Local | AWS target |
|---|---|
| FastAPI + Uvicorn | API Gateway + Lambda/ECS |
| Gemini / Mock | Bedrock |
| `io.BytesIO` in RAM | S3 with lifecycle policy |
| Console logs | DynamoDB audit trail, CloudWatch |
| In-memory email text | SES |

## Observability

Three levels:

1. Web UI with stepper and log over SSE (`POST /analyze/stream`): one event per completed node.
2. CLI runner: `python backend/run_live_stream.py`.
3. LangSmith tracing via `.env` (`LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`).

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
```

Set in `backend/.env` (optional; without a key the system uses the Mock):

```env
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.0-flash
```

Start:

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

Open `http://127.0.0.1:8000`, load the sample PDFs with the demo button
and review the dashboard, discrepancies and email draft. Interactive guide at
`http://127.0.0.1:8000/docs/code-guide.html` ([versione italiana](http://127.0.0.1:8000/docs/guida-codice.html)).

## Tests

```bash
PYTHONPATH=backend pytest -v backend/tests/
```

14 unit and integration tests, offline execution with MockLLMProvider.

## Implementation details

- Pydantic `Field(description=...)`: documentation and guidance for LLM structured output.
- Dependency inversion: nodes depend on `BaseLLMProvider`.
- Cross-field validation (`model_validator`): `APPROVED` cannot contain discrepancies.
- Conditional edge: with zero discrepancies the LLM reasoning is skipped.
- Zero disk I/O for input PDFs.

## Repository layout

```text
RevenueLeakageDefender/
├── README.md
├── README.en.md
├── PROJECT_DESCRIPTION.md
├── docs/
│   ├── guida-codice.html
│   └── code-guide.html
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
└── backend/
    ├── requirements.txt
    ├── .env.example
    ├── main.py
    ├── run_live_stream.py
    ├── models/schemas.py
    ├── graph/state.py
    ├── graph/prompts.py
    ├── graph/nodes.py
    ├── graph/workflow.py
    ├── services/llm_provider.py
    ├── services/mock_provider.py
    ├── services/pdf_parser.py
    └── tests/
```

## License

MIT.
