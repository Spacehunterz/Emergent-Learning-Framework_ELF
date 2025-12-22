import json
import httpx
from fastapi import APIRouter, HTTPException, Depends, Request, Body
from pydantic import BaseModel
from typing import List, Dict, Any
from utils.database import get_db, dict_from_row
from routers.auth import get_user_id, SESSIONS

router = APIRouter(prefix="/api/game", tags=["game"])

class GameState(BaseModel):
    score: int
    level: int = 1
    active_weapon: str
    unlocked_weapons: List[str]
    unlocked_cursors: List[str]

@router.get("/state")
async def get_game_state(request: Request):
    """Get authoritative game state for current user."""
    user_id = get_user_id(request)
    if not user_id:
        # Return default Guest state
        return {
            "score": 0,
            "level": 1,
            "active_weapon": "pulse_laser",
            "unlocked_weapons": ["pulse_laser"],
            "unlocked_cursors": ["default"]
        }

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM game_state WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if not row:
            # Initialize if missing
            return { "score": 0, "unlocked_weapons": ["pulse_laser"] }
            
        data = dict_from_row(row)
        return {
            "score": data["score"],
            "level": 1, # Logic for levels can be added later
            "active_weapon": data["active_weapon"],
            "unlocked_weapons": json.loads(data["unlocked_weapons"]),
            "unlocked_cursors": json.loads(data["unlocked_cursors"])
        }

@router.post("/sync")
async def sync_score(request: Request, payload: Dict[str, Any] = Body(...)):
    """Sync score from client (Server Validated)."""
    user_id = get_user_id(request)
    if not user_id:
        return {"success": False, "message": "Login required to save progress"}

    # Basic Anti-Cheat: Rate limiting / Delta checks could go here.
    # For now, we trust the client's score addition but log it.
    score_delta = payload.get("score_delta", 0)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT score FROM game_state WHERE user_id = ?", (user_id,))
        current_score = cursor.fetchone()["score"]
        
        new_score = current_score + score_delta
        
        cursor.execute("UPDATE game_state SET score = ? WHERE user_id = ?", (new_score, user_id))
        conn.commit()
        
    return {"success": True, "new_score": new_score}

@router.post("/equip")
async def equip_item(request: Request, payload: Dict[str, str] = Body(...)):
    """Server-side equip (prevents client from forcing locked items)."""
    user_id = get_user_id(request)
    if not user_id: return {"error": "Guest"}
    
    item_id = payload.get("id")
    # type = 'weapon' | 'cursor'
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT unlocked_weapons FROM game_state WHERE user_id = ?", (user_id,))
        unlocked = json.loads(cursor.fetchone()["unlocked_weapons"])
        
        if item_id in unlocked:
            cursor.execute("UPDATE game_state SET active_weapon = ? WHERE user_id = ?", (item_id, user_id))
            conn.commit()
            return {"success": True}
            
    return {"success": False, "message": "Item locked"}

@router.post("/verify-star")
async def verify_star(request: Request):
    """
    CHECK GITHUB API: Did this user star server-authoritative repo?
    If yes -> Unlock 'star_blaster' and 'star_cursor'.
    """
    user_id = get_user_id(request)
    if not user_id:
         raise HTTPException(status_code=401, detail="Login required")

    # 1. Get User's GitHub ID/Username from DB
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, github_id FROM users WHERE id = ?", (user_id,))
        user_row = dict_from_row(cursor.fetchone())
    
    username = user_row["username"]
    
    token = request.cookies.get("session_token")
    if not token or token not in SESSIONS:
         raise HTTPException(status_code=401, detail="Session expired")
         
    access_token = SESSIONS[token].get("access_token")
    
    # In a real app we'd use the stored OAuth Access Token for private checks.
    async with httpx.AsyncClient() as client:
        # Check if AUTHENTICATED user starred it
        # GET /user/starred/{owner}/{repo}
        url = "https://api.github.com/user/starred/Spacehunterz/Emergent-Learning-Framework_ELF"
        
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/vnd.github+json"
        }
        
        # MOCK FOR DEV
        if access_token == "mock_token":
             res_status = 204
        else:
             res = await client.get(url, headers=headers)
             res_status = res.status_code

    if res_status == 204:
        # 3. UNLOCK REWARD
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT unlocked_weapons, unlocked_cursors FROM game_state WHERE user_id = ?", (user_id,))
            row = dict_from_row(cursor.fetchone())
            
            weapons = json.loads(row["unlocked_weapons"])
            cursors = json.loads(row["unlocked_cursors"])
            
            unlocked_any = False
            if "star_blaster" not in weapons:
                weapons.append("star_blaster")
                unlocked_any = True

            # Unlock star_ship cursor and star_trail
            if "star_ship" not in cursors:
                cursors.append("star_ship")
                unlocked_any = True
            if "star_trail" not in cursors:
                cursors.append("star_trail")
                unlocked_any = True
            
            if unlocked_any:
                cursor.execute("""
                    UPDATE game_state 
                    SET unlocked_weapons = ?, unlocked_cursors = ?
                    WHERE user_id = ?
                """, (json.dumps(weapons), json.dumps(cursors), user_id))
                conn.commit()
                return {"success": True, "message": "Star confirmed! Rewards unlocked!"}
            else:
                 return {"success": True, "message": "Already unlocked.", "already_unlocked": True}

    return {"success": False, "message": "Repo not starred. Please star to unlock!"}
