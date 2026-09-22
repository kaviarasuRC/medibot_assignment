"""FastAPI application: CORS, router registration, and model warm-up."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import auth_routes, chat_routes, meta_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
for noisy in ("httpx", "urllib3", "sentence_transformers"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

log = logging.getLogger("medibot")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Warm the models at startup so the first request isn't 30 seconds. A
    # failure here is logged, not fatal - /health reports the degraded state.
    try:
        from app.embeddings import warm as warm_embeddings
        from app.rerank import warm as warm_reranker

        log.info("Warming embedding and rerank models...")
        warm_embeddings()
        warm_reranker()
        log.info("Models ready.")
    except Exception as exc:  # noqa: BLE001
        log.error("Model warm-up failed: %s", exc)
    yield


app = FastAPI(
    title="MediBot",
    description=(
        "Advanced RAG with role-based access control enforced as a Qdrant "
        "metadata pre-filter, so the LLM never sees a restricted chunk."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # Restricted to the frontend origin, not "*".
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(chat_routes.router)
app.include_router(meta_routes.router)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"service": "medibot", "docs": "/docs", "health": "/health"}
