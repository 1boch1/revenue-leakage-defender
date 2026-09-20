from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from graph.workflow import build_workflow
from models.schemas import FinalReport

load_dotenv(override=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-28s | %(levelname)-5s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Revenue Leakage Defender",
    description="Audit contrattuale delle fatture fornitore.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

workflow = build_workflow()

FIXTURES_DIR = Path(__file__).parent / "tests" / "fixtures"
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
DOCS_DIR = Path(__file__).parent.parent / "docs"


async def _read_pdf_upload(file: UploadFile, label: str) -> bytes:
    if file.content_type and file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail=f"Il file {label} deve essere un PDF (ricevuto: {file.content_type})",
        )
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Errore lettura file {label}: {e}")
    finally:
        await file.close()
    if not content:
        raise HTTPException(status_code=400, detail=f"Il file {label} e vuoto.")
    return content


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "revenue-leakage-defender"}


@app.post("/analyze", response_model=FinalReport)
async def analyze(
    invoice: UploadFile = File(..., description="PDF della fattura fornitore"),
    contract: UploadFile = File(..., description="PDF del contratto quadro"),
):
    invoice_bytes = await _read_pdf_upload(invoice, "fattura")
    contract_bytes = await _read_pdf_upload(contract, "contratto")
    logger.info("/analyze: fattura=%dB contratto=%dB", len(invoice_bytes), len(contract_bytes))
    t0 = time.perf_counter()
    try:
        result = await workflow.ainvoke({
            "invoice_pdf_bytes": invoice_bytes,
            "contract_pdf_bytes": contract_bytes,
        })
    except Exception as e:
        logger.exception("Errore workflow")
        raise HTTPException(status_code=500, detail=f"Errore durante l'analisi: {e}")
    logger.info("/analyze completato in %.2fs", time.perf_counter() - t0)
    report = result.get("final_report")
    if not report:
        raise HTTPException(status_code=500, detail="Report finale non generato.")
    return report


@app.post("/analyze/stream")
async def analyze_stream(
    invoice: UploadFile = File(..., description="PDF della fattura fornitore"),
    contract: UploadFile = File(..., description="PDF del contratto quadro"),
):
    invoice_bytes = await _read_pdf_upload(invoice, "fattura")
    contract_bytes = await _read_pdf_upload(contract, "contratto")

    async def event_generator():
        t0 = time.perf_counter()
        yield f"data: {json.dumps({'type': 'init', 'message': 'Avvio analisi...'})}\n\n"
        final_report = None
        try:
            async for chunk in workflow.astream(
                {"invoice_pdf_bytes": invoice_bytes, "contract_pdf_bytes": contract_bytes},
                stream_mode="updates",
            ):
                for node_name, state_update in chunk.items():
                    elapsed = round(time.perf_counter() - t0, 2)
                    summary = ""
                    if node_name == "parse_documents":
                        inv_len = len(state_update.get("raw_invoice_text", ""))
                        ctr_len = len(state_update.get("raw_contract_text", ""))
                        summary = f"PDF estratti: fattura ({inv_len:,} car.), contratto ({ctr_len:,} car.)"
                    elif node_name == "extract_invoice":
                        inv = state_update.get("parsed_invoice")
                        if inv:
                            summary = f"Fattura {inv.invoice_id} ({inv.vendor_name}): {len(inv.lines)} righe, totale {inv.total_amount:,.2f}"
                        else:
                            summary = f"Fattura: {state_update.get('invoice_extraction_error')}"
                    elif node_name == "extract_contract":
                        ctr = state_update.get("parsed_contract")
                        if ctr:
                            summary = f"Contratto {ctr.contract_id}: {len(ctr.pricing_rules)} tariffe"
                        else:
                            summary = f"Contratto: {state_update.get('contract_extraction_error')}"
                    elif node_name == "deterministic_match":
                        raw = state_update.get("raw_discrepancies", [])
                        summary = f"Match numerico: {len(raw)} discrepanze grezze"
                    elif node_name == "llm_contract_reasoning":
                        analyzed = state_update.get("analyzed_discrepancies", [])
                        unjustified = sum(1 for d in analyzed if not d.is_justified_by_contract)
                        summary = f"Reasoning: {unjustified} discrepanze ingiustificate"
                    elif node_name == "generate_dispute_report":
                        rep = state_update.get("final_report")
                        if rep:
                            final_report = rep
                            summary = f"Report: {rep.status}, sovrafatturazione {rep.total_overbilling:,.2f}"
                    yield f"data: {json.dumps({'type': 'node_update', 'node': node_name, 'elapsed': elapsed, 'summary': summary})}\n\n"

            if final_report:
                yield f"data: {json.dumps({'type': 'complete', 'report': final_report.model_dump(), 'elapsed': round(time.perf_counter() - t0, 2)})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Nessun report generato.'})}\n\n"
        except Exception as e:
            logger.exception("Errore streaming workflow")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _ensure_fixtures() -> None:
    inv = FIXTURES_DIR / "fattura_test.pdf"
    ctr = FIXTURES_DIR / "contratto_test.pdf"
    if not inv.exists() or not ctr.exists():
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        from tests.generate_test_pdfs import generate_contract_pdf, generate_invoice_pdf

        generate_invoice_pdf()
        generate_contract_pdf()


@app.get("/demo-fixtures/status")
async def demo_fixtures_status():
    _ensure_fixtures()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    is_live = bool(api_key and api_key not in ("la-tua-api-key-qui", "YOUR_API_KEY"))
    return {
        "status": "ready",
        "llm_mode": "live_gemini" if is_live else "zero_cost_demo",
        "fixtures": ["fattura_test.pdf", "contratto_test.pdf"],
    }


@app.get("/demo-fixtures/invoice")
async def demo_invoice_pdf():
    _ensure_fixtures()
    return FileResponse(
        path=str(FIXTURES_DIR / "fattura_test.pdf"),
        media_type="application/pdf",
        filename="fattura_test.pdf",
    )


@app.get("/demo-fixtures/contract")
async def demo_contract_pdf():
    _ensure_fixtures()
    return FileResponse(
        path=str(FIXTURES_DIR / "contratto_test.pdf"),
        media_type="application/pdf",
        filename="contratto_test.pdf",
    )


if DOCS_DIR.exists():
    app.mount("/docs", StaticFiles(directory=str(DOCS_DIR), html=True), name="docs")

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
