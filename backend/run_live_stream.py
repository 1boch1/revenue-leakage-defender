from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env", override=True)

from graph.workflow import build_workflow


async def main():
    print("Revenue Leakage Defender: live stream")
    print("")

    fixtures_dir = Path(__file__).parent / "tests" / "fixtures"
    invoice_pdf = fixtures_dir / "fattura_test.pdf"
    contract_pdf = fixtures_dir / "contratto_test.pdf"

    if not invoice_pdf.exists() or not contract_pdf.exists():
        print("Fixtures mancanti, generazione in corso.")
        from tests.generate_test_pdfs import main as gen_main

        gen_main()

    api_key = os.getenv("GEMINI_API_KEY", "")
    is_live = bool(api_key.strip() not in ("", "la-tua-api-key-qui", "YOUR_API_KEY"))

    if is_live:
        print(f"Modalita: live ({os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')})")
    else:
        print("Modalita: mock locale (zero cost)")

    print(f"Fattura: {invoice_pdf.name} ({invoice_pdf.stat().st_size:,} bytes)")
    print(f"Contratto: {contract_pdf.name} ({contract_pdf.stat().st_size:,} bytes)")
    print("-" * 72)
    print(f"{'TEMPO':>8}  {'NODO':<26}  OUTPUT")
    print("-" * 72)

    workflow = build_workflow()
    t0 = time.perf_counter()
    final_report = None

    async for chunk in workflow.astream(
        {
            "invoice_pdf_bytes": invoice_pdf.read_bytes(),
            "contract_pdf_bytes": contract_pdf.read_bytes(),
        },
        stream_mode="updates",
    ):
        for node_name, state_update in chunk.items():
            elapsed = time.perf_counter() - t0
            if node_name == "parse_documents":
                summary = (
                    f"Fattura: {len(state_update.get('raw_invoice_text', ''))} car., "
                    f"Contratto: {len(state_update.get('raw_contract_text', ''))} car."
                )
            elif node_name == "extract_invoice":
                inv = state_update.get("parsed_invoice")
                summary = (
                    f"Fattura {inv.invoice_id} ({len(inv.lines)} righe, {inv.total_amount:,.2f})"
                    if inv
                    else "Estrazione fattura fallita"
                )
            elif node_name == "extract_contract":
                ctr = state_update.get("parsed_contract")
                summary = (
                    f"Contratto {ctr.contract_id} ({len(ctr.pricing_rules)} tariffe)"
                    if ctr
                    else "Estrazione contratto fallita"
                )
            elif node_name == "deterministic_match":
                summary = f"{len(state_update.get('raw_discrepancies', []))} discrepanze rilevate"
            elif node_name == "llm_contract_reasoning":
                analyzed = state_update.get("analyzed_discrepancies", [])
                unjustified = sum(1 for d in analyzed if not d.is_justified_by_contract)
                summary = f"{unjustified} ingiustificate su {len(analyzed)}"
            elif node_name == "generate_dispute_report":
                final_report = state_update.get("final_report")
                summary = (
                    f"{final_report.status}, overbilling {final_report.total_overbilling:,.2f}"
                    if final_report
                    else "Report mancante"
                )
            else:
                summary = ""
            print(f"[{elapsed:6.2f}s]  {node_name:<26}  {summary}")

    total_time = time.perf_counter() - t0
    print("-" * 72)
    if final_report:
        print(f"Risultato: {final_report.status} ({total_time:.2f}s)")
        print(f"Sovrafatturazione: {final_report.total_overbilling:,.2f}")
        print(f"Discrepanze: {len(final_report.discrepancies)}")
        if final_report.dispute_email_draft:
            print("")
            print("Bozza email:")
            print("-" * 40)
            print(final_report.dispute_email_draft[:300] + "...")


if __name__ == "__main__":
    asyncio.run(main())
