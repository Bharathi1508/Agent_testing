"""HEAAP Phase 21.9 - Local reviewer authentication."""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pwdlib import PasswordHash


ROOT = Path(__file__).resolve().parents[2]

load_dotenv(ROOT / ".env.phase21_9")

USERNAME = os.getenv("HEAAP_LOCAL_REVIEWER")
PASSWORD_HASH = os.getenv("HEAAP_LOCAL_PASSWORD_HASH")
JWT_SECRET = os.getenv("HEAAP_LOCAL_JWT_SECRET")

if not all([USERNAME, PASSWORD_HASH, JWT_SECRET]):
    raise RuntimeError("Local reviewer credentials not configured")

hasher = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)


def authenticate_reviewer(username, password):
    if username != USERNAME:
        return None

    if not hasher.verify(password, PASSWORD_HASH):
        return None

    now = datetime.now(timezone.utc)

    return jwt.encode(
        {
            "sub": USERNAME,
            "role": "reviewer",
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "iss": "heaap-local-poc",
            "aud": "heaap-governance",
        },
        JWT_SECRET,
        algorithm="HS256",
    )


def require_reviewer(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=["HS256"],
            issuer="heaap-local-poc",
            audience="heaap-governance",
            options={"require": ["sub", "exp", "iat", "iss", "aud"]},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session",
        )

    if (
        payload.get("sub") != USERNAME
        or payload.get("role") != "reviewer"
    ):
        raise HTTPException(
            status_code=403,
            detail="Reviewer permission required",
        )

    return {
        "username": USERNAME,
        "role": "reviewer",
    }
