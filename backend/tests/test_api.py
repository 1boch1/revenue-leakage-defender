from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from graph.nodes import set_llm_provider
from main import app
from services.mock_provider import MockLLMProvider

FIXTURES_DIR = Path(__file__).parent / "fixtures"
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_llm():
    yield
    set_llm_provider(None)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "revenue-leakage-defender"


def test_analyze_rejects_non_pdf():
    files = {
        "invoice": ("invoice.txt", b"testo semplice", "text/plain"),
        "contract": ("contract.pdf", b"%PDF-1.4 dummy", "application/pdf"),
    }
    response = client.post("/analyze", files=files)
    assert response.status_code == 400
    assert "deve essere un PDF" in response.json()["detail"]


def test_analyze_rejects_empty_file():
    files = {
        "invoice": ("invoice.pdf", b"", "application/pdf"),
        "contract": ("contract.pdf", b"%PDF-1.4 dummy", "application/pdf"),
    }
    response = client.post("/analyze", files=files)
    assert response.status_code == 400
    assert "vuoto" in response.json()["detail"]


def test_analyze_successful_e2e():
    invoice_path = FIXTURES_DIR / "fattura_test.pdf"
    contract_path = FIXTURES_DIR / "contratto_test.pdf"

    set_llm_provider(MockLLMProvider())

    with open(invoice_path, "rb") as inv_f, open(contract_path, "rb") as ctr_f:
        files = {
            "invoice": ("fattura_test.pdf", inv_f.read(), "application/pdf"),
            "contract": ("contratto_test.pdf", ctr_f.read(), "application/pdf"),
        }

    response = client.post("/analyze", files=files)
    assert response.status_code == 200

    report = response.json()
    assert report["status"] == "DISCREPANCIES_FOUND"
    assert report["invoice_id"] == "INV-2024-1042"
    assert report["contract_id"] == "MSA-2023-ACME-001"
    assert report["total_overbilling"] >= 1000.0
    assert len(report["discrepancies"]) > 0
    assert report["dispute_email_draft"] is not None


def test_demo_fixtures_endpoints():
    status_resp = client.get("/demo-fixtures/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "ready"
    assert "fixtures" in status_resp.json()

    inv_resp = client.get("/demo-fixtures/invoice")
    assert inv_resp.status_code == 200
    assert inv_resp.headers["content-type"] == "application/pdf"
    assert len(inv_resp.content) > 500

    ctr_resp = client.get("/demo-fixtures/contract")
    assert ctr_resp.status_code == 200
    assert ctr_resp.headers["content-type"] == "application/pdf"
    assert len(ctr_resp.content) > 500
