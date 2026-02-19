"""
Anti-duplication guard.
Uses SHA-256 content hashing + semantic similarity fingerprinting
to prevent publishing duplicate or near-duplicate content.
"""
import hashlib
import re
from typing import Optional

from memory.repository import Repository


def _normalize(text: str) -> str:
    """Normalize text for comparison: lowercase, strip punctuation and extra whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _hash(text: str) -> str:
    return hashlib.sha256(_normalize(text).encode("utf-8")).hexdigest()


def _shingle(text: str, k: int = 3) -> set[str]:
    """Create k-word shingles for Jaccard similarity."""
    words = _normalize(text).split()
    return {" ".join(words[i:i+k]) for i in range(len(words) - k + 1)}


def jaccard_similarity(a: str, b: str, k: int = 3) -> float:
    shingles_a = _shingle(a, k)
    shingles_b = _shingle(b, k)
    if not shingles_a or not shingles_b:
        return 0.0
    intersection = shingles_a & shingles_b
    union = shingles_a | shingles_b
    return len(intersection) / len(union)


class DeduplicationGuard:
    SIMILARITY_THRESHOLD = 0.45  # Posts with >45% overlap are considered duplicates

    def __init__(self, repo: Repository):
        self._repo = repo
        self._session_hashes: set[str] = set()    # In-session dedup (before DB flush)
        self._session_texts: list[str] = []

    def compute_hash(self, text: str) -> str:
        return _hash(text)

    async def is_duplicate(self, text: str) -> tuple[bool, str]:
        """
        Returns (is_duplicate, reason).
        Checks exact hash match first, then semantic similarity.
        """
        content_hash = _hash(text)

        # Check in-session hashes first (fast path)
        if content_hash in self._session_hashes:
            return True, "exact_hash_session"

        # Check DB for exact hash
        existing = await self._repo.get_post_by_hash(content_hash)
        if existing:
            return True, f"exact_hash_db:{existing.id}"

        # Check semantic similarity against recent session texts
        for prev_text in self._session_texts[-50:]:  # check last 50
            sim = jaccard_similarity(text, prev_text)
            if sim >= self.SIMILARITY_THRESHOLD:
                return True, f"semantic_similarity:{sim:.2f}"

        return False, ""

    def register(self, text: str) -> str:
        """Register a text as used. Returns the content hash."""
        content_hash = _hash(text)
        self._session_hashes.add(content_hash)
        self._session_texts.append(text)
        return content_hash

    def clear_session(self) -> None:
        self._session_hashes.clear()
        self._session_texts.clear()
