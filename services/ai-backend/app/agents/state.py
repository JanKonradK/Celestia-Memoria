"""Agent state definition for the RAG agent graph."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State object passed between nodes in the agent graph.

    Attributes:
        messages: Conversation message history (LangChain format).
        intent: Classified query intent from the router node.
        requires_rag: Whether the query needs document retrieval.
        query_rewrite: Optimized query for retrieval (from router).
        retrieved_chunks: Raw retrieval results before reranking.
        reranked_chunks: Final chunks after reranking.
        final_response: The synthesized answer text.
        sources: Parsed source references from the response.
        node_trace: Ordered list of nodes executed.
        model_slug: LLM model identifier to use for synthesis.
        aerodrome_icao: Target aerodrome for filtering retrieval.
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
    intent: str
    requires_rag: bool
    query_rewrite: str
    retrieved_chunks: list[dict]
    reranked_chunks: list[dict]
    final_response: str
    sources: list[dict]
    node_trace: list[str]
    model_slug: str
    aerodrome_icao: str
