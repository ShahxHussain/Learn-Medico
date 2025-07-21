import re
from typing import List, Dict

def split_into_chapters(full_text: str) -> Dict[str, str]:
    # Split text by 'Chapter [number]' or 'Unit [number]' pattern (case-insensitive)
    chapters = {}
    matches = list(re.finditer(r'(Chapter \d+|Unit \d+)', full_text, re.IGNORECASE))
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i+1].start() if i+1 < len(matches) else len(full_text)
        chapter_title = match.group(1)
        chapters[chapter_title] = full_text[start:end].strip()
    return chapters

def chunk_text(text: str, max_tokens: int = 500, overlap: int = 50) -> List[str]:
    # Simple whitespace tokenization
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = words[i:i+max_tokens]
        chunks.append(' '.join(chunk))
        if i + max_tokens >= len(words):
            break
        i += max_tokens - overlap
    return chunks 