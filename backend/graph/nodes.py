from __future__ import annotations

import logging

from graph.prompts import (
    EXTRACT_CONTRACT_SYSTEM,
    EXTRACT_INVOICE_SYSTEM,
    GENERATE_DISPUTE_EMAIL_SYSTEM,
    LLM_REASONING_SYSTEM,
)
from graph.state import GraphState
from models.schemas import (
    ContractPricingRule,
    ContractReasoningOutput,
    ContractTerms,
    Discrepancy,
    DisputeEmailDraft,
    FinalReport,
    Invoice,
)
from services.llm_provider import BaseLLMProvider, LLMProviderError, create_llm_provider
from services.pdf_parser import extract_text_from_pdf

logger = logging.getLogger(__name__)

_llm: BaseLLMProvider | None = None


def set_llm_provider(provider: BaseLLMProvider | None) -> None:
    global _llm
    _llm = provider


def _get_llm() -> BaseLLMProvider:
    global _llm
    if _llm is not None:
        return _llm
    return create_llm_provider()


async def parse_documents(state: GraphState) -> dict:
    logger.info("parse_documents: estrazione testo dai PDF")
    raw_invoice = extract_text_from_pdf(state["invoice_pdf_bytes"], label="Fattura")
    raw_contract = extract_text_from_pdf(state["contract_pdf_bytes"], label="Contratto")
    logger.info(
        "parse_documents: fattura=%d car., contratto=%d car.", len(raw_invoice), len(raw_contract)
    )
    return {
        "raw_invoice_text": raw_invoice,
        "raw_contract_text": raw_contract,
    }


async def extract_invoice(state: GraphState) -> dict:
    logger.info("extract_invoice: estrazione dati fattura")
    llm = _get_llm()
    try:
        invoice = await llm.structured_completion(
            system_prompt=EXTRACT_INVOICE_SYSTEM,
            user_message=state["raw_invoice_text"],
            output_schema=Invoice,
        )
        logger.info("extract_invoice: %s (%d righe)", invoice.invoice_id, len(invoice.lines))
        return {"parsed_invoice": invoice}
    except LLMProviderError as e:
        logger.error("extract_invoice: errore: %s", e)
        return {"invoice_extraction_error": str(e)}


async def extract_contract(state: GraphState) -> dict:
    logger.info("extract_contract: estrazione clausole contratto")
    llm = _get_llm()
    try:
        contract = await llm.structured_completion(
            system_prompt=EXTRACT_CONTRACT_SYSTEM,
            user_message=state["raw_contract_text"],
            output_schema=ContractTerms,
        )
        logger.info(
            "extract_contract: %s (%d regole)", contract.contract_id, len(contract.pricing_rules)
        )
        return {"parsed_contract": contract}
    except LLMProviderError as e:
        logger.error("extract_contract: errore: %s", e)
        return {"contract_extraction_error": str(e)}


_SEVERITY_HIGH_EUR = 2000.0
_SEVERITY_MEDIUM_EUR = 500.0


def _classify_severity(delta: float, reference_amount: float) -> str:
    abs_delta = abs(delta)
    pct = (abs_delta / reference_amount * 100) if reference_amount > 0 else 0
    if abs_delta > _SEVERITY_HIGH_EUR or pct > 15:
        return "high"
    if abs_delta > _SEVERITY_MEDIUM_EUR or pct > 5:
        return "medium"
    return "low"


def _match_service_score(invoice_desc: str, contract_service: str) -> float:
    a = invoice_desc.lower().strip()
    b = contract_service.lower().strip()
    if a == b:
        return 1.0
    if b in a or a in b:
        return 0.8
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / max(len(words_a), len(words_b))


def _find_pricing_rule(
    line_desc: str, rules: list[ContractPricingRule]
) -> ContractPricingRule | None:
    best_score = 0.0
    best_rule = None
    for rule in rules:
        score = _match_service_score(line_desc, rule.service_type)
        if score > best_score and score >= 0.4:
            best_score = score
            best_rule = rule
    return best_rule


def deterministic_match(state: GraphState) -> dict:
    logger.info("deterministic_match: verifica matematica e contrattuale")
    invoice: Invoice | None = state.get("parsed_invoice")
    contract: ContractTerms | None = state.get("parsed_contract")

    if not invoice or not contract:
        logger.warning("deterministic_match: fattura o contratto assenti, skip")
        return {"raw_discrepancies": []}

    discrepancies: list[Discrepancy] = []

    for line in invoice.lines:
        expected_line_total = round(line.quantity * line.unit_price, 2)
        if abs(line.total_price - expected_line_total) > 0.01:
            delta = line.total_price - expected_line_total
            discrepancies.append(
                Discrepancy(
                    field_name=f"line_total:{line.description}",
                    invoice_value=f"{line.total_price:.2f}",
                    expected_value=f"{expected_line_total:.2f}",
                    delta=delta,
                    severity=_classify_severity(delta, expected_line_total),
                    is_justified_by_contract=False,
                    reasoning=(
                        f"Errore di calcolo nella riga: {line.quantity} x {line.unit_price:.2f} "
                        f"= {expected_line_total:.2f}, riportato {line.total_price:.2f}"
                    ),
                )
            )

    line_sum = round(sum(line.total_price for line in invoice.lines), 2)
    if abs(invoice.subtotal - line_sum) > 0.01:
        delta = invoice.subtotal - line_sum
        discrepancies.append(
            Discrepancy(
                field_name="subtotal",
                invoice_value=f"{invoice.subtotal:.2f}",
                expected_value=f"{line_sum:.2f}",
                delta=delta,
                severity=_classify_severity(delta, line_sum),
                is_justified_by_contract=False,
                reasoning=(
                    f"Subtotale indicato ({invoice.subtotal:.2f}) non corrispondente "
                    f"alla somma righe ({line_sum:.2f})"
                ),
            )
        )

    if invoice.tax_amount is not None:
        expected_total = round(invoice.subtotal + invoice.tax_amount, 2)
        if abs(invoice.total_amount - expected_total) > 0.01:
            delta = invoice.total_amount - expected_total
            discrepancies.append(
                Discrepancy(
                    field_name="total_amount",
                    invoice_value=f"{invoice.total_amount:.2f}",
                    expected_value=f"{expected_total:.2f}",
                    delta=delta,
                    severity=_classify_severity(delta, expected_total),
                    is_justified_by_contract=False,
                    reasoning=(
                        f"Totale dichiarato ({invoice.total_amount:.2f}) non corrispondente "
                        f"a imponibile ({invoice.subtotal:.2f}) + IVA ({invoice.tax_amount:.2f})"
                    ),
                )
            )

    for line in invoice.lines:
        rule = _find_pricing_rule(line.description, contract.pricing_rules)
        if rule and line.unit_price > rule.max_unit_price:
            delta_unit = line.unit_price - rule.max_unit_price
            total_overcharge = round(delta_unit * line.quantity, 2)
            discrepancies.append(
                Discrepancy(
                    field_name=f"unit_price:{line.description}",
                    invoice_value=f"{line.unit_price:.2f}",
                    expected_value=f"<= {rule.max_unit_price:.2f} ({rule.unit})",
                    delta=total_overcharge,
                    severity=_classify_severity(total_overcharge, rule.max_unit_price),
                    is_justified_by_contract=False,
                    reasoning=(
                        f"Tariffa applicata ({line.unit_price:.2f}/{rule.unit}) superiore al massimale "
                        f"({rule.max_unit_price:.2f}/{rule.unit}) per '{rule.service_type}'. "
                        f"Sovrapprezzo: {total_overcharge:.2f}"
                    ),
                )
            )

    if (
        invoice.payment_terms_days is not None
        and invoice.payment_terms_days < contract.payment_terms_days
    ):
        discrepancies.append(
            Discrepancy(
                field_name="payment_terms_days",
                invoice_value=f"{invoice.payment_terms_days} giorni",
                expected_value=f">= {contract.payment_terms_days} giorni",
                delta=None,
                severity="medium",
                is_justified_by_contract=False,
                reasoning=(
                    f"Termini in fattura ({invoice.payment_terms_days} giorni) piu restrittivi "
                    f"dei {contract.payment_terms_days} giorni pattuiti"
                ),
            )
        )

    logger.info("deterministic_match: %d discrepanze", len(discrepancies))
    return {"raw_discrepancies": discrepancies}


async def llm_contract_reasoning(state: GraphState) -> dict:
    logger.info("llm_contract_reasoning: valutazione discrepanze")
    llm = _get_llm()
    raw = state.get("raw_discrepancies", [])
    contract = state.get("parsed_contract")

    disc_lines = [
        f"- {d.field_name}: fattura={d.invoice_value}, atteso={d.expected_value}, "
        f"delta={d.delta}, motivo={d.reasoning}"
        for d in raw
    ]
    contract_json = contract.model_dump_json(indent=2) if contract else "{}"
    user_msg = (
        f"DISCREPANZE DA ANALIZZARE:\n{chr(10).join(disc_lines)}\n\n"
        f"CONTRATTO QUADRO:\n{contract_json}"
    )

    try:
        analysis = await llm.structured_completion(
            system_prompt=LLM_REASONING_SYSTEM,
            user_message=user_msg,
            output_schema=ContractReasoningOutput,
        )
        analysis_map = {a.field_name: a for a in analysis.analyses}
        analyzed: list[Discrepancy] = []
        for d in raw:
            match = analysis_map.get(d.field_name)
            if match:
                analyzed.append(
                    d.model_copy(
                        update={
                            "is_justified_by_contract": match.verdict == "JUSTIFIED",
                            "reasoning": match.reasoning,
                        }
                    )
                )
            else:
                analyzed.append(d)
        unjustified = sum(1 for d in analyzed if not d.is_justified_by_contract)
        logger.info("llm_contract_reasoning: %d ingiustificate su %d", unjustified, len(analyzed))
        return {"analyzed_discrepancies": analyzed}
    except LLMProviderError as e:
        logger.error("llm_contract_reasoning: errore: %s", e)
        return {"analyzed_discrepancies": raw}


async def generate_dispute_report(state: GraphState) -> dict:
    logger.info("generate_dispute_report: composizione report")
    invoice = state.get("parsed_invoice")
    contract = state.get("parsed_contract")

    inv_error = state.get("invoice_extraction_error")
    ctr_error = state.get("contract_extraction_error")
    if inv_error or ctr_error:
        errors = [f"Fattura: {inv_error}"] if inv_error else []
        if ctr_error:
            errors.append(f"Contratto: {ctr_error}")
        report = FinalReport(
            status="APPROVED",
            invoice_id=invoice.invoice_id if invoice else "NON_DISPONIBILE",
            contract_id=contract.contract_id if contract else "NON_DISPONIBILE",
            analysis_summary=f"Analisi incompleta a causa di errori: {'; '.join(errors)}",
            discrepancies=[],
            total_overbilling=0.0,
            dispute_email_draft=None,
        )
        return {"final_report": report}

    all_discrepancies = state.get("analyzed_discrepancies", state.get("raw_discrepancies", []))
    unjustified = [d for d in all_discrepancies if not d.is_justified_by_contract]
    total_overbilling = round(sum(d.delta for d in unjustified if d.delta and d.delta > 0), 2)
    status = "DISCREPANCIES_FOUND" if unjustified else "APPROVED"

    if unjustified:
        summary = (
            f"Audit completato. {len(all_discrepancies)} discrepanze totali, "
            f"di cui {len(unjustified)} ingiustificate per {total_overbilling:,.2f} EUR recuperabili."
        )
    else:
        summary = (
            "Audit completato. Nessuna discrepanza rilevata. "
            "La fattura risulta conforme al contratto."
        )

    email_draft: str | None = None
    if unjustified and invoice and contract:
        try:
            llm = _get_llm()
            disc_text = "\n".join(
                f"- {d.field_name}: fatturato={d.invoice_value}, atteso={d.expected_value}, sovrapprezzo={d.delta}"
                for d in unjustified
            )
            user_msg = (
                f"FATTURA: {invoice.invoice_id} del {invoice.invoice_date}\n"
                f"FORNITORE: {invoice.vendor_name}\n"
                f"CONTRATTO QUADRO: {contract.contract_id}\n"
                f"TOTALE SOVRAFATTURATO: {total_overbilling:,.2f}\n\n"
                f"ANOMALIE CONFERMATE:\n{disc_text}"
            )
            email = await llm.structured_completion(
                system_prompt=GENERATE_DISPUTE_EMAIL_SYSTEM,
                user_message=user_msg,
                output_schema=DisputeEmailDraft,
            )
            email_draft = f"Oggetto: {email.subject}\n\n{email.body}"
        except LLMProviderError as e:
            logger.error("generate_dispute_report: errore email: %s", e)
            email_draft = "[Bozza email non generata per errore del servizio LLM]"

    report = FinalReport(
        status=status,
        invoice_id=invoice.invoice_id if invoice else "N/D",
        contract_id=contract.contract_id if contract else "N/D",
        analysis_summary=summary,
        discrepancies=unjustified,
        total_overbilling=total_overbilling,
        dispute_email_draft=email_draft,
    )
    logger.info("generate_dispute_report: stato=%s overbilling=%.2f", status, total_overbilling)
    return {"final_report": report}
