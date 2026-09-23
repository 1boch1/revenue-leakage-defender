# Revenue Leakage Defender

Agente GenAI per la verifica di conformita tra fatture fornitore e contratti quadro.
Confronta righe fattura e clausole contrattuali con una pipeline ibrida
deterministica/probabilistica orchestrata con LangGraph.

## Indice

1. [Problema](#problema)
2. [Vincoli](#vincoli)
3. [Architettura](#architettura)
4. [Osservabilita](#osservabilita)
5. [Quickstart](#quickstart)
6. [Test](#test)
7. [Struttura repository](#struttura-repository)

## Problema

La verifica manuale delle fatture fornitore contro i contratti quadro (MSA)
e lenta e campionaria. Errori tariffari, totali riga errati e termini di
pagamento non conformi generano sovrafatturazione. Questo progetto automatizza
il ciclo: estrae clausole e righe fattura, calcola le discrepanze numeriche e
valuta le motivazioni contrattuali, producendo un report e una bozza di email
di contestazione.

## Vincoli

| Vincolo | Soluzione |
|---|---|
| Zero costi cloud | Implementazione 100% locale; provider Mock per CI/CD, free tier Gemini in opzione |
| Stateless, privacy-first | PDF elaborati in RAM (`io.BytesIO`), mai scritti su disco |
| LLM indipendente dal provider | Interfaccia `BaseLLMProvider`; switch via variabili d'ambiente |
| Safe automation | Bozza di contestazione in sola lettura, revisione umana obbligatoria |

## Architettura

Pipeline LangGraph a 6 nodi:

```
parse_documents -> extract_invoice -> extract_contract
  -> deterministic_match -> [llm_contract_reasoning] -> generate_dispute_report
```

1. `parse_documents`: estrae testo e tabelle dai PDF in memoria (pdfplumber).
2. `extract_invoice`: structured output LLM verso schema Pydantic `Invoice`.
3. `extract_contract`: structured output LLM verso schema `ContractTerms`.
4. `deterministic_match`: confronto matematico e tariffario in puro Python, produce `raw_discrepancies`.
5. `llm_contract_reasoning`: eseguito solo se ci sono mismatch; valuta se le deviazioni sono giustificate da clausole.
6. `generate_dispute_report`: assembla `FinalReport` e bozza email.

Corrispondenza con architettura AWS target:

| Locale | AWS target |
|---|---|
| FastAPI + Uvicorn | API Gateway + Lambda/ECS |
| Gemini / Mock | Bedrock |
| `io.BytesIO` in RAM | S3 con lifecycle policy |
| Log console | DynamoDB audit trail, CloudWatch |
| Testo email in memoria | SES |

## Osservabilita

Tre livelli:

1. Web UI con stepper e log via SSE (`POST /analyze/stream`): un evento per nodo completato.
2. CLI runner: `python backend/run_live_stream.py`.
3. LangSmith tracing via `.env` (`LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`).

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
```

Impostare in `backend/.env` (opzionale; senza chiave il sistema usa il Mock):

```env
GEMINI_API_KEY=la-tua-chiave-api-gemini
GEMINI_MODEL=gemini-2.0-flash
```

Avvio:

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

Aprire `http://127.0.0.1:8000`, caricare i PDF di esempio con il pulsante demo
e consultare dashboard, discrepanze e bozza email. Guida interattiva su
`http://127.0.0.1:8000/docs/guida-codice.html`.

## Test

```bash
PYTHONPATH=backend pytest -v backend/tests/
```

14 test unitari e di integrazione, esecuzione offline con MockLLMProvider.

## Dettagli implementativi

- `Field(description=...)` Pydantic: documentazione e guida per lo structured output LLM.
- Inversione delle dipendenze: i nodi dipendono da `BaseLLMProvider`.
- Validazione cross-field (`model_validator`): `APPROVED` non puo contenere discrepanze.
- Edge condizionale: con zero discrepanze si salta il reasoning LLM.
- Zero disk I/O per i PDF in input.

## Struttura repository

```text
RevenueLeakageDefender/
├── README.md
├── PROJECT_DESCRIPTION.md
├── docs/
│   └── guida-codice.html
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

## Licenza

MIT.
