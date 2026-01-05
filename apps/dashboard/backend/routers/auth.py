import os
import secrets
import json
import httpx
import logging
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
from cryptography.fernet import Fernet
from slowapi import Limiter
from slowapi.util import get_remote_address

from utils.database import get_db, dict_from_row

logger = logging.getLogger(__name__)

# Router
router = APIRouter(prefix="/api/auth", tags=["auth"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Configuration
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")
is_missing = not (GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET)
is_mock_config = GITHUB_CLIENT_ID == "mock"
IS_DEV_MOCK = is_missing or is_mock_config

# Development mode requires a secure token
DEV_ACCESS_TOKEN = os.environ.get("DEV_ACCESS_TOKEN")
if IS_DEV_MOCK and not DEV_ACCESS_TOKEN:
    raise RuntimeError("DEV_ACCESS_TOKEN environment variable required")

# Session encryption key
SESSION_ENCRYPTION_KEY = os.environ.get("SESSION_ENCRYPTION_KEY")
if not SESSION_ENCRYPTION_KEY:
    raise RuntimeError("SESSION_ENCRYPTION_KEY environment variable required")

cipher = Fernet(SESSION_ENCRYPTION_KEY.encode())
SESSION_DOMAIN = os.environ.get("SESSION_DOMAIN", "localhost")

# Redis session storage
redis_client = None
USE_REDIS = False
try:
    import redis
    redis_client = redis.Redis(
        host=os.environ.get("REDIS_HOST", "localhost"),
        port=int(os.environ.get("REDIS_PORT", 6379)),
        db=0,
        decode_responses=False,
        socket_connect_timeout=5
    )
    redis_client.ping()
    USE_REDIS = True
    logger.info("Redis session store initialized")
except Exception as e:
    logger.warning(f"Redis unavailable, using in-memory: {e}")
    USE_REDIS = False

IN_MEMORY_SESSIONS = {}


class User(BaseModel):
    id: int
    github_id: int
    username: str
    avatar_url: Optional[str]
    is_authenticated: bool = True


def create_session(user_data: dict) -> str:
    """Create encrypted session"""
    token = secrets.token_urlsafe(32)
    encrypted = cipher.encrypt(json.dumps(user_data).encode())
    if USE_REDIS:
        redis_client.setex(f"session:{token}", 604800, encrypted)
    else:
        IN_MEMORY_SESSIONS[token] = encrypted
    return token


def get_session(token: str) -> Optional[dict]:
    """Retrieve and decrypt session"""
    try:
        if USE_REDIS:
            encrypted = redis_client.get(f"session:{token}")
        else:
            encrypted = IN_MEMORY_SESSIONS.get(token)
        if not encrypted:
            return None
        return json.loads(cipher.decrypt(encrypted).decode())
    except Exception as e:
        logger.error(f"Session decryption error: {e}")
        return None


def delete_session(token: str):
    """Delete session"""
    if USE_REDIS:
        redis_client.delete(f"session:{token}")
    else:
        IN_MEMORY_SESSIONS.pop(token, None)


def get_user_id(request: Request) -> Optional[int]:
    """Get user ID from session"""
    token = request.cookies.get("session_token")
    if not token:
        return None
    user = get_session(token)
    return user["id"] if user else None


def require_auth(request: Request) -> int:
    """Require authentication"""
    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id


@router.get("/login")
@limiter.limit("10/minute")
async def login(request: Request):
    """Redirect to GitHub OAuth."""
    if IS_DEV_MOCK:
        return RedirectResponse(url="/api/auth/dev-callback")
    redirect_uri = "http://localhost:8888/api/auth/callback"
    return RedirectResponse(
        url=f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&redirect_uri={redirect_uri}&scope=read:user"
    )


@router.get("/dev-callback")
@limiter.limit("3/minute")
async def dev_callback(request: Request, response: Response, dev_token: Optional[str] = None):
    """Mock callback for development - REQUIRES DEV_ACCESS_TOKEN"""
    if not IS_DEV_MOCK:
        raise HTTPException(status_code=403, detail="Dev mode disabled")
    if not dev_token or dev_token != DEV_ACCESS_TOKEN:
        logger.warning("Failed dev authentication attempt with invalid token")
        raise HTTPException(status_code=401, detail="Invalid dev access token")
    return await handle_login(response, 12345, "DevUser", None, "mock_token")


@router.get("/callback")
@limiter.limit("5/minute")
async def callback(request: Request, code: str, response: Response):
    """Handle GitHub OAuth callback."""
    if IS_DEV_MOCK:
        raise HTTPException(status_code=400, detail="In Dev Mode")
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": "http://localhost:8888/api/auth/callback"
            }
        )
        token_data = token_res.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to get access token")
        user_res = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {access_token}"}
        )
        user_data = user_res.json()
        return await handle_login(response, user_data["id"], user_data["login"], user_data.get("avatar_url"), access_token)


async def handle_login(response: Response, github_id: int, username: str, avatar_url: Optional[str], access_token: str):
    """Common login logic: Upsert User, Create Session, Redirect."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE github_id = ?", (github_id,))
        existing = cursor.fetchone()
        if existing:
            user_id = existing["id"]
            cursor.execute("UPDATE users SET username = ?, avatar_url = ? WHERE id = ?", (username, avatar_url, user_id))
        else:
            cursor.execute("INSERT INTO users (github_id, username, avatar_url) VALUES (?, ?, ?)", (github_id, username, avatar_url))
            user_id = cursor.lastrowid
            cursor.execute("INSERT OR IGNORE INTO game_state (user_id) VALUES (?)", (user_id,))
        conn.commit()

    token = create_session({
        "id": user_id,
        "github_id": github_id,
        "username": username,
        "avatar_url": avatar_url
    })

    response = RedirectResponse(url="http://localhost:3001")
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=True,
        max_age=86400 * 7,
        samesite="strict",
        domain=SESSION_DOMAIN
    )
    return response


@router.get("/me")
async def get_current_user(request: Request):
    """Get current session user."""
    token = request.cookies.get("session_token")
    if not token:
        return {"is_authenticated": False}
    user = get_session(token)
    if not user:
        return {"is_authenticated": False}
    return {**user, "is_authenticated": True}


@router.post("/logout")
async def logout(response: Response, request: Request):
    """Logout: delete session and clear cookie"""
    token = request.cookies.get("session_token")
    if token:
        delete_session(token)
    response.delete_cookie("session_token")
    return {"success": True}
