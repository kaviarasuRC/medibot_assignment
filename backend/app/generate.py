"""Answer generation, grounded in the reranked chunks and nothing else.

`generate_answer()` accepts only the reranked list. It has no access to the
candidate pool, so the assignment's requirement that "the full initial candidate
set must not be passed through" is enforced structurally rather than by
discipline.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from groq import Groq

from app.chunk import Chunk
from app.config import settings
from app.models import Source
from app.rbac import Role, coerce_role, refusal_message

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are MediBot, an internal assistant for MediAssist Health Network.
You are speaking with a staff member whose role is: {role}.

Rules:
1. Answer ONLY from the CONTEXT below. It is the complete set of documents this
   user is authorised to see.
2. If the CONTEXT does not contain the answer, say so plainly. Do not use outside
   knowledge. Do not guess.
3. Cite the source for every substantive claim, as [source_document - section_title].
4. You are not a medical decision-maker. Report what the protocol says; do not
   extrapolate dosages, diagnoses, or treatment decisions beyond the text.
5. Never speculate about documents outside the CONTEXT, and never comment on what
   other roles can access."""

# Rule 5 earns its place: without it, a model shown only nursing documents will
# sometimes helpfully volunteer "billing information would be in the billing
# handbook, which I can't see". Technically not a leak, but it confirms the
# existence and naming of restricted collections and looks bad in a demo.


class GenerationUnavailable(RuntimeError):
    """Raised when the LLM cannot be reached or is not configured."""


@lru_cache(maxsize=1)
def get_groq() -> Groq:
    if not settings.groq_configured:
        raise GenerationUnavailable(
            "GROQ_API_KEY is not set. Add it to backend/.env - see .env.example."
        )
    return Groq(api_key=settings.groq_api_key)


def build_context(chunks: list[tuple[float, Chunk]]) -> str:
    """The numbered CONTEXT block.

    Each entry shows `source_document` and `section_title`, so the citation
    format the model is asked for is the format it can actually see.
    """
    blocks = []
    for index, (_score, chunk) in enumerate(chunks, start=1):
        blocks.append(
            f"[{index}] source_document: {chunk.source_document}\n"
            f"    section_title:   {chunk.section_title or '(none)'}\n"
            f"    content:         {chunk.text}"
        )
    return "\n\n".join(blocks)


def build_sources(chunks: list[tuple[float, Chunk]]) -> list[Source]:
    """Sources come from the chunks actually passed in, never parsed from prose.

    De-duplicated on (document, section) so three chunks from one section render
    as one citation card.
    """
    seen: set[tuple[str, str]] = set()
    sources: list[Source] = []
    for _score, chunk in chunks:
        key = (chunk.source_document, chunk.section_title)
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            Source(
                source_document=chunk.source_document,
                section_title=chunk.section_title,
                collection=chunk.collection,
            )
        )
    return sources


def generate_answer(
    question: str,
    role: Role | str,
    chunks: list[tuple[float, Chunk]],
) -> tuple[str, list[Source]]:
    """Produce a cited answer, or a role-scoped refusal if nothing survived.

    An empty chunk list never reaches the LLM: the refusal is cheaper, faster,
    and deterministic, which is what makes it assertable in the adversarial
    suite.
    """
    resolved = coerce_role(role)

    if not chunks:
        log.info("No chunks for role=%s - returning refusal without calling the LLM", resolved.value)
        return refusal_message(resolved), []

    prompt = (
        f"{SYSTEM_PROMPT.format(role=resolved.value)}\n\n"
        f"CONTEXT\n{build_context(chunks)}"
    )

    response = get_groq().chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": question},
        ],
        # This is a document-grounded factual task. Creativity is a defect.
        temperature=0.1,
        max_completion_tokens=1024,
    )
    answer = (response.choices[0].message.content or "").strip()
    return answer, build_sources(chunks)
