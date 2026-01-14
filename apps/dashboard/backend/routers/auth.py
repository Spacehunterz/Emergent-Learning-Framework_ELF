import os
import secrets
import json
import httpx
import logging
import time
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet, InvalidToken
from slowapi import Limiter
from slowapi.util import get_remote_address

from utils.database import get_db

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger(f"{__name__}.audit")

# Router
router = APIRouter(prefix="/api/auth", tags=["auth"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Configuration - GitHub OAuth
# Option 1: Direct OAuth (set GITHUB_CLIENT_ID + GITHUB_CLIENT_SECRET)
# Option 2: Worker proxy (set OAUTH_WORKER_URL only - client_id fetched from worker)
OAUTH_WORKER_URL = os.environ.get("OAUTH_WORKER_URL", "https://elf-oauth.elf0auth.workers.dev")
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")

USE_OAUTH_WORKER = not GITHUB_CLIENT_SECRET

async def get_oauth_config():
    """Get OAuth config - from env or worker"""
    global GITHUB_CLIENT_ID
    if GITHUB_CLIENT_ID:
        return GITHUB_CLIENT_ID
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{OAUTH_WORKER_URL}/oauth/config")
        data = resp.json()
        GITHUB_CLIENT_ID = data.get("client_id")
        return GITHUB_CLIENT_ID

# Session encryption key - auto-generate if not set
SESSION_ENCRYPTION_KEY = os.environ.get("SESSION_ENCRYPTION_KEY")
if not SESSION_ENCRYPTION_KEY:
    from cryptography.fernet import Fernet
    SESSION_ENCRYPTION_KEY = Fernet.generate_key().decode()
    logger.warning("SESSION_ENCRYPTION_KEY not set - generated temporary key (sessions won't persist across restarts)")

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
    """Thread-safe in-memory session storage with TTL, idle timeout, and automatic expiration."""

    MAX_SESSIONS = 10000  # Prevent unbounded memory growth
    CLEANUP_INTERVAL = 300  # Run cleanup every 5 minutes

    def __init__(self, max_age: int, idle_timeout: int):
        # {token: (encrypted_data, created_timestamp, last_access_timestamp)}
        self.sessions: Dict[str, tuple] = {}
        self.max_age = max_age
        self.idle_timeout = idle_timeout
        self.last_cleanup = time.time()

    def set(self, token: str, encrypted_data: bytes) -> None:
        """Store session with timestamp. Triggers cleanup if needed."""
        self._cleanup_if_needed()

        # Prevent unbounded growth
        if len(self.sessions) >= self.MAX_SESSIONS:
            logger.warning(f"In-memory session store at capacity ({self.MAX_SESSIONS}), purging oldest sessions")
            self._purge_oldest_sessions()

        now = time.time()
        self.sessions[token] = (encrypted_data, now, now)

    def get(self, token: str) -> Optional[bytes]:
        """Retrieve session if not expired or idle. Returns None if expired/idle or missing."""
        if token not in self.sessions:
            return None

        encrypted_data, created_timestamp, last_access = self.sessions[token]
        now = time.time()

        # Check if session exceeded max age (absolute timeout)
        if now - created_timestamp > self.max_age:
            del self.sessions[token]
            audit_logger.warning(f"Session expired by max age: {token[:8]}... (age: {now - created_timestamp:.0f}s)")
            return None

        # Check if session is idle (idle timeout)
        if now - last_access > self.idle_timeout:
            del self.sessions[token]
            audit_logger.warning(f"Session expired by idle timeout: {token[:8]}... (idle: {now - last_access:.0f}s)")
            return None

        # Update last access time
        self.sessions[token] = (encrypted_data, created_timestamp, now)
        return encrypted_data

    def delete(self, token: str) -> bool:
        """Delete session. Returns True if session existed."""
        return self.sessions.pop(token, None) is not None

    def clear(self) -> None:
        """Clear all sessions (for testing)."""
        self.sessions.clear()

    def _cleanup_if_needed(self) -> None:
        """Periodically remove expired/idle sessions."""
        now = time.time()
        if now - self.last_cleanup < self.CLEANUP_INTERVAL:
            return

        expired = [
            token for token, (_, created, last_access) in self.sessions.items()
            if (now - created > self.max_age) or (now - last_access > self.idle_timeout)
        ]

        for token in expired:
            del self.sessions[token]

        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired/idle in-memory sessions")

        self.last_cleanup = now

    def _purge_oldest_sessions(self) -> None:
        """Remove oldest 25% of sessions when at capacity."""
        # Sort by created timestamp and remove oldest sessions
        sorted_sessions = sorted(
            self.sessions.items(),
            key=lambda x: x[1][1]  # created_timestamp
        )

        purge_count = len(sorted_sessions) // 4
        for token, _ in sorted_sessions[:purge_count]:
            del self.sessions[token]

        audit_logger.warning(f"Purged {purge_count} oldest in-memory sessions due to capacity limit")


# Initialize in-memory session store with max age and idle timeout
IN_MEMORY_SESSIONS = InMemorySessionStore(SESSION_MAX_AGE, SESSION_IDLE_TIMEOUT)
SESSIONS = IN_MEMORY_SESSIONS


class SessionData(BaseModel):
    """Validated session data structure"""
    model_config = {"frozen": True}

    id: int = Field(..., gt=0)
    github_id: int = Field(..., gt=0)
    username: str = Field(..., min_length=1, max_length=255)
    avatar_url: Optional[str] = Field(None, max_length=2048)
    access_token: Optional[str] = Field(None, max_length=255)

    @field_validator("username")
    @classmethod
    def sanitize_username(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Username cannot be empty")
        return v.strip()[:255]

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not v.startswith(("https://", "http://")):
            raise ValueError("Avatar URL must be HTTP(S)")
        return v[:2048]


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
            logger.info(f"Session stored in Redis: {token[:20]}...")
        except Exception as e:
            logger.error(f"Failed to store session in Redis: {type(e).__name__}")
            IN_MEMORY_SESSIONS.set(token, encrypted)
            logger.info(f"Session fallback to in-memory: {token[:20]}...")
    else:
        IN_MEMORY_SESSIONS.set(token, encrypted)
        logger.info(f"Session stored in-memory: {token[:20]}... (sessions count: {len(IN_MEMORY_SESSIONS.sessions)})")

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
    client_id = await get_oauth_config()
    if not client_id:
        raise HTTPException(status_code=500, detail="OAuth not configured")
    redirect_uri = "http://localhost:8888/api/auth/callback"
    return RedirectResponse(
        url=f"https://github.com/login/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&scope=read:user"
    )


async def exchange_code_for_token(code: str, redirect_uri: str) -> dict:
    """Exchange OAuth code for access token - via worker or direct."""
    async with httpx.AsyncClient() as client:
        if USE_OAUTH_WORKER:
            resp = await client.post(
                f"{OAUTH_WORKER_URL}/oauth/token",
                json={"code": code, "redirect_uri": redirect_uri}
            )
            return resp.json()
        else:
            resp = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": GITHUB_CLIENT_ID,
                    "client_secret": GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": redirect_uri
                }
            )
            return resp.json()


@router.get("/callback")
@limiter.limit("5/minute")
async def callback(request: Request, code: str, response: Response):
    """Handle GitHub OAuth callback."""
    client_ip = request.client.host if request.client else "unknown"
    redirect_uri = "http://localhost:8888/api/auth/callback"

    try:
        token_data = await exchange_code_for_token(code, redirect_uri)
        access_token = token_data.get("access_token")

        if not access_token:
            error_msg = token_data.get("error_description", token_data.get("error", "Unknown error"))
            audit_logger.warning(f"Failed to get GitHub access token from {client_ip}: {error_msg}")
            raise HTTPException(status_code=400, detail=f"Failed to get access token: {error_msg}")

        async with httpx.AsyncClient() as client:
            user_res = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"token {access_token}"}
            )
            user_data = user_res.json()

        return await handle_login(response, user_data["id"], user_data["login"], user_data.get("avatar_url"), access_token, client_ip)

    except HTTPException:
        raise
    except Exception as e:
        audit_logger.error(f"OAuth callback error from {client_ip}: {type(e).__name__}: {e}")
        raise HTTPException(status_code=400, detail="OAuth authentication failed")


async def handle_login(response: Response, github_id: int, username: str, avatar_url: Optional[str], access_token: str, client_ip: str = "unknown") -> RedirectResponse:
    """Common login logic: Upsert User, Create Session, Redirect."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE github_id = ?", (github_id,))
            existing = cursor.fetchone()
            if existing:
                user_id = existing["id"]
                is_new_user = False
                cursor.execute("UPDATE users SET username = ?, avatar_url = ? WHERE id = ?", (username, avatar_url, user_id))
            else:
                cursor.execute("INSERT INTO users (github_id, username, avatar_url) VALUES (?, ?, ?)", (github_id, username, avatar_url))
                user_id = cursor.lastrowid
                is_new_user = True
                cursor.execute("INSERT OR IGNORE INTO game_state (user_id) VALUES (?)", (user_id,))
            conn.commit()

        session_data = SessionData(
            id=user_id,
            github_id=github_id,
            username=username,
            avatar_url=avatar_url,
            access_token=access_token
        )
        token = await create_session(session_data)

        # Audit log successful login
        event_type = "new_user_signup" if is_new_user else "user_login"
        audit_logger.info(f"{event_type}: user_id={user_id} username={username} github_id={github_id} from {client_ip}")

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
    except Exception as e:
        audit_logger.error(f"Login failed for github_id={github_id} from {client_ip}: {type(e).__name__}: {e}")
        raise


@router.get("/me")
async def get_current_user(request: Request) -> Dict[str, Any]:
    """Get current session user."""
    token = request.cookies.get("session_token")
    if not token:
        return {"is_authenticated": False}
    user = await get_session(token)
    if not user:
        audit_logger.debug(f"Invalid/expired session token attempted: {token[:8] if token else 'None'}...")
        return {"is_authenticated": False}
    audit_logger.debug(f"Session validated for user_id={user.id} username={user.username}")
    return {**user.model_dump(), "is_authenticated": True}


@router.post("/logout")
async def logout(response: Response, request: Request) -> Dict[str, bool]:
    """Logout: delete session and clear cookie"""
    token = request.cookies.get("session_token")
    client_ip = request.client.host if request.client else "unknown"
    success = True

    if token:
        # Get user info before deleting session for audit log
        user_session = await get_session(token)
        success = await delete_session(token)
        if user_session:
            audit_logger.info(f"user_logout: user_id={user_session.id} username={user_session.username} from {client_ip}")
        else:
            audit_logger.debug(f"Logout attempted with invalid/expired token from {client_ip}")
    else:
        audit_logger.debug(f"Logout attempted without session token from {client_ip}")

    response.delete_cookie("session_token", domain=SESSION_DOMAIN)
    return {"success": success}
