from pathlib import Path

import pytest

from graph.nodes import set_llm_provider
from graph.workflow import _route_after_match, build_workflow
from services.mock_provider import MockLLMProvider

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def reset_llm():
    yield
    set_llm_provider(None)


@pytest.mark.asyncio
async def test_workflow_end_to_end_with_discrepancies():
    invoice_pdf = FIXTURES_DIR / "fattura_test.pdf"
    contract_pdf = FIXTURES_DIR / "contratto_test.pdf"

    set_llm_provider(MockLLMProvider())
    workflow = build_workflow()

    result = await workflow.ainvoke({
        "invoice_pdf_bytes": invoice_pdf.read_bytes(),
        "contract_pdf_bytes": contract_pdf.read_bytes(),
    })

    assert "raw_invoice_text" in result
    assert "raw_contract_text" in result
    assert "parsed_invoice" in result
    assert "parsed_contract" in result
    assert "raw_discrepancies" in result
    assert "analyzed_discrepancies" in result
    assert "final_report" in result

    report = result["final_report"]
    assert report.status == "DISCREPANCIES_FOUND"
    assert report.invoice_id == "INV-2024-1042"
    assert report.contract_id == "MSA-2023-ACME-001"
    assert len(report.discrepancies) > 0
    assert report.total_overbilling >= 1000.0
    assert report.dispute_email_draft is not None
    assert "Contestazione formale" in report.dispute_email_draft


def test_workflow_conditional_routing():
    assert _route_after_match({"raw_discrepancies": [{"dummy": "item"}]}) == "llm_contract_reasoning"
    assert _route_after_match({"raw_discrepancies": []}) == "generate_dispute_report"


@pytest.mark.asyncio
async def test_workflow_graceful_degradation_on_llm_error():
    invoice_pdf = FIXTURES_DIR / "fattura_test.pdf"
    contract_pdf = FIXTURES_DIR / "contratto_test.pdf"

    set_llm_provider(MockLLMProvider(should_fail=True))
    workflow = build_workflow()

    result = await workflow.ainvoke({
        "invoice_pdf_bytes": invoice_pdf.read_bytes(),
        "contract_pdf_bytes": contract_pdf.read_bytes(),
    })

    assert "invoice_extraction_error" in result or "contract_extraction_error" in result
    assert "incompleta a causa di errori" in result["final_report"].analysis_summary
