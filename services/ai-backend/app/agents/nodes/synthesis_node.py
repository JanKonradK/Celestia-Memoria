"""Synthesis node: generates the final answer with source citations."""

from __future__ import annotations

import logging
import re

from langchain_core.messages import AIMessage

from app.agents.state import AgentState
from app.llm.openrouter import get_llm

logger = logging.getLogger(__name__)

SYNTHESIS_SYSTEM_PROMPT = """You are Celestia Memoria, an AI assistant for air traffic controllers.
You help them quickly find and understand aviation regulatory information from ICAO documents,
EASA regulations, AIPs, unit manuals, and other official aviation publications.

You have been provided with relevant document excerpts below. Follow these rules strictly:

1. **Always cite sources** using [Source N] notation when referencing specific information.
   Place the citation immediately after the relevant statement.
2. **Never reproduce entire sections** verbatim — summarize and reference.
3. **State clearly when information is not found** in the provided sources. Say "I could not find
   this information in the available documents" rather than guessing.
4. **Never fabricate regulatory requirements.** If you're unsure, say so.
5. **Be concise** — controllers need fast, accurate answers during operations.
6. **Include source citations for specific values** like minima, distances, altitudes, frequencies.

If no relevant sources were found, answer based on your general knowledge but clearly indicate
that the answer is not from the indexed documents."""

SOURCE_PATTERN = re.compile(r"\[Source\s+(\d+)\]")


def _build_context(chunks: list[dict]) -> str:
    """Build a numbered context string from reranked chunks."""
    if not chunks:
        return "No relevant document sources were found for this query."

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        doc_name = chunk.get("doc_name", "Unknown Document")
        section = chunk.get("section_path", "")
        page = chunk.get("page_number")
        text = chunk.get("chunk_text", "")

        header = f"[Source {i}] {doc_name}"
        if section:
            header += f" — {section}"
        if page is not None:
            header += f" (p. {page})"

        context_parts.append(f"{header}\n{text}")

    return "\n\n---\n\n".join(context_parts)


def _parse_sources(response_text: str, chunks: list[dict]) -> list[dict]:
    """Extract [Source N] references from the response and map to chunk metadata."""
    matches = SOURCE_PATTERN.findall(response_text)
    seen_indices = set()
    sources = []

    for match in matches:
        idx = int(match) - 1  # Convert to 0-indexed
        if idx < 0 or idx >= len(chunks) or idx in seen_indices:
            continue
        seen_indices.add(idx)

        chunk = chunks[idx]
        sources.append({
            "source_index": idx + 1,
            "doc_name": chunk.get("doc_name", ""),
            "doc_type": chunk.get("doc_type", ""),
            "section_path": chunk.get("section_path", ""),
            "page_number": chunk.get("page_number"),
            "chunk_text": chunk.get("chunk_text", "")[:500],
            "aerodrome_icao": chunk.get("aerodrome_icao", "GLOBAL"),
        })

    return sources


async def synthesis_node(state: AgentState) -> dict:
    """Generate the final response using retrieved context and LLM.

    Builds context from reranked chunks, invokes the synthesis LLM with
    citation-disciplined system prompt, and parses source references.
    """
    messages = state.get("messages", [])
    chunks = state.get("reranked_chunks", [])
    model_slug = state.get("model_slug", "default")

    # Build context from retrieved chunks
    context = _build_context(chunks)

    # Get the user's original query
    user_query = ""
    if messages:
        last = messages[-1]
        user_query = last.content if hasattr(last, "content") else str(last)

    # Construct the full prompt
    full_prompt = f"""## Retrieved Document Sources

{context}

## User Query

{user_query}

Please answer the user's query based on the document sources above. Remember to cite sources
using [Source N] notation."""

    llm = get_llm(model_slug)

    try:
        response = await llm.ainvoke(
            [
                {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                {"role": "user", "content": full_prompt},
            ]
        )

        response_text = response.content
        sources = _parse_sources(response_text, chunks)

        logger.info(
            "Synthesis: %d chars, %d sources cited",
            len(response_text),
            len(sources),
        )

        return {
            "messages": [AIMessage(content=response_text)],
            "final_response": response_text,
            "sources": sources,
            "node_trace": state.get("node_trace", []) + ["synthesis"],
        }

    except Exception as e:
        logger.exception("Synthesis failed: %s", e)
        error_msg = "I apologize, but I encountered an error generating a response. Please try again."
        return {
            "messages": [AIMessage(content=error_msg)],
            "final_response": error_msg,
            "sources": [],
            "node_trace": state.get("node_trace", []) + ["synthesis"],
        }
