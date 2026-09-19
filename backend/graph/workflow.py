from __future__ import annotations

import logging

from langgraph.graph import END, StateGraph

from graph.nodes import (
    deterministic_match,
    extract_contract,
    extract_invoice,
    generate_dispute_report,
    llm_contract_reasoning,
    parse_documents,
)
from graph.state import GraphState

logger = logging.getLogger(__name__)


def _route_after_match(state: GraphState) -> str:
    raw_discrepancies = state.get("raw_discrepancies", [])
    if raw_discrepancies:
        logger.info("routing: %d discrepanze -> llm_contract_reasoning", len(raw_discrepancies))
        return "llm_contract_reasoning"
    logger.info("routing: 0 discrepanze -> generate_dispute_report")
    return "generate_dispute_report"


def build_workflow():
    graph = StateGraph(GraphState)

    graph.add_node("parse_documents", parse_documents)
    graph.add_node("extract_invoice", extract_invoice)
    graph.add_node("extract_contract", extract_contract)
    graph.add_node("deterministic_match", deterministic_match)
    graph.add_node("llm_contract_reasoning", llm_contract_reasoning)
    graph.add_node("generate_dispute_report", generate_dispute_report)

    graph.set_entry_point("parse_documents")
    graph.add_edge("parse_documents", "extract_invoice")
    graph.add_edge("extract_invoice", "extract_contract")
    graph.add_edge("extract_contract", "deterministic_match")

    graph.add_conditional_edges(
        "deterministic_match",
        _route_after_match,
        {
            "llm_contract_reasoning": "llm_contract_reasoning",
            "generate_dispute_report": "generate_dispute_report",
        },
    )

    graph.add_edge("llm_contract_reasoning", "generate_dispute_report")
    graph.add_edge("generate_dispute_report", END)

    logger.info("Workflow compilato.")
    return graph.compile()
