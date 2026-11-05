"""Split one turn into overlapping windows.

A short message stays whole. A report is cut so a later question can retrieve
the paragraph that contains the figure, instead of only the opening characters.
"""

CHUNK_SIZE = 480
CHUNK_OVERLAP = 80
MAX_CHUNKS = 6


def chunk_text(text: str, *, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    compact = " ".join(text.split())
    if not compact:
        return []
    if len(compact) <= size:
        return [compact]
    chunks: list[str] = []
    start = 0
    while start < len(compact) and len(chunks) < MAX_CHUNKS:
        end = min(start + size, len(compact))
        if end < len(compact):
            space = compact.rfind(" ", start + size // 2, end)
            if space > start:
                end = space
        piece = compact[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(compact):
            break
        next_start = end - overlap
        start = end if next_start <= start else next_start
    return chunks
