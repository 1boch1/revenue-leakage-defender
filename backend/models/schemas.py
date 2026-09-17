from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class InvoiceLine(BaseModel):
    description: str = Field(description="Descrizione del servizio o prodotto fatturato.")
    quantity: float = Field(description="Quantita (puo essere frazionaria, es. 2.5).")
    unit_price: float = Field(description="Prezzo unitario, al netto di IVA.")
    total_price: float = Field(description="Totale riga = quantity x unit_price.")


class Invoice(BaseModel):
    invoice_id: str = Field(description="Codice identificativo (es. 'INV-2024-1042').")
    vendor_name: str = Field(description="Nome del fornitore.")
    client_name: str = Field(description="Nome del cliente.")
    invoice_date: str = Field(description="Data di emissione (YYYY-MM-DD).")
    due_date: str | None = Field(default=None, description="Data scadenza pagamento (YYYY-MM-DD).")
    currency: str = Field(default="EUR", description="Valuta ISO 4217 (es. 'EUR').")
    lines: list[InvoiceLine] = Field(description="Righe di fattura.")
    subtotal: float = Field(description="Totale imponibile, al netto di IVA.")
    tax_rate: float | None = Field(default=None, description="Aliquota IVA in % (es. 22.0).")
    tax_amount: float | None = Field(default=None, description="Importo IVA totale.")
    total_amount: float = Field(description="Totale fattura, IVA inclusa.")
    payment_terms_days: int | None = Field(default=None, description="Giorni per il pagamento (es. 30, 60).")
    notes: str | None = Field(default=None, description="Note aggiuntive, se presenti.")


class ContractPricingRule(BaseModel):
    service_type: str = Field(description="Tipo di servizio (es. 'Consulenza Senior').")
    max_unit_price: float = Field(description="Prezzo unitario massimo concordato.")
    unit: str = Field(description="Unita di misura (es. 'giorno/uomo', 'ora').")
    notes: str | None = Field(default=None, description="Eccezioni o condizioni specifiche.")


class ContractTerms(BaseModel):
    contract_id: str = Field(description="Identificativo contratto (es. 'MSA-2023-AGENCY-001').")
    vendor_name: str = Field(description="Fornitore firmatario.")
    client_name: str = Field(description="Cliente firmatario.")
    effective_date: str = Field(description="Inizio validita (YYYY-MM-DD).")
    expiry_date: str | None = Field(default=None, description="Scadenza contratto (YYYY-MM-DD).")
    payment_terms_days: int = Field(description="Giorni massimi concordati per il pagamento.")
    pricing_rules: list[ContractPricingRule] = Field(description="Regole di pricing per servizio.")
    allows_price_adjustments: bool = Field(description="True se il contratto permette adeguamenti (es. ISTAT).")
    adjustment_rules: str | None = Field(
        default=None,
        description="Condizioni per gli adeguamenti. Obbligatorio se allows_price_adjustments e True.",
    )
    late_payment_penalty_pct: float | None = Field(default=None, description="% penale ritardo pagamento.")
    governing_law: str | None = Field(default=None, description="Legge applicabile (es. 'Legge Italiana').")


class Discrepancy(BaseModel):
    field_name: str = Field(description="Campo interessato (es. 'unit_price:Consulenza Senior').")
    invoice_value: str = Field(description="Valore presente in fattura.")
    expected_value: str = Field(description="Valore atteso in base al contratto o ai calcoli.")
    delta: float | None = Field(default=None, description="Differenza monetaria (EUR) se applicabile.")
    severity: Literal["low", "medium", "high"] = Field(
        description="'low' = <5% o <500EUR; 'medium' = 5-15% o 500-2000EUR; 'high' = >15% o >2000EUR."
    )
    is_justified_by_contract: bool = Field(description="True se giustificata da una clausola contrattuale.")
    reasoning: str = Field(description="Motivazione dell'anomalia e perche e (o non e) giustificata.")


class FinalReport(BaseModel):
    status: Literal["APPROVED", "DISCREPANCIES_FOUND"] = Field(
        description="APPROVED = nessuna anomalia ingiustificata. DISCREPANCIES_FOUND = altrimenti."
    )
    invoice_id: str = Field(description="ID fattura analizzata.")
    contract_id: str = Field(description="ID contratto di riferimento.")
    analysis_summary: str = Field(description="Sommario esecutivo dell'audit in linguaggio naturale.")
    discrepancies: list[Discrepancy] = Field(default_factory=list, description="Lista delle anomalie riscontrate.")
    total_overbilling: float = Field(default=0.0, description="Importo totale sovrafatturato (EUR).")
    dispute_email_draft: str | None = Field(default=None, description="Bozza email formale di contestazione.")

    @model_validator(mode="after")
    def validate_consistency(self) -> FinalReport:
        if self.status == "DISCREPANCIES_FOUND" and not self.discrepancies:
            raise ValueError("DISCREPANCIES_FOUND richiede almeno una discrepanza nella lista.")
        if self.status == "APPROVED" and self.discrepancies:
            raise ValueError("APPROVED non puo contenere discrepanze ingiustificate.")
        return self


class DiscrepancyReasoning(BaseModel):
    field_name: str = Field(description="Il field_name della discrepanza, identico all'input ricevuto.")
    verdict: Literal["JUSTIFIED", "UNJUSTIFIED"] = Field(
        description="JUSTIFIED = coperta da clausola contrattuale. UNJUSTIFIED = sovrafatturazione indebita."
    )
    reasoning: str = Field(
        description="Spiegazione: quale clausola la giustifica, oppure perche nessuna la copre."
    )


class ContractReasoningOutput(BaseModel):
    analyses: list[DiscrepancyReasoning] = Field(
        description="Un'analisi per ciascuna discrepanza ricevuta, mantenendo lo stesso ordine."
    )


class DisputeEmailDraft(BaseModel):
    subject: str = Field(description="Oggetto dell'email (chiaro, sintetico e formale).")
    body: str = Field(
        description="Testo dell'email. Tono professionale e assertivo, con elenco anomalie e richiesta nota di credito."
    )
