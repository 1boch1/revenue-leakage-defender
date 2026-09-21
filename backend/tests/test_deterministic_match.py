from graph.nodes import deterministic_match
from graph.state import GraphState
from models.schemas import ContractPricingRule, ContractTerms, Invoice, InvoiceLine


def create_sample_contract() -> ContractTerms:
    return ContractTerms(
        contract_id="MSA-2023-ACME-001",
        vendor_name="TechConsult S.r.l.",
        client_name="ACME Italia S.p.A.",
        effective_date="2024-01-01",
        expiry_date="2025-12-31",
        payment_terms_days=60,
        pricing_rules=[
            ContractPricingRule(
                service_type="Consulenza Senior",
                max_unit_price=500.0,
                unit="giorno/uomo",
            ),
            ContractPricingRule(
                service_type="Sviluppo Software",
                max_unit_price=450.0,
                unit="giorno/uomo",
            ),
            ContractPricingRule(
                service_type="Project Management",
                max_unit_price=550.0,
                unit="giorno/uomo",
            ),
            ContractPricingRule(
                service_type="Formazione Team",
                max_unit_price=400.0,
                unit="giorno/uomo",
            ),
        ],
        allows_price_adjustments=True,
        adjustment_rules="Adeguamento ISTAT annuale con 90gg di preavviso.",
        late_payment_penalty_pct=2.0,
        governing_law="Legge Italiana",
    )


def test_deterministic_match_detects_all_discrepancies():
    invoice = Invoice(
        invoice_id="INV-2024-1042",
        vendor_name="TechConsult S.r.l.",
        client_name="ACME Italia S.p.A.",
        invoice_date="2024-06-15",
        due_date="2024-07-15",
        payment_terms_days=30,
        currency="EUR",
        lines=[
            InvoiceLine(
                description="Consulenza Senior",
                quantity=10.0,
                unit_price=600.0,
                total_price=6000.0,
            ),
            InvoiceLine(
                description="Sviluppo Software",
                quantity=15.0,
                unit_price=450.0,
                total_price=6750.0,
            ),
            InvoiceLine(
                description="Project Management",
                quantity=5.0,
                unit_price=550.0,
                total_price=2750.0,
            ),
            InvoiceLine(
                description="Formazione Team",
                quantity=3.0,
                unit_price=400.0,
                total_price=1250.0,
            ),
        ],
        subtotal=16800.0,
        tax_rate=22.0,
        tax_amount=3696.0,
        total_amount=20496.0,
    )
    state: GraphState = {
        "parsed_invoice": invoice,
        "parsed_contract": create_sample_contract(),
    }

    discrepancies = deterministic_match(state).get("raw_discrepancies", [])
    field_names = [d.field_name for d in discrepancies]

    assert "unit_price:Consulenza Senior" in field_names
    assert "line_total:Formazione Team" in field_names
    assert "subtotal" in field_names
    assert "payment_terms_days" in field_names

    up_disc = next(d for d in discrepancies if d.field_name == "unit_price:Consulenza Senior")
    assert up_disc.delta == 1000.0
    assert up_disc.severity in ("medium", "high")

    lt_disc = next(d for d in discrepancies if d.field_name == "line_total:Formazione Team")
    assert lt_disc.delta == 50.0

    st_disc = next(d for d in discrepancies if d.field_name == "subtotal")
    assert st_disc.delta == 50.0


def test_deterministic_match_compliant_invoice():
    invoice = Invoice(
        invoice_id="INV-2024-OK",
        vendor_name="TechConsult S.r.l.",
        client_name="ACME Italia S.p.A.",
        invoice_date="2024-06-15",
        payment_terms_days=60,
        currency="EUR",
        lines=[
            InvoiceLine(
                description="Consulenza Senior",
                quantity=5.0,
                unit_price=500.0,
                total_price=2500.0,
            ),
            InvoiceLine(
                description="Sviluppo Software",
                quantity=10.0,
                unit_price=450.0,
                total_price=4500.0,
            ),
        ],
        subtotal=7000.0,
        tax_rate=22.0,
        tax_amount=1540.0,
        total_amount=8540.0,
    )
    state: GraphState = {
        "parsed_invoice": invoice,
        "parsed_contract": create_sample_contract(),
    }

    assert len(deterministic_match(state).get("raw_discrepancies", [])) == 0


def test_deterministic_match_missing_data():
    state: GraphState = {}
    assert deterministic_match(state) == {"raw_discrepancies": []}
