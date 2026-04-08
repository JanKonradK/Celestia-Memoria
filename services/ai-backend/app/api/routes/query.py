"""Direct query endpoint for non-LangServe access."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from app.agents.graph import get_graph

logger = logging.getLogger(__name__)

QUERY_TIMEOUT_SECONDS = 120

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    """Request body for a direct query."""

    message: str = Field(
        description="The user's question",
        min_length=1,
        max_length=10_000,
    )
    aerodrome_icao: str = Field(
        default="GLOBAL",
        description="Target aerodrome ICAO code",
        pattern=r"^([A-Z]{4}|GLOBAL)$",
    )
    model_slug: str = Field(default="default", description="LLM model to use", max_length=100)


class SourceRef(BaseModel):
    source_index: int
    doc_name: str
    doc_type: str
    section_path: str
    page_number: int | None
    aerodrome_icao: str
    clause_id: str = ""
    cited_clause: str = ""


class QueryResponse(BaseModel):
    """Response from a direct query."""

    answer: str
    sources: list[SourceRef]
    intent: str
    node_trace: list[str]


@router.post("", response_model=QueryResponse)
async def query_documents(
    body: QueryRequest,
    request: Request,
) -> QueryResponse:
    """Execute a query through the full agent graph and return the result.

    Unlike the LangServe /chat endpoint, this returns a simple JSON response
    without streaming. Useful for programmatic access.
    """
    graph = get_graph()

    initial_state = {
        "messages": [HumanMessage(content=body.message)],
        "intent": "",
        "requires_rag": False,
        "query_rewrite": "",
        "retrieved_chunks": [],
        "reranked_chunks": [],
        "final_response": "",
        "sources": [],
        "node_trace": [],
        "model_slug": body.model_slug,
        "aerodrome_icao": body.aerodrome_icao,
    }

    try:
        result = await asyncio.wait_for(
            graph.ainvoke(initial_state),
            timeout=QUERY_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        logger.error("Query timed out after %ds: %s", QUERY_TIMEOUT_SECONDS, body.message[:100])
        raise HTTPException(
            status_code=504, detail="Query timed out. Please try a simpler question.",
        )
    except Exception as e:
        logger.error("Query execution failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to process query")

    sources = [
        SourceRef(
            source_index=s.get("source_index", 0),
            doc_name=s.get("doc_name", ""),
            doc_type=s.get("doc_type", ""),
            section_path=s.get("section_path", ""),
            page_number=s.get("page_number"),
            aerodrome_icao=s.get("aerodrome_icao", "GLOBAL"),
            clause_id=s.get("clause_id", ""),
            cited_clause=s.get("cited_clause", ""),
        )
        for s in result.get("sources", [])
    ]

    return QueryResponse(
        answer=result.get("final_response", ""),
        sources=sources,
        intent=result.get("intent", ""),
        node_trace=result.get("node_trace", []),
    )
