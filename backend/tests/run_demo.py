from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from graph.nodes import set_llm_provider
from graph.workflow import build_workflow
from services.mock_provider import MockLLMProvider


async def main():
    print("Revenue Leakage Defender: demo end-to-end")
    print("")

    fixtures_dir = Path(__file__).parent / "fixtures"
    invoice_pdf = fixtures_dir / "fattura_test.pdf"
    contract_pdf = fixtures_dir / "contratto_test.pdf"

    if not invoice_pdf.exists() or not contract_pdf.exists():
        print("Fixtures mancanti, generazione in corso.")
        from tests.generate_test_pdfs import main as gen_main

        gen_main()

    api_key = os.environ.get("GEMINI_API_KEY", "")
    has_gemini = bool(api_key and api_key != "la-tua-api-key-qui")

    if has_gemini:
        print("Modalita: live (Gemini)")
    else:
        print("Modalita: mock locale")
        set_llm_provider(MockLLMProvider())

    print(f"Fattura: {invoice_pdf.name} ({invoice_pdf.stat().st_size:,} bytes)")
    print(f"Contratto: {contract_pdf.name} ({contract_pdf.stat().st_size:,} bytes)")
    print("")

    workflow = build_workflow()
    t0 = time.perf_counter()
    result = await workflow.ainvoke({
        "invoice_pdf_bytes": invoice_pdf.read_bytes(),
        "contract_pdf_bytes": contract_pdf.read_bytes(),
    })
    elapsed = time.perf_counter() - t0
    report = result["final_report"]

    print(f"Analisi completata in {elapsed:.2f}s")
    print(f"Status: {report.status}")
    print(f"Fattura: {report.invoice_id}")
    print(f"Contratto: {report.contract_id}")
    print(f"Sovrafatturazione: {report.total_overbilling:,.2f}")
    print(f"Sommario: {report.analysis_summary}")
    print("")
    print("Discrepanze:")
    for i, d in enumerate(report.discrepancies, 1):
        print(f"[{i}] {d.field_name} (severity: {d.severity})")
        print(f"    Fattura: {d.invoice_value}")
        print(f"    Atteso: {d.expected_value}")
        if d.delta:
            print(f"    Delta: {d.delta:,.2f}")
        print(f"    Giustificata: {'si' if d.is_justified_by_contract else 'no'}")
        print(f"    Motivo: {d.reasoning}")

    if report.dispute_email_draft:
        print("")
        print("Bozza email:")
        print(report.dispute_email_draft)

    print("")
    print("Demo completata.")


if __name__ == "__main__":
    asyncio.run(main())
