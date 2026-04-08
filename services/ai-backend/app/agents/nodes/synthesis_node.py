"""Synthesis node: generates the final answer with source citations."""

from __future__ import annotations

import logging
import re

from langchain_core.messages import AIMessage

from app.agents.state import AgentState
from app.llm.openrouter import get_llm

logger = logging.getLogger(__name__)

SYNTHESIS_SYSTEM_PROMPT = """\
You are Celestia Memoria, an AI assistant for air traffic controllers. You help them find \
and understand aviation regulatory information from ICAO documents, EASA regulations, AIPs, \
unit manuals, and other official aviation publications.

## STRICT GROUNDING RULES

1. You MUST ONLY use information from the Retrieved Document Sources provided below. \
Do NOT use your general aviation knowledge to supplement or fill gaps.
2. If the sources do not contain the answer, state this clearly. Never invent or guess \
regulatory requirements.

## CITATION FORMAT

1. After each factual statement, cite the source using [Source N, <clause>] where <clause> \
is the specific clause or section identifier shown in the source header (e.g., \
[Source 1, 4.6.1.2] or [Source 3, ENR 1.1]).
2. If no clause identifier is shown for a source, use [Source N] alone.
3. For critical regulatory values (minima, distances, altitudes, frequencies), quote the \
exact source text in quotation marks, then cite. \
Example: "The vertical separation minimum shall be 1000 ft below FL 410" [Source 2, 3.1.2]

## WHEN INFORMATION IS NOT FOUND

If the retrieved sources do not contain information relevant to the query:
- State: "I could not find information about [topic] in the available documents."
- Do NOT fall back to general knowledge.
- Suggest the user verify the document has been indexed or rephrase their query.

## OUT-OF-SCOPE QUERIES

If the query is not about aviation regulations, procedures, or standards:
- State: "This question is outside the scope of aviation regulatory documents. \
I can only assist with questions about aviation regulations, procedures, and standards."

## PARTIAL ANSWERS

If sources only partially answer the query:
- Provide the information you CAN cite from sources.
- Explicitly state what aspects are NOT covered: "The available sources address X \
[Source N], but do not contain information about Y."

## STYLE

- Be concise. Controllers need fast, accurate answers during operations.
- State cited information authoritatively. Do not add unnecessary hedging to properly sourced facts.
- Never reproduce entire document sections verbatim — summarize and cite."""

SOURCE_PATTERN = re.compile(r"\[Source\s+(\d+)(?:,\s*([^\]]+))?\]")


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

        clause_id = chunk.get("clause_id", "")

        header = f"[Source {i}] {doc_name}"
        if section:
            header += f" — {section}"
        if clause_id:
            header += f" (Clause {clause_id})"
        if page is not None:
            header += f" (p. {page})"

        context_parts.append(f"{header}\n{text}")

    return "\n\n---\n\n".join(context_parts)


def _parse_sources(response_text: str, chunks: list[dict]) -> list[dict]:
    """Extract [Source N] and [Source N, clause] references from the response.

    Maps each reference back to chunk metadata. Supports both formats:
    - [Source 1] — basic source reference
    - [Source 1, 4.6.1.2] — source with specific clause citation
    """
    seen_indices: set[int] = set()
    sources: list[dict] = []

    for match in SOURCE_PATTERN.finditer(response_text):
        idx = int(match.group(1)) - 1  # Convert to 0-indexed
        cited_clause = (match.group(2) or "").strip()

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
            "clause_id": chunk.get("clause_id", ""),
            "cited_clause": cited_clause,
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

Answer the user's query using ONLY the document sources above. Cite specific clause numbers \
where shown. Quote exact text for numerical values. If the sources do not answer the query, \
say so clearly."""

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
        error_msg = (
            "I apologize, but I encountered an error generating a response. "
            "Please try again."
        )
        return {
            "messages": [AIMessage(content=error_msg)],
            "final_response": error_msg,
            "sources": [],
            "node_trace": state.get("node_trace", []) + ["synthesis"],
        }
