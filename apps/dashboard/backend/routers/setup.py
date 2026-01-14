import os
import httpx
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/setup", tags=["setup"])

ENV_PATH = Path(__file__).parent.parent / ".env"
OAUTH_WORKER_URL = os.environ.get("OAUTH_WORKER_URL", "https://elf-oauth.elf0auth.workers.dev")

class SetupConfig(BaseModel):
    client_id: str
    client_secret: str

@router.get("/status")
async def get_setup_status():
    """Check if GitHub Auth is configured (local env OR OAuth worker)."""
    client_id = os.environ.get("GITHUB_CLIENT_ID")
    client_secret = os.environ.get("GITHUB_CLIENT_SECRET")

    is_placeholder = client_id == "your_client_id_here"

    if client_secret and not is_placeholder:
        return {"configured": True, "missing": [], "is_placeholder": False, "mode": "local"}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OAUTH_WORKER_URL}/oauth/config")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("client_id"):
                    return {"configured": True, "missing": [], "is_placeholder": False, "mode": "worker"}
    except:
        pass

    missing = []
    if not client_id or is_placeholder:
        missing.append("GITHUB_CLIENT_ID")
    if not client_secret or is_placeholder:
        missing.append("GITHUB_CLIENT_SECRET")

    return {
        "configured": False,
        "missing": missing,
        "is_placeholder": is_placeholder,
        "mode": "none"
    }

@router.post("/config")
async def save_setup_config(config: SetupConfig):
    """Save configuration to .env file."""
    
    # Read existing content to preserve other vars
    content = ""
    if ENV_PATH.exists():
        with open(ENV_PATH, "r") as f:
            content = f.read()
            
    # Parse lines
    lines = content.splitlines()
    new_lines = []
    
    # Update or Add keys
    updated_id = False
    updated_secret = False
    
    for line in lines:
        if line.startswith("GITHUB_CLIENT_ID="):
            new_lines.append(f"GITHUB_CLIENT_ID={config.client_id}")
            updated_id = True
        elif line.startswith("GITHUB_CLIENT_SECRET="):
            new_lines.append(f"GITHUB_CLIENT_SECRET={config.client_secret}")
            updated_secret = True
        else:
            new_lines.append(line)
            
    if not updated_id:
        new_lines.append(f"GITHUB_CLIENT_ID={config.client_id}")
    if not updated_secret:
        new_lines.append(f"GITHUB_CLIENT_SECRET={config.client_secret}")
        
    # Write back
    with open(ENV_PATH, "w") as f:
        f.write("\n".join(new_lines) + "\n")
        
    return {"success": True, "message": "Configuration saved. Please restart the backend server."}
