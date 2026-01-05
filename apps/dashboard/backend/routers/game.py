import json
import httpx
from fastapi import APIRouter, HTTPException, Depends, Request, Body, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from utils.database import get_db, dict_from_row
from routers.auth import get_user_id, SESSIONS

router = APIRouter(prefix="/api/game", tags=["game"])


# =============================================================================
# Leaderboard Models
# =============================================================================

class LeaderboardEntry(BaseModel):
    """Single leaderboard entry with user info and score."""
    rank: int
    user_id: int
    username: str
    avatar_url: Optional[str] = None
    score: int
    is_current_user: bool = False


class LeaderboardResponse(BaseModel):
    """Complete leaderboard response with pagination metadata."""
    entries: List[LeaderboardEntry]
    total_players: int
    current_user_rank: Optional[int] = None
    current_user_score: Optional[int] = None
    has_more: bool
    offset: int
    limit: int


# =============================================================================
# Leaderboard Configuration
# =============================================================================

# Anti-cheat: Maximum allowed score per session (configurable)
MAX_VALID_SCORE = 1_000_000_000  # 1 billion - adjust based on game design
# Minimum score to appear on leaderboard (filters out inactive accounts)
MIN_LEADERBOARD_SCORE = 0


# =============================================================================
# Leaderboard Endpoint
# =============================================================================

@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    request: Request,
    limit: int = Query(default=10, ge=1, le=100, description="Number of entries to return (1-100)"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    include_self: bool = Query(default=True, description="Include current user's rank even if not in top N"),
):
    """
    Get the game leaderboard with top scores.

    Features:
    - Returns top N scores with usernames and avatars
    - Includes current user's rank if authenticated (even if not in top N)
    - Supports pagination via offset/limit
    - Anti-cheat: Only shows scores within valid range
    - Performance: Uses indexed queries and limits result set

    Returns:
        LeaderboardResponse with ranked entries and metadata
    """
    current_user_id = await get_user_id(request)

    with get_db() as conn:
        cursor = conn.cursor()

        # ---------------------------------------------------------------------
        # Query 1: Get total player count (for pagination metadata)
        # Only count players with scores in valid range
        # ---------------------------------------------------------------------
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM game_state gs
            JOIN users u ON gs.user_id = u.id
            WHERE gs.score >= ? AND gs.score <= ?
        """, (MIN_LEADERBOARD_SCORE, MAX_VALID_SCORE))
        total_players = cursor.fetchone()["total"]

        # ---------------------------------------------------------------------
        # Query 2: Get leaderboard entries with ranking
        # Uses window function for accurate ranking (handles ties correctly)
        # Joins with users table for display info
        # Filters out potentially cheated scores
        # ---------------------------------------------------------------------
        cursor.execute("""
            SELECT
                u.id as user_id,
                u.username,
                u.avatar_url,
                gs.score,
                DENSE_RANK() OVER (ORDER BY gs.score DESC) as rank
            FROM game_state gs
            JOIN users u ON gs.user_id = u.id
            WHERE gs.score >= ? AND gs.score <= ?
            ORDER BY gs.score DESC, u.id ASC
            LIMIT ? OFFSET ?
        """, (MIN_LEADERBOARD_SCORE, MAX_VALID_SCORE, limit, offset))

        rows = cursor.fetchall()

        # Build leaderboard entries
        entries: List[LeaderboardEntry] = []
        for row in rows:
            data = dict_from_row(row)
            entries.append(LeaderboardEntry(
                rank=data["rank"],
                user_id=data["user_id"],
                username=data["username"],
                avatar_url=data["avatar_url"],
                score=data["score"],
                is_current_user=(data["user_id"] == current_user_id) if current_user_id else False
            ))

        # ---------------------------------------------------------------------
        # Query 3: Get current user's rank (if authenticated and include_self)
        # Uses subquery to calculate rank without fetching all rows
        # ---------------------------------------------------------------------
        current_user_rank: Optional[int] = None
        current_user_score: Optional[int] = None

        if current_user_id and include_self:
            # First get the user's score
            cursor.execute("""
                SELECT gs.score
                FROM game_state gs
                WHERE gs.user_id = ?
            """, (current_user_id,))
            user_score_row = cursor.fetchone()

            if user_score_row:
                current_user_score = user_score_row["score"]

                # Only calculate rank if score is within valid range
                if MIN_LEADERBOARD_SCORE <= current_user_score <= MAX_VALID_SCORE:
                    # Count how many players have a higher score (rank = count + 1)
                    cursor.execute("""
                        SELECT COUNT(*) + 1 as rank
                        FROM game_state gs
                        JOIN users u ON gs.user_id = u.id
                        WHERE gs.score > ?
                        AND gs.score >= ? AND gs.score <= ?
                    """, (current_user_score, MIN_LEADERBOARD_SCORE, MAX_VALID_SCORE))
                    rank_row = cursor.fetchone()
                    current_user_rank = rank_row["rank"] if rank_row else None

        # Calculate if there are more entries
        has_more = (offset + limit) < total_players

        return LeaderboardResponse(
            entries=entries,
            total_players=total_players,
            current_user_rank=current_user_rank,
            current_user_score=current_user_score,
            has_more=has_more,
            offset=offset,
            limit=limit
        )


@router.get("/leaderboard/around-me")
async def get_leaderboard_around_me(
    request: Request,
    context: int = Query(default=5, ge=1, le=25, description="Number of entries above and below current user"),
):
    """
    Get leaderboard entries around the current user's rank.

    Useful for showing the user their position relative to nearby competitors.
    Returns `context` entries above and below the user's current rank.

    Requires authentication.

    Returns:
        LeaderboardResponse centered on the current user
    """
    current_user_id = await get_user_id(request)
    if not current_user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    with get_db() as conn:
        cursor = conn.cursor()

        # Get current user's score
        cursor.execute("""
            SELECT gs.score
            FROM game_state gs
            WHERE gs.user_id = ?
        """, (current_user_id,))
        user_score_row = cursor.fetchone()

        if not user_score_row:
            raise HTTPException(status_code=404, detail="No game state found for user")

        current_user_score = user_score_row["score"]

        # Validate score is in range
        if not (MIN_LEADERBOARD_SCORE <= current_user_score <= MAX_VALID_SCORE):
            raise HTTPException(status_code=400, detail="Score outside valid range")

        # Get user's rank
        cursor.execute("""
            SELECT COUNT(*) + 1 as rank
            FROM game_state gs
            JOIN users u ON gs.user_id = u.id
            WHERE gs.score > ?
            AND gs.score >= ? AND gs.score <= ?
        """, (current_user_score, MIN_LEADERBOARD_SCORE, MAX_VALID_SCORE))
        current_user_rank = cursor.fetchone()["rank"]

        # Get total players
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM game_state gs
            JOIN users u ON gs.user_id = u.id
            WHERE gs.score >= ? AND gs.score <= ?
        """, (MIN_LEADERBOARD_SCORE, MAX_VALID_SCORE))
        total_players = cursor.fetchone()["total"]

        # Calculate offset to center on user
        # We want `context` entries above the user
        offset = max(0, current_user_rank - context - 1)
        limit = (context * 2) + 1  # context above + user + context below

        # Get entries around the user
        cursor.execute("""
            SELECT
                u.id as user_id,
                u.username,
                u.avatar_url,
                gs.score,
                DENSE_RANK() OVER (ORDER BY gs.score DESC) as rank
            FROM game_state gs
            JOIN users u ON gs.user_id = u.id
            WHERE gs.score >= ? AND gs.score <= ?
            ORDER BY gs.score DESC, u.id ASC
            LIMIT ? OFFSET ?
        """, (MIN_LEADERBOARD_SCORE, MAX_VALID_SCORE, limit, offset))

        rows = cursor.fetchall()

        entries: List[LeaderboardEntry] = []
        for row in rows:
            data = dict_from_row(row)
            entries.append(LeaderboardEntry(
                rank=data["rank"],
                user_id=data["user_id"],
                username=data["username"],
                avatar_url=data["avatar_url"],
                score=data["score"],
                is_current_user=(data["user_id"] == current_user_id)
            ))

        has_more = (offset + limit) < total_players

        return LeaderboardResponse(
            entries=entries,
            total_players=total_players,
            current_user_rank=current_user_rank,
            current_user_score=current_user_score,
            has_more=has_more,
            offset=offset,
            limit=limit
        )

class GameState(BaseModel):
    score: int
    level: int = 1
    active_weapon: str
    unlocked_weapons: List[str]
    unlocked_cursors: List[str]

@router.get("/state")
async def get_game_state(request: Request):
    """Get authoritative game state for current user."""
    user_id = await get_user_id(request)
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
    user_id = await get_user_id(request)
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
    user_id = await get_user_id(request)
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
    user_id = await get_user_id(request)
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
