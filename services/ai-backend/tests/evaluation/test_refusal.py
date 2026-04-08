"""Tests for refusal behavior: out-of-scope queries and missing source handling."""

from __future__ import annotations

from app.agents.nodes.synthesis_node import (
    SYNTHESIS_SYSTEM_PROMPT,
    _build_context,
)

# ---------------------------------------------------------------------------
# Refusal prompt instructions
# ---------------------------------------------------------------------------


class TestRefusalPrompt:
    """Verify synthesis prompt has clear refusal instructions."""

    def test_prompt_has_not_found_instructions(self):
        assert "could not find" in SYNTHESIS_SYSTEM_PROMPT.lower()

    def test_prompt_has_out_of_scope_instructions(self):
        assert "outside the scope" in SYNTHESIS_SYSTEM_PROMPT

    def test_prompt_has_partial_answer_instructions(self):
        assert "do not contain information about" in SYNTHESIS_SYSTEM_PROMPT.lower() or \
               "NOT covered" in SYNTHESIS_SYSTEM_PROMPT

    def test_prompt_forbids_fabrication(self):
        assert "Never invent" in SYNTHESIS_SYSTEM_PROMPT or \
               "never invent" in SYNTHESIS_SYSTEM_PROMPT.lower()

    def test_prompt_suggests_rephrase(self):
        assert "rephrase" in SYNTHESIS_SYSTEM_PROMPT.lower()


# ---------------------------------------------------------------------------
# No-chunks context
# ---------------------------------------------------------------------------


class TestSynthesisWithNoChunks:
    """Test synthesis behavior when no chunks are retrieved."""

    def test_no_chunks_context_message(self):
        context = _build_context([])
        assert "No relevant document sources" in context
        assert "[Source" not in context

    def test_no_chunks_context_is_informative(self):
        context = _build_context([])
        # Should guide the LLM to refuse/state unavailability
        assert "found" in context.lower() or "no" in context.lower()
