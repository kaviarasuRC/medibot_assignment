"""GET /collections/{role} and GET /health."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.models import CollectionsResponse, HealthResponse
from app.rbac import PermissionDenied, can_use_sql_rag, coerce_role, collections_for_role
from app.vector_store import count_points, get_client

log = logging.getLogger(__name__)

router = APIRouter(tags=["meta"])


@router.get("/collections/{role}", response_model=CollectionsResponse)
async def collections(role: str) -> CollectionsResponse:
    try:
        resolved = coerce_role(role)
    except PermissionDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown role: {role}"
        ) from exc
    return CollectionsResponse(
        role=resolved.value,
        collections=collections_for_role(resolved),
        sql_access=can_use_sql_rag(resolved),
    )


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Checking Qdrant reachability and the point count turns "why is it
    returning nothing" into a five-second diagnosis."""
    qdrant_status = "down"
    points = 0
    try:
        if get_client().collection_exists(settings.qdrant_collection):
            points = count_points()
            qdrant_status = "ok" if points else "empty"
        else:
            qdrant_status = "collection missing - run ingestion"
    except Exception as exc:  # noqa: BLE001 - health must never raise
        log.warning("Qdrant health check failed: %s", exc)
        qdrant_status = f"error: {type(exc).__name__}"

    groq_status = "configured" if settings.groq_configured else "missing GROQ_API_KEY"
    overall = "ok" if qdrant_status == "ok" and groq_status == "configured" else "degraded"

    return HealthResponse(
        status=overall,
        qdrant=qdrant_status,
        groq=groq_status,
        collection=settings.qdrant_collection,
        points_count=points,
        model=settings.groq_model,
    )
