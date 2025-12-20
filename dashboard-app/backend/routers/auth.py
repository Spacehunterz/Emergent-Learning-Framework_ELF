import os
import secrets
import httpx
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, Dict
from utils.database import get_db, dict_from_row

# Router
router = APIRouter(prefix="/api/auth", tags=["auth"])

# Configuration (Env vars in production, hardcoded/mock in dev if needed)
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")
# For dev, we might mock if these aren't present
is_missing = not (GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET)
is_mock_config = GITHUB_CLIENT_ID == "mock"
IS_DEV_MOCK = is_missing or is_mock_config

# Session Storage (Memory for now, Use Redis/DB in prod)
# Map: session_token -> user_dict
SESSIONS: Dict[str, dict] = {}

class User(BaseModel):
    id: int
    github_id: int
    username: str
    avatar_url: Optional[str]
    is_authenticated: bool = True

@router.get("/login")
async def login():
    """Redirect to GitHub OAuth."""
    if IS_DEV_MOCK:
        # Direct login for development without keys
        return RedirectResponse(url="/api/auth/dev-callback")
    
    redirect_uri = "http://localhost:8888/api/auth/callback"
    return RedirectResponse(
        url=f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&redirect_uri={redirect_uri}&scope=read:user"
    )

@router.get("/dev-callback")
async def dev_callback(response: Response):
    """Mock callback for development."""
    if not IS_DEV_MOCK:
        raise HTTPException(status_code=403, detail="Dev mode disabled")
        
    # Create mock user
    mock_github_id = 12345
    mock_username = "DevUser"
    mock_avatar = None
    mock_token = "mock_token"
    
    return await handle_login(response, mock_github_id, mock_username, mock_avatar, mock_token)

@router.get("/callback")
async def callback(code: str, response: Response):
    """Handle GitHub OAuth callback."""
    if IS_DEV_MOCK:
         raise HTTPException(status_code=400, detail="In Dev Mode")

    # Exchange code for token
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

        # Get User Info
        user_res = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"token {access_token}"}
        )
        user_data = user_res.json()
        
        return await handle_login(
            response, 
            user_data["id"], 
            user_data["login"], 
            user_data.get("avatar_url"),
            access_token
        )

async def handle_login(response: Response, github_id: int, username: str, avatar_url: Optional[str], access_token: str):
    """Common login logic: Upsert User, Create Session, Redirect."""
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Upsert User
        cursor.execute("SELECT * FROM users WHERE github_id = ?", (github_id,))
        existing = cursor.fetchone()
        
        if existing:
            user_id = existing["id"]
            cursor.execute("""
                UPDATE users SET username = ?, avatar_url = ? WHERE id = ?
            """, (username, avatar_url, user_id))
        else:
            cursor.execute("""
                INSERT INTO users (github_id, username, avatar_url) VALUES (?, ?, ?)
            """, (github_id, username, avatar_url))
            user_id = cursor.lastrowid
            
            # Initialize Game State for new user
            cursor.execute("""
                INSERT OR IGNORE INTO game_state (user_id) VALUES (?)
            """, (user_id,))
            
        conn.commit()
    
    # Create Session
    token = secrets.token_hex(32)
    SESSIONS[token] = {
        "id": user_id,
        "github_id": github_id,
        "username": username,
        "avatar_url": avatar_url,
        "access_token": access_token
    }
    
    # Set Cookie
    # In dev, we redirect to the frontend server (3001), not the backend root (8888)
    response = RedirectResponse(url="http://localhost:3001") 
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=86400 * 7, # 7 days
        samesite="lax"
    )
    return response

@router.get("/me")
async def get_current_user(request: Request):
    """Get current session user."""
    token = request.cookies.get("session_token")
    if not token or token not in SESSIONS:
        return {"is_authenticated": False}
    
    user = SESSIONS[token]
    return {**user, "is_authenticated": True}

@router.post("/logout")
async def logout(response: Response, request: Request):
    token = request.cookies.get("session_token")
    if token and token in SESSIONS:
        del SESSIONS[token]
    
    response.delete_cookie("session_token")
    return {"success": True}

# Middleware helper to get user ID inside other routes
def get_user_id(request: Request) -> Optional[int]:
    token = request.cookies.get("session_token")
    if not token or token not in SESSIONS:
        return None
    return SESSIONS[token]["id"]
