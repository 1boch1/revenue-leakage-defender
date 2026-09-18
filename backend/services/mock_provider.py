from __future__ import annotations

import logging
from typing import TypeVar

from models.schemas import (
    ContractPricingRule,
    ContractReasoningOutput,
    ContractTerms,
    DiscrepancyReasoning,
    DisputeEmailDraft,
    Invoice,
    InvoiceLine,
)
from services.llm_provider import BaseLLMProvider, LLMProviderError

logger = logging.getLogger(__name__)
T = TypeVar("T")


class MockLLMProvider(BaseLLMProvider):
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.call_count = 0

    async def structured_completion(
        self,
        system_prompt: str,
        user_message: str,
        output_schema: type[T],
    ) -> T:
        self.call_count += 1
        logger.info("MockLLMProvider: chiamata #%d schema=%s", self.call_count, output_schema.__name__)

        if self.should_fail:
            raise LLMProviderError("Simulated LLM API failure")

        if output_schema == Invoice:
            return Invoice(
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
            )  # type: ignore

        if output_schema == ContractTerms:
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
            )  # type: ignore

        if output_schema == ContractReasoningOutput:
            return ContractReasoningOutput(
                analyses=[
                    DiscrepancyReasoning(
                        field_name="unit_price:Consulenza Senior",
                        verdict="UNJUSTIFIED",
                        reasoning="La tariffa di 600/gg supera il massimo contrattuale di 500/gg e non risulta alcuna comunicazione formale di adeguamento ISTAT con preavviso di 90gg.",
                    ),
                    DiscrepancyReasoning(
                        field_name="line_total:Formazione Team",
                        verdict="UNJUSTIFIED",
                        reasoning="Errore di calcolo aritmetico nella riga: quantita 3 x 400,00 = 1.200,00, mentre in fattura e indicato 1.250,00.",
                    ),
                    DiscrepancyReasoning(
                        field_name="subtotal",
                        verdict="UNJUSTIFIED",
                        reasoning="Il subtotale esposto (16.800,00) non corrisponde alla somma reale delle righe fattura (16.750,00).",
                    ),
                    DiscrepancyReasoning(
                        field_name="payment_terms_days",
                        verdict="UNJUSTIFIED",
                        reasoning="I termini di pagamento di 30 giorni indicati in fattura violano la clausola di 60 giorni del contratto quadro.",
                    ),
                ]
            )  # type: ignore

        if output_schema == DisputeEmailDraft:
            return DisputeEmailDraft(
                subject="Contestazione formale fattura INV-2024-1042 (Rif. Contratto MSA-2023-ACME-001)",
                body=(
                    "Spett.le TechConsult S.r.l.,\n\n"
                    "Con riferimento alla fattura n. INV-2024-1042 del 15/06/2024 per un totale di 20.496,00 IVA inclusa, "
                    "a seguito del controllo di conformita con il Contratto Quadro MSA-2023-ACME-001 "
                    "sono emerse le seguenti discrepanze:\n\n"
                    "1. Tariffa Consulenza Senior applicata a 600,00/gg anziche il massimo concordato di 500,00/gg (sovrapprezzo: 1.000,00);\n"
                    "2. Errore aritmetico sulla riga Formazione Team (3 x 400,00 = 1.200,00, esposto 1.250,00, sovrapprezzo: 50,00);\n"
                    "3. Subtotale errato (16.800,00 anziche 16.750,00, delta: 50,00);\n"
                    "4. Termini di pagamento indicati a 30 giorni, in contrasto con i 60 giorni pattuiti.\n\n"
                    "L'importo totale indebitamente fatturato ammonta a 1.100,00 oltre IVA.\n\n"
                    "Chiediamo l'emissione di nota di credito e documento corretto con scadenza a 60 giorni.\n\n"
                    "Cordiali saluti,\n"
                    "ACME Italia S.p.A., Finance & Operations"
                ),
            )  # type: ignore

        raise ValueError(f"Schema sconosciuto: {output_schema}")
