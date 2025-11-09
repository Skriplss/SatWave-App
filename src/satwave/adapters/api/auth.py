"""Auth helpers and protected endpoints using Supabase JWT."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Annotated, Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, status
from jose import jwk, jwt
from jose.utils import base64url_decode

from satwave.config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@lru_cache(maxsize=1)
def _get_jwks() -> Dict[str, Any]:
    settings = get_settings()
    if not settings.supabase_jwks_url:
        raise RuntimeError("SUPABASE_JWKS_URL (supabase_jwks_url) is not configured")
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(settings.supabase_jwks_url)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:  # pragma: no cover - network/env dependent
        logger.error(f"Failed to fetch JWKS: {e}")
        raise


def _verify_token_and_get_claims(token: str) -> Dict[str, Any]:
    # https://datatracker.ietf.org/doc/html/rfc7517 using python-jose
    jwks = _get_jwks()
    headers = jwt.get_unverified_header(token)
    kid = headers.get("kid")
    if not kid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing kid header")

    key = None
    for jwk_data in jwks.get("keys", []):
        if jwk_data.get("kid") == kid:
            key = jwk.construct(jwk_data)
            break
    if key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Signing key not found")

    message, encoded_sig = token.rsplit(".", 1)
    decoded_sig = base64url_decode(encoded_sig.encode())
    if not key.verify(message.encode(), decoded_sig):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    claims = jwt.get_unverified_claims(token)
    # Basic exp check (python-jose verify can also be used with public key but we already verified signature)
    if "exp" in claims:
        import time

        if time.time() > float(claims["exp"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

    return claims


async def get_current_user(authorization: Annotated[Optional[str], Header(None)]) -> Dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        claims = _verify_token_and_get_claims(token)
        return claims
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Token verification error")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")


@router.get("/me")
async def me(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Return decoded token claims. Frontend should use Supabase directly for auth & profile.

    This endpoint is useful to test auth wiring and protect backend routes with Supabase JWT.
    """
    # Normalize some fields
    return {
        "sub": user.get("sub"),
        "email": user.get("email"),
        "role": user.get("role"),
        "app_metadata": user.get("app_metadata"),
        "user_metadata": user.get("user_metadata"),
    }


# Registration endpoint intentionally removed. Use Supabase dashboard or invite links to create users.
