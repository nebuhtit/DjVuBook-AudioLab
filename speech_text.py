"""Prepare readable speech chunks with pause durations; no TTS dependencies."""
from __future__ import annotations

import re


def _sentences(paragraph: str) -> list[str]:
    """Split after sentence punctuation, keeping a closing quote with its sentence."""
    result: list[str] = []
    start = 0
    pattern = re.compile(r"[.!?…]+(?:[»”\"'])?(?=\s+|$)")
    for match in pattern.finditer(paragraph):
        end = match.end()
        piece = paragraph[start:end].strip()
        if piece:
            result.append(piece)
        start = end
        while start < len(paragraph) and paragraph[start].isspace():
            start += 1
    tail = paragraph[start:].strip()
    if tail:
        result.append(tail)
    return result


def chunks(
    text: str,
    limit: int = 700,
    sentence_pause: float = 0.6,
    paragraph_pause: float = 1.8,
    punctuation_pause: float = 0.25,
) -> list[tuple[str, float]]:
    """Return speech fragments and silence after each, preserving punctuation."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"^\s*\|?\s*:?-{3,}.*$", " ", text, flags=re.M)
    text = re.sub(r"^\s*\d{1,4}\s*$", " ", text, flags=re.M)
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"\|", ". ", text)
    text = re.sub(r"[*_~`#]", "", text)
    text = re.sub(r"[ \t]+", " ", text).strip()
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    result: list[tuple[str, float]] = []
    clause_pattern = re.compile(r"(?<=[,;:)\]»”’\"'])\s+")

    for paragraph_index, paragraph in enumerate(paragraphs):
        sentences = _sentences(paragraph)
        for sentence_index, sentence in enumerate(sentences):
            clauses = [part.strip() for part in clause_pattern.split(sentence) if part.strip()]
            for clause_index, clause in enumerate(clauses):
                parts = []
                remainder = clause
                while len(remainder) > limit:
                    cut = remainder.rfind(" ", 0, limit)
                    if cut < limit // 2:
                        cut = limit
                    parts.append(remainder[:cut].strip())
                    remainder = remainder[cut:].strip()
                if remainder:
                    parts.append(remainder)

                for part_index, part in enumerate(parts):
                    final_part = part_index == len(parts) - 1
                    final_clause = clause_index == len(clauses) - 1
                    final_sentence = sentence_index == len(sentences) - 1
                    final_paragraph = paragraph_index == len(paragraphs) - 1
                    if not final_part:
                        pause = min(0.3, sentence_pause)
                    elif not final_clause:
                        pause = punctuation_pause
                    elif not final_sentence:
                        pause = sentence_pause
                    elif not final_paragraph:
                        pause = paragraph_pause
                    else:
                        pause = 0.0
                    result.append((part, pause))
    return result
