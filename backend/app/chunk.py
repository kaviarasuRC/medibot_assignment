"""The internal chunk type.

A thin, Qdrant-free value object. Generation and reranking take `Chunk`s rather
than `ScoredPoint`s so they can be unit-tested with hand-built fixtures and no
running vector store.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Chunk:
    text: str
    source_document: str
    collection: str
    section_title: str
    chunk_type: str
    access_roles: tuple[str, ...] = ()
    retrieval_score: float = 0.0
    hybrid_rank: int = 0

    @classmethod
    def from_point(cls, point, hybrid_rank: int = 0) -> "Chunk":
        payload = point.payload or {}
        return cls(
            text=payload.get("text", ""),
            source_document=payload.get("source_document", ""),
            collection=payload.get("collection", ""),
            section_title=payload.get("section_title", ""),
            chunk_type=payload.get("chunk_type", "text"),
            access_roles=tuple(payload.get("access_roles", ())),
            retrieval_score=float(getattr(point, "score", 0.0) or 0.0),
            hybrid_rank=hybrid_rank,
        )

    @property
    def citation(self) -> str:
        return f"{self.source_document} — {self.section_title}" if self.section_title else self.source_document
