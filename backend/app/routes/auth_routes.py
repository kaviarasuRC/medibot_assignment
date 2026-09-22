"""POST /login - exchange demo credentials for a role-tagged token."""

from __future__ import annotations

from fastapi import APIRouter

from app.auth import authenticate, create_token
from app.models import LoginRequest, LoginResponse
from app.rbac import can_use_sql_rag, collections_for_role

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    role = authenticate(payload.username, payload.password)
    return LoginResponse(
        access_token=create_token(payload.username, role),
        role=role.value,
        collections=collections_for_role(role),
        sql_access=can_use_sql_rag(role),
    )
