from __future__ import annotations

from typing import TypedDict

from models.schemas import ContractTerms, Discrepancy, FinalReport, Invoice


class GraphState(TypedDict, total=False):
    invoice_pdf_bytes: bytes
    contract_pdf_bytes: bytes

    raw_invoice_text: str
    raw_contract_text: str

    parsed_invoice: Invoice | None
    parsed_contract: ContractTerms | None

    invoice_extraction_error: str | None
    contract_extraction_error: str | None

    raw_discrepancies: list[Discrepancy]
    analyzed_discrepancies: list[Discrepancy]

    final_report: FinalReport | None
