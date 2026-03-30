"""Heading-aware markdown chunking with token counting via tiktoken."""

from __future__ import annotations

import re
import logging

import tiktoken

logger = logging.getLogger(__name__)

_encoder = tiktoken.get_encoding("cl100k_base")

HEADING_PATTERN = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
SENTENCE_END_PATTERN = re.compile(r"[.!?]\s+(?=[A-Z])")


def count_tokens(text: str) -> int:
    """Count tokens in text using cl100k_base encoding."""
    return len(_encoder.encode(text))


def _get_last_sentence(text: str, max_tokens: int = 200) -> str:
    """Extract the last complete sentence from text for overlap.

    Returns up to max_tokens worth of the last sentence(s).
    """
    sentences = SENTENCE_END_PATTERN.split(text)
    if len(sentences) <= 1:
        # No sentence boundary found, return last portion
        tokens = _encoder.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return _encoder.decode(tokens[-max_tokens:])

    # Take the last sentence
    last = sentences[-1].strip()
    if count_tokens(last) <= max_tokens:
        return last
    tokens = _encoder.encode(last)
    return _encoder.decode(tokens[-max_tokens:])


def _split_at_headings(markdown: str) -> list[dict]:
    """Split markdown into sections based on headings.

    Returns a list of dicts with 'heading', 'level', 'content', and 'section_path'.
    """
    sections: list[dict] = []
    heading_stack: list[str] = []

    # Split at heading boundaries
    parts = HEADING_PATTERN.split(markdown)

    # parts alternates: [pre-heading-text, #level, heading-text, content, #level, ...]
    if parts[0].strip():
        sections.append({
            "heading": "",
            "level": 0,
            "content": parts[0].strip(),
            "section_path": "",
        })

    i = 1
    while i < len(parts) - 2:
        level = len(parts[i])  # Number of # characters
        heading = parts[i + 1].strip()
        content = parts[i + 2].strip() if i + 2 < len(parts) else ""

        # Update heading stack for section path
        while len(heading_stack) >= level:
            heading_stack.pop()
        heading_stack.append(heading)

        section_path = " > ".join(heading_stack)

        sections.append({
            "heading": heading,
            "level": level,
            "content": f"{'#' * level} {heading}\n\n{content}" if content else f"{'#' * level} {heading}",
            "section_path": section_path,
        })
        i += 3

    return sections if sections else [{"heading": "", "level": 0, "content": markdown, "section_path": ""}]


def chunk_markdown(
    markdown: str,
    metadata: dict,
    target_tokens: int = 800,
    min_tokens: int = 100,
    overlap_tokens: int = 100,
) -> list[dict]:
    """Split markdown into chunks respecting heading boundaries.

    Each chunk carries metadata including section_path and chunk_index.

    Args:
        markdown: The full markdown text to chunk.
        metadata: Base metadata dict to merge into each chunk.
        target_tokens: Target size for each chunk in tokens.
        min_tokens: Minimum chunk size; smaller sections merge with neighbors.
        overlap_tokens: Number of overlap tokens between consecutive chunks.

    Returns:
        List of chunk dicts with keys: chunk_text, section_path, chunk_index,
        token_count, plus all keys from metadata.
    """
    sections = _split_at_headings(markdown)
    chunks: list[dict] = []
    chunk_index = 0
    current_text = ""
    current_section_path = ""
    overlap_text = ""

    for section in sections:
        section_text = section["content"]
        section_tokens = count_tokens(section_text)
        section_path = section["section_path"]

        if section_tokens > target_tokens:
            # Section is too large — flush current buffer and split the section
            if current_text.strip():
                token_count = count_tokens(current_text)
                if token_count >= min_tokens:
                    chunks.append({
                        **metadata,
                        "chunk_text": current_text.strip(),
                        "section_path": current_section_path,
                        "chunk_index": chunk_index,
                        "token_count": token_count,
                    })
                    overlap_text = _get_last_sentence(current_text, overlap_tokens)
                    chunk_index += 1
                current_text = ""

            # Split large section by paragraphs
            paragraphs = section_text.split("\n\n")
            buffer = overlap_text

            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                test_text = f"{buffer}\n\n{para}" if buffer else para
                if count_tokens(test_text) > target_tokens and buffer.strip():
                    token_count = count_tokens(buffer)
                    if token_count >= min_tokens:
                        chunks.append({
                            **metadata,
                            "chunk_text": buffer.strip(),
                            "section_path": section_path,
                            "chunk_index": chunk_index,
                            "token_count": token_count,
                        })
                        overlap_text = _get_last_sentence(buffer, overlap_tokens)
                        chunk_index += 1
                    buffer = f"{overlap_text}\n\n{para}" if overlap_text else para
                else:
                    buffer = test_text

            current_text = buffer
            current_section_path = section_path
        else:
            # Section fits — try to merge with current buffer
            test_text = f"{current_text}\n\n{section_text}" if current_text else section_text
            if count_tokens(test_text) > target_tokens and current_text.strip():
                token_count = count_tokens(current_text)
                if token_count >= min_tokens:
                    chunks.append({
                        **metadata,
                        "chunk_text": current_text.strip(),
                        "section_path": current_section_path,
                        "chunk_index": chunk_index,
                        "token_count": token_count,
                    })
                    overlap_text = _get_last_sentence(current_text, overlap_tokens)
                    chunk_index += 1
                current_text = f"{overlap_text}\n\n{section_text}" if overlap_text else section_text
                current_section_path = section_path
            else:
                current_text = test_text
                if not current_section_path:
                    current_section_path = section_path

    # Flush remaining buffer
    if current_text.strip():
        token_count = count_tokens(current_text)
        if token_count >= min_tokens or not chunks:
            chunks.append({
                **metadata,
                "chunk_text": current_text.strip(),
                "section_path": current_section_path,
                "chunk_index": chunk_index,
                "token_count": token_count,
            })
        elif chunks:
            # Merge tiny trailing chunk into last chunk
            last = chunks[-1]
            last["chunk_text"] = f"{last['chunk_text']}\n\n{current_text.strip()}"
            last["token_count"] = count_tokens(last["chunk_text"])

    logger.info(
        "Chunked document into %d chunks (target=%d tokens)",
        len(chunks),
        target_tokens,
    )
    return chunks
