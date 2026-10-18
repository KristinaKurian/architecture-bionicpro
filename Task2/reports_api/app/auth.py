"""Confidential OAuth2 Authorization Code + PKCE with an opaque browser session.

Only local demonstration over http://localhost is allowed with COOKIE_SECURE=false.
In production enforce HTTPS and COOKIE_SECURE=true.
"""
import base64
import hashlib
import json
import os
import secrets
from typing import Annotated

import httpx
import jwt
from jwt import PyJWKClient
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
import redis

router = APIRouter(prefix="/auth", tags=["auth"])

PUBLIC_BASE = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
ISSUER = os.getenv("OIDC_ISSUER", "http://localhost:8080/realms/reports-realm")
AUTH_URL = ISSUER + "/protocol/openid-connect/auth"
TOKEN_URL = os.getenv("OIDC_INTERNAL_URL", "http://keycloak:8080/realms/reports-realm") + "/protocol/openid-connect/token"
LOGOUT_URL = os.getenv("OIDC_INTERNAL_URL", "http://keycloak:8080/realms/reports-realm") + "/protocol/openid-connect/logout"
JWKS_URL = os.getenv("OIDC_INTERNAL_URL", "http://keycloak:8080/realms/reports-realm") + "/protocol/openid-connect/certs"
CLIENT_ID = os.getenv("OIDC_CLIENT_ID", "reports-bff")
CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET", "")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() == "true"
SESSION_TTL_SECONDS = 3600

def get_redis():
    return redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)


def verifier_and_challenge():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def _clear_cookie(response, name):
    response.delete_cookie(name, path="/", samesite="lax", secure=COOKIE_SECURE)

@router.get("/login")
def login(r: Annotated[redis.Redis, Depends(get_redis)]):
    from urllib.parse import urlencode
    state, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    verifier, challenge = verifier_and_challenge()
    r.setex("login:" + state, 300, json.dumps({"verifier": verifier, "nonce": nonce}))
    url = AUTH_URL + "?" + urlencode({
        "response_type": "code", "client_id": CLIENT_ID,
        "redirect_uri": PUBLIC_BASE + "/auth/callback",
        "scope": "openid profile", "state": state, "nonce": nonce,
        "code_challenge": challenge, "code_challenge_method": "S256",
    })
    response = RedirectResponse(url, status_code=302)
    response.set_cookie("bionic_login_state", state, httponly=True, secure=COOKIE_SECURE,
                        samesite="lax", max_age=300, path="/")
    return response

@router.get("/callback")
def callback(code: str, state: str, request: Request, r: Annotated[redis.Redis, Depends(get_redis)]):
    cookie_state = request.cookies.get("bionic_login_state")
    if not cookie_state or not secrets.compare_digest(cookie_state, state):
        raise HTTPException(400, "OAuth state mismatch")
    pending = r.getdel("login:" + state)
    if not pending:
        raise HTTPException(400, "Expired OAuth state")
    pending = json.loads(pending)
    with httpx.Client(timeout=15.0) as client:
        result = client.post(TOKEN_URL, data={
            "grant_type": "authorization_code", "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET, "code": code,
            "redirect_uri": PUBLIC_BASE + "/auth/callback",
            "code_verifier": pending["verifier"],
        })
        if result.status_code != 200:
            raise HTTPException(401, "OIDC code exchange failed")
        tokens = result.json()
    try:
        key = PyJWKClient(JWKS_URL).get_signing_key_from_jwt(tokens["id_token"])
        claims = jwt.decode(tokens["id_token"], key.key,
                            algorithms=["RS256"], audience=CLIENT_ID, issuer=ISSUER)
    except Exception:
        raise HTTPException(401, "Invalid ID token")
    if not secrets.compare_digest(claims.get("nonce", ""), pending["nonce"]):
        raise HTTPException(401, "Invalid OIDC nonce")
    if not claims.get("sub"):
        raise HTTPException(401, "Missing user subject")
    session_id = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    r.setex("session:" + session_id, SESSION_TTL_SECONDS, json.dumps({
        "sub": claims["sub"], "iss": claims["iss"], "csrf": csrf,
        "refresh_token": tokens.get("refresh_token"),
    }))
    response = RedirectResponse(os.getenv("FRONTEND_URL", "http://localhost:3000"), status_code=303)
    _clear_cookie(response, "bionic_login_state")
    response.set_cookie("bionic_session", session_id, httponly=True, secure=COOKIE_SECURE,
                        samesite="lax", max_age=SESSION_TTL_SECONDS, path="/")
    return response


def get_principal(
    bionic_session: Annotated[str | None, Cookie()] = None,
    r: redis.Redis = Depends(get_redis),
) -> dict:
    if not bionic_session:
        raise HTTPException(401, "Sign in required")
    raw = r.get("session:" + bionic_session)
    if raw is None:
        raise HTTPException(401, "Session expired")
    principal = json.loads(raw)
    return principal

@router.get("/me")
def me(principal: Annotated[dict, Depends(get_principal)]):
    return {"authenticated": True, "csrf": principal["csrf"]}

@router.post("/logout")
def logout(
    principal: Annotated[dict, Depends(get_principal)],
    bionic_session: Annotated[str | None, Cookie()] = None,
    x_csrf_token: Annotated[str | None, Header()] = None,
    r: redis.Redis = Depends(get_redis),
):
    if not x_csrf_token or not secrets.compare_digest(x_csrf_token, principal["csrf"]):
        raise HTTPException(403, "CSRF token required")
    if principal.get("refresh_token"):
        try:
            with httpx.Client(timeout=10.0) as client:
                client.post(LOGOUT_URL, data={
                    "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
                    "refresh_token": principal["refresh_token"],
                })
        except httpx.HTTPError:
            pass  # Destroy local session regardless of IdP availability.
    if bionic_session:
        r.delete("session:" + bionic_session)
    response = Response(status_code=204)
    _clear_cookie(response, "bionic_session")
    return response
