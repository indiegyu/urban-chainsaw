def is_relevant(text: str, exclude_words: list[str]) -> bool:
    """Return False if any exclude word appears in text (case-insensitive)."""
    if not exclude_words:
        return True
    lower = text.lower()
    return not any(w.lower() in lower for w in exclude_words)
