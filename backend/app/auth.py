"""Demo user store and token issue/verify.

Demo-grade storage is acceptable here and stated as such in the README - this is
a retrieval assignment, not an auth assignment. What is NOT negotiable is that
the token genuinely carries the role and the server genuinely re-derives it,
because the entire assignment is about access control. A spoofable token would
make every other layer decorative.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings
from app.rbac import PermissionDenied, Role, coerce_role

log = logging.getLogger(__name__)

# One demo account per role. Passwords are the role names - these are published
# in the README for a reviewer to use, so there is nothing to protect.
DEMO_USERS: dict[str, tuple[str, Role]] = {
    "dr.mehta": ("doctor", Role.DOCTOR),
    "nurse.priya": ("nurse", Role.NURSE),
    "billing.ravi": ("billing", Role.BILLING_EXECUTIVE),
    "tech.anand": ("technician", Role.TECHNICIAN),
    "admin.sys": ("admin", Role.ADMIN),
}

bearer_scheme = HTTPBearer(auto_error=False)


def authenticate(username: str, password: str) -> Role:
    """Verify credentials, returning the role. Raises 401 on any failure."""
    entry = DEMO_USERS.get(username)

    # compare_digest against a dummy even on an unknown user, so the response
    # time does not distinguish "no such user" from "wrong password".
    expected, role = entry if entry else ("\x00invalid", None)
    matched = secrets.compare_digest(password, expected)

    if not entry or not matched:
        log.warning("Failed login attempt for username=%r", username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return role


def create_token(username: str, role: Role) -> str:
    """Sign a token carrying {sub, role}. The role is fixed here and nowhere else."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "role": role.value,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expiry_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_role(token: str) -> Role:
    """Recover the role from a token, failing closed on anything unexpected."""
    try:
        claims = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        # A token whose `role` claim has been tampered with to an unknown value
        # must fail, not fall through to a default.
        return coerce_role(claims.get("role"))
    except PermissionDenied as exc:
        log.warning("Token carried an unrecognised role: %r", claims.get("role"))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token carries no recognised role",
        ) from exc


async def get_current_role(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Role:
    """THE only source of role in the request path.

    `/chat` takes the role from here and from nowhere else. Any `role` field in
    the request body is discarded by `ChatRequest`'s `extra="ignore"`.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_role(credentials.credentials)
