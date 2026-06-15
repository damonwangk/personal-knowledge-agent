from __future__ import annotations

import re

import jieba


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "by",
    "do",
    "does",
    "for",
    "how",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "with",
}

ACRONYM_EXPANSIONS = {
    "rag": "retrieval augmented generation",
}


def expand_query(query: str) -> str:
    additions: list[str] = []
    lower = query.lower()
    for acronym, expansion in ACRONYM_EXPANSIONS.items():
        if re.search(rf"\b{re.escape(acronym)}\b", lower) and expansion not in lower:
            additions.append(expansion)
    if not additions:
        return query
    return f"{query} {' '.join(additions)}"


def tokenize_query(query: str) -> list[str]:
    expanded = expand_query(query)
    return tokenize_text(expanded)


def tokenize_text(text: str) -> list[str]:
    normalized = text.lower()
    chinese_tokens = [token.strip() for token in jieba.lcut(normalized) if token.strip()]
    ascii_tokens = re.findall(r"[a-z0-9_]+", normalized)
    terms = chinese_tokens + ascii_tokens
    return [term for term in terms if len(term) > 1 and term not in STOPWORDS]
