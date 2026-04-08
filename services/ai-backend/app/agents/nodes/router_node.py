"""Router node: classifies query intent and rewrites for optimal retrieval."""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from app.agents.state import AgentState
from app.llm.openrouter import get_llm

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """You are an intent classifier for Celestia Memoria, an aviation regulatory
document assistant used by air traffic controllers. Your job is to analyze the user's query and:

1. Classify the intent into one of three categories:
   - "regulation_lookup": Questions about specific regulations, rules, standards, or procedures
     from official aviation documents (ICAO, EASA, AIPs, NOTAMs, etc.)
   - "procedure_check": Questions about operational procedures, separation minima, techniques,
     or aerodrome-specific operations
   - "general": General questions, greetings, clarifications, or topics that don't require
     searching regulatory documents

2. Decide whether RAG (document retrieval) is needed:
   - Set requires_rag=true for regulation_lookup and procedure_check
   - Set requires_rag=false for general queries

3. Rewrite the query to be optimal for semantic search over aviation documents:
   - If the user mentions a specific clause number (e.g., "4.6.1", "ENR 1.1"), preserve it
     verbatim in the rewrite and add surrounding context
   - Expand abbreviations with both forms (e.g., "RVR" -> "Runway Visual Range (RVR)")
   - If a specific document is mentioned, include its full title:
     Doc 4444 = "Procedures for Air Navigation Services — Air Traffic Management (PANS-ATM)"
     Doc 7030 = "Regional Supplementary Procedures"
   - Add relevant context terms
   - Make the query self-contained (don't rely on conversation history)
   - Keep it concise but specific

Respond with a JSON object matching the RouterOutput schema."""


class RouterOutput(BaseModel):
    """Structured output from the router node."""

    intent: str = Field(
        description="Query intent: 'regulation_lookup', 'procedure_check', or 'general'"
    )
    requires_rag: bool = Field(
        description="Whether document retrieval is needed to answer this query"
    )
    query_rewrite: str = Field(
        description="Rewritten query optimized for semantic search over aviation documents"
    )


async def router_node(state: AgentState) -> dict:
    """Classify the user's query intent and rewrite it for retrieval.

    Uses a fast, cheap model (e.g., Gemini Flash) for low-latency classification.
    """
    messages = state.get("messages", [])
    if not messages:
        return {
            "intent": "general",
            "requires_rag": False,
            "query_rewrite": "",
            "node_trace": state.get("node_trace", []) + ["router"],
        }

    # Get the last user message
    last_message = messages[-1]
    user_query = (
        last_message.content
        if hasattr(last_message, "content")
        else str(last_message)
    )

    llm = get_llm("router")
    structured_llm = llm.with_structured_output(RouterOutput)

    try:
        result: RouterOutput = await structured_llm.ainvoke(
            [
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": user_query},
            ]
        )

        logger.info(
            "Router: intent=%s, requires_rag=%s, rewrite='%s'",
            result.intent,
            result.requires_rag,
            result.query_rewrite[:100],
        )

        return {
            "intent": result.intent,
            "requires_rag": result.requires_rag,
            "query_rewrite": result.query_rewrite,
            "node_trace": state.get("node_trace", []) + ["router"],
        }

    except Exception as e:
        logger.warning("Router failed, defaulting to RAG: %s", e)
        return {
            "intent": "regulation_lookup",
            "requires_rag": True,
            "query_rewrite": user_query,
            "node_trace": state.get("node_trace", []) + ["router"],
        }
