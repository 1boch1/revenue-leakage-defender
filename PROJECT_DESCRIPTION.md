# Revenue Leakage Defender: Descrizione Progetto

## 1. Visione e problema

Strumento GenAI per Finance/Operations che verifica le fatture contro i
contratti quadro, individua discrepanze (prezzi non concordati, clausole
violate, errori di calcolo) e genera un report di contestazione con bozza email.

Target: finance manager, operations team, valutatori tecnici in demo.

## 2. Vincoli architetturali

| Vincolo | Descrizione |
|---------|-------------|
| Zero costi cloud | Architettura pensata per AWS, implementazione 100% locale/gratuita |
| Stateless, privacy-first | Nessun database; PDF in memoria, cancellati dopo la risposta |
| LLM indipendente dal provider | Interfaccia `BaseLLMProvider`; switch via env (Gemini, OpenAI, Groq, Ollama) |
| Niente email reali | Mail di disputa generata come testo, mai inviata |

## 3. Stack

| Layer | Tecnologia | Scopo |
|-------|-----------|-------|
| Backend | Python + FastAPI | API REST, upload PDF |
| Orchestrazione | LangGraph | Workflow a grafo |
| Validazione | Pydantic v2 | Structured output e stato |
| PDF parsing | pdfplumber | Estrazione testo/tabelle |
| LLM | Google Gemini | Free tier via SDK `google-genai` |
| Frontend | HTML/CSS/JS | Drag & drop, dashboard risultati |

Dipendenze in `backend/requirements.txt`.

## 4. Workflow LangGraph

Sei nodi:

1. `parse_documents`: testo grezzo dai PDF in memoria.
2. `extract_invoice`: structured output verso `Invoice`.
3. `extract_contract`: structured output verso `ContractTerms`.
4. `deterministic_match`: confronto numerico in Python, produce `raw_discrepancies`.
5. `llm_contract_reasoning`: classifica ogni mismatch come giustificato/ingiustificato.
6. `generate_dispute_report`: `FinalReport` + bozza email.

## 5. Stato di completamento

| Componente | Stato |
|-----------|-------|
| Modelli Pydantic | Completo |
| GraphState | Completo |
| LLM provider + Mock | Completo |
| PDF parser | Completo |
| Prompt | Completo |
| Nodi e grafo | Completo |
| FastAPI (`/analyze`, `/analyze/stream`) | Completo |
| Test e fixture (14 test) | Completo |
| Frontend Web UI | Completo |
| Streaming SSE + CLI | Completo |
| README e guida codice | Completo |

## 6. Architettura AWS target

```
[Frontend] -> [API Gateway] -> [Lambda/ECS] -> [Bedrock]
                                        S3 (PDF temporanei)
                                        DynamoDB (audit log)
                                        SES (invio contestazioni)
```

## 7. Design pattern

- Dependency inversion (`BaseLLMProvider`)
- Factory (`create_llm_provider`)
- Structured output su schemi Pydantic
- Stateless processing in-memory
- Pipeline ibrida deterministico/probabilistica
- Degradazione elegante su errori LLM o PDF non leggibili
