from __future__ import annotations


def truncate_text(text: str, max_chars: int, strategy: str) -> str:
    if len(text) <= max_chars:
        return text
    if strategy == "truncate_tail":
        return text[:max_chars]
    if strategy == "truncate_head":
        return text[-max_chars:]
    raise ValueError(f"Unsupported truncation strategy: {strategy}")
