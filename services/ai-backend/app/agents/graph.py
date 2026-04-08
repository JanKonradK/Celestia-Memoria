"""LangGraph agent graph: router -> (conditional) -> retrieval -> synthesis."""

from __future__ import annotations

import logging

from langgraph.graph import END, StateGraph

from app.agents.nodes.retrieval_node import retrieval_node
from app.agents.nodes.router_node import router_node
from app.agents.nodes.synthesis_node import synthesis_node
from app.agents.state import AgentState

logger = logging.getLogger(__name__)


def after_router(state: AgentState) -> str:
    """Conditional edge: decide whether to retrieve or go straight to synthesis.

    If the router determined the query needs RAG, route to retrieval.
    Otherwise, go directly to synthesis (for general queries like greetings).
    """
    if state.get("requires_rag", False):
        return "retrieval"
    return "synthesis"


def build_graph() -> StateGraph:
    """Build and compile the agent graph.

    Graph structure:
        router -> [conditional] -> retrieval -> synthesis -> END
                              |                            ^
                              +----> synthesis -------------+
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("router", router_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("synthesis", synthesis_node)

    # Set entry point
    graph.set_entry_point("router")

    # Add conditional edge from router
    graph.add_conditional_edges(
        "router",
        after_router,
        {
            "retrieval": "retrieval",
            "synthesis": "synthesis",
        },
    )

    # Retrieval always leads to synthesis
    graph.add_edge("retrieval", "synthesis")

    # Synthesis is the final node
    graph.add_edge("synthesis", END)

    return graph.compile()


# Singleton compiled graph
_compiled_graph = None


def get_graph():
    """Get the singleton compiled agent graph."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
        logger.info("Agent graph compiled successfully")
    return _compiled_graph
