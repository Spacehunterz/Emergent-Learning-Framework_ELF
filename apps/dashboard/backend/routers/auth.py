import os
import secrets
import json
import httpx
import logging
import asyncio
import time
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet, InvalidToken
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
SESSION_MAX_AGE = int(os.environ.get("SESSION_MAX_AGE", "604800"))
SESSION_IDLE_TIMEOUT = int(os.environ.get("SESSION_IDLE_TIMEOUT", "86400"))

async_redis_client = None
USE_REDIS = False

async def init_redis():
    """Initialize async Redis client during FastAPI startup"""
    global async_redis_client, USE_REDIS
    try:
        from redis.asyncio import Redis
        async_redis_client = Redis(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", 6379)),
            db=0,
            decode_responses=False,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        await async_redis_client.ping()
        USE_REDIS = True
        logger.info("Async Redis session store initialized")
    except ImportError:
        logger.warning("Redis module not installed - using in-memory sessions")
        USE_REDIS = False
    except Exception as e:
        logger.warning(f"Redis unavailable - using in-memory sessions: {type(e).__name__}")
        USE_REDIS = False


class InMemorySessionStore:
    """Thread-safe in-memory session storage with TTL and automatic expiration."""

    MAX_SESSIONS = 10000  # Prevent unbounded memory growth
    CLEANUP_INTERVAL = 300  # Run cleanup every 5 minutes

    def __init__(self, max_age: int):
        self.sessions: Dict[str, tuple] = {}  # {token: (encrypted_data, timestamp)}
        self.max_age = max_age
        self.last_cleanup = time.time()

    def set(self, token: str, encrypted_data: bytes) -> None:
        """Store session with timestamp. Triggers cleanup if needed."""
        self._cleanup_if_needed()

        # Prevent unbounded growth
        if len(self.sessions) >= self.MAX_SESSIONS:
            logger.warning(f"In-memory session store at capacity ({self.MAX_SESSIONS}), purging oldest sessions")
            self._purge_oldest_sessions()

        self.sessions[token] = (encrypted_data, time.time())

    def get(self, token: str) -> Optional[bytes]:
        """Retrieve session if not expired. Returns None if expired or missing."""
        if token not in self.sessions:
            return None

        encrypted_data, timestamp = self.sessions[token]

        # Check if expired
        if time.time() - timestamp > self.max_age:
            del self.sessions[token]
            logger.debug(f"Session expired: {token[:8]}...")
            return None

        return encrypted_data

    def delete(self, token: str) -> bool:
        """Delete session. Returns True if session existed."""
        return self.sessions.pop(token, None) is not None

    def _cleanup_if_needed(self) -> None:
        """Periodically remove expired sessions."""
        now = time.time()
        if now - self.last_cleanup < self.CLEANUP_INTERVAL:
            return

        expired = [
            token for token, (_, timestamp) in self.sessions.items()
            if now - timestamp > self.max_age
        ]

        for token in expired:
            del self.sessions[token]

        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired in-memory sessions")

        self.last_cleanup = now

    def _purge_oldest_sessions(self) -> None:
        """Remove oldest 25% of sessions when at capacity."""
        # Sort by timestamp and remove oldest sessions
        sorted_sessions = sorted(
            self.sessions.items(),
            key=lambda x: x[1][1]
        )

        purge_count = len(sorted_sessions) // 4
        for token, _ in sorted_sessions[:purge_count]:
            del self.sessions[token]

        logger.warning(f"Purged {purge_count} oldest in-memory sessions")


# Initialize in-memory session store with max age
IN_MEMORY_SESSIONS = InMemorySessionStore(SESSION_MAX_AGE)


class SessionData(BaseModel):
    """Validated session data structure"""
    id: int = Field(..., gt=0)
    github_id: int = Field(..., gt=0)
    username: str = Field(..., min_length=1, max_length=255)
    avatar_url: Optional[str] = Field(None, max_length=2048)

    @validator("username")
    def sanitize_username(cls, v):
        if not v or not v.strip():
            raise ValueError("Username cannot be empty")
        return v.strip()[:255]

    @validator("avatar_url")
    def validate_avatar_url(cls, v):
        if v is None:
            return v
        if not v.startswith(("https://", "http://")):
            raise ValueError("Avatar URL must be HTTP(S)")
        return v[:2048]

    class Config:
        frozen = True


class User(BaseModel):
    id: int
    github_id: int
    username: str
    avatar_url: Optional[str]
    is_authenticated: bool = True


async def create_session(user_data: SessionData) -> str:
    """Create encrypted session with async Redis"""
    token = secrets.token_urlsafe(32)
    encrypted = cipher.encrypt(user_data.model_dump_json().encode())

    if USE_REDIS and async_redis_client:
        try:
            await async_redis_client.setex(f"session:{token}", SESSION_MAX_AGE, encrypted)
        except Exception as e:
            logger.error(f"Failed to store session in Redis: {type(e).__name__}")
            IN_MEMORY_SESSIONS.set(token, encrypted)
    else:
        IN_MEMORY_SESSIONS.set(token, encrypted)

    return token


async def get_session(token: str) -> Optional[SessionData]:
    """Retrieve and decrypt session with async Redis"""
    if not token or len(token) > 64:
        return None

    try:
        encrypted = None
        if USE_REDIS and async_redis_client:
            try:
                encrypted = await async_redis_client.get(f"session:{token}")
            except Exception as e:
                logger.error(f"Redis retrieval error: {type(e).__name__}")
                encrypted = IN_MEMORY_SESSIONS.get(token)
        else:
            encrypted = IN_MEMORY_SESSIONS.get(token)

        if not encrypted:
            return None

        try:
            decrypted = cipher.decrypt(encrypted).decode("utf-8")
            return SessionData.model_validate_json(decrypted)
        except InvalidToken:
            logger.warning(f"Invalid/tampered session token: {token[:8]}...")
            return None
        except json.JSONDecodeError:
            logger.error("Session data corrupted - invalid JSON")
            return None
        except ValueError as e:
            logger.warning(f"Session validation failed: {e}")
            return None

    except Exception as e:
        logger.error(f"Session retrieval error: {type(e).__name__}: {e}")
        return None


async def delete_session(token: str) -> bool:
    """Delete session from storage"""
    if not token:
        return False

    try:
        if USE_REDIS and async_redis_client:
            try:
                result = await async_redis_client.delete(f"session:{token}")
                return result > 0
            except Exception as e:
                logger.error(f"Redis deletion error: {type(e).__name__}")
                return IN_MEMORY_SESSIONS.delete(token)
        else:
            return IN_MEMORY_SESSIONS.delete(token)
    except Exception as e:
        logger.error(f"Session deletion error: {type(e).__name__}")
        return False


async def get_user_id(request: Request) -> Optional[int]:
    """Get user ID from session (async)"""
    token = request.cookies.get("session_token")
    if not token:
        return None
    user = await get_session(token)
    return user.id if user else None


async def require_auth(request: Request) -> int:
    """Require authentication (async)"""
    user_id = await get_user_id(request)
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


async def handle_login(response: Response, github_id: int, username: str, avatar_url: Optional[str], access_token: str) -> RedirectResponse:
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

    session_data = SessionData(
        id=user_id,
        github_id=github_id,
        username=username,
        avatar_url=avatar_url
    )
    token = await create_session(session_data)

    redirect = RedirectResponse(url="http://localhost:3001")
    redirect.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=True,
        max_age=86400 * 7,
        samesite="strict",
        domain=SESSION_DOMAIN
    )
    return redirect


@router.get("/me")
async def get_current_user(request: Request) -> Dict[str, Any]:
    """Get current session user."""
    token = request.cookies.get("session_token")
    if not token:
        return {"is_authenticated": False}
    user = await get_session(token)
    if not user:
        return {"is_authenticated": False}
    return {**user.model_dump(), "is_authenticated": True}


@router.post("/logout")
async def logout(response: Response, request: Request) -> Dict[str, bool]:
    """Logout: delete session and clear cookie"""
    token = request.cookies.get("session_token")
    success = True
    if token:
        success = await delete_session(token)
    response.delete_cookie("session_token", domain=SESSION_DOMAIN)
    return {"success": success}
