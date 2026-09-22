"""Settings, loaded once from the environment.

Everything else imports `settings` from here. There is deliberately no
`os.getenv` anywhere else in the codebase - a model ID or a top-k that can be
changed in two places is a model ID that will eventually disagree with itself.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> backend/app -> backend -> <repo root>
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM ---
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="openai/gpt-oss-120b", alias="GROQ_MODEL")

    # --- Qdrant ---
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_collection: str = Field(default="medibot_documents", alias="QDRANT_COLLECTION")

    # --- Data (relative to the repo root) ---
    sqlite_path: str = Field(default="data/mediassist.db", alias="SQLITE_PATH")
    documents_path: str = Field(default="data/documents", alias="DOCUMENTS_PATH")

    # --- Auth ---
    jwt_secret: str = Field(default="change-me", alias="JWT_SECRET")
    jwt_expiry_hours: int = Field(default=8, alias="JWT_EXPIRY_HOURS")
    jwt_algorithm: str = "HS256"

    # --- Models ---
    embed_model: str = Field(default="BAAI/bge-small-en-v1.5", alias="EMBED_MODEL")
    embed_dim: int = 384
    sparse_model: str = Field(default="Qdrant/bm25", alias="SPARSE_MODEL")
    # L6, not L-6. The `L-6-v2` spelling copied across most tutorials is the
    # legacy repo name.
    rerank_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L6-v2", alias="RERANK_MODEL"
    )

    # --- Funnel ---
    # Policy narrowing (the RBAC filter) is NOT in this list and is not tunable.
    # These two are quality knobs: changing them changes answer quality, never
    # who can see what.
    retrieval_top_k: int = Field(default=20, alias="RETRIEVAL_TOP_K")
    rerank_top_k: int = Field(default=3, alias="RERANK_TOP_K")
    max_tokens: int = Field(default=512, alias="MAX_TOKENS")

    # Relevance floor on the cross-encoder score. Below this, nothing the user
    # may see is actually about the question, so the role-scoped refusal is
    # returned instead of letting the LLM improvise from loosely-related text.
    #
    # CALIBRATED, NOT GUESSED - see scripts/calibrate_floor.py and
    # docs/rerank_floor_calibration.md. Re-run that script whenever the corpus,
    # the embedder or the reranker changes.
    #
    # Measured over 18 labelled cases on this corpus:
    #     highest score among should-REFUSE : 0.000323
    #     lowest  score among should-ANSWER : 0.005906
    # 0.002 is roughly the geometric midpoint, leaving ~6x margin above the
    # highest correct refusal and ~3x below the lowest correct answer.
    #
    # The first guess here was 0.05, reasoning that a relevant passage "lands in
    # the 0.5-0.99 band". That is true only for well-phrased questions. The
    # model is bimodal but NOT calibrated across queries: a weakly phrased
    # correct match ("what is the preventive maintenance schedule for the
    # autoclave?") scored 0.0059 while its chunk still ranked FIRST. At 0.05
    # that answer was refused - and a false refusal is the dangerous direction,
    # because it looks exactly like RBAC working correctly.
    rerank_min_score: float = Field(default=0.002, alias="RERANK_MIN_SCORE")

    # --- Dev flags ---
    log_rerank: bool = Field(default=False, alias="MEDIBOT_LOG_RERANK")

    # --- CORS ---
    frontend_origin: str = Field(default="http://localhost:3000", alias="FRONTEND_ORIGIN")

    @property
    def groq_configured(self) -> bool:
        """True only for a real key.

        `.env.example` ships the placeholder `gsk_your_key_here`, and a copied
        .env that still contains it is the most likely misconfiguration. Treating
        it as configured would turn a clear "add your key" message into an opaque
        401 from Groq.
        """
        key = self.groq_api_key.strip()
        return bool(key) and key != "gsk_your_key_here" and not key.endswith("_here")

    @property
    def sqlite_abspath(self) -> Path:
        return REPO_ROOT / self.sqlite_path

    @property
    def documents_abspath(self) -> Path:
        return REPO_ROOT / self.documents_path


settings = Settings()
