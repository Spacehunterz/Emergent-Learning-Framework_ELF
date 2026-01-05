#!/usr/bin/env python3
"""
Security Setup Script for Emergent Learning Dashboard Backend

Helps developers configure required security parameters:
- SESSION_ENCRYPTION_KEY
- DEV_ACCESS_TOKEN  
- .env file setup
"""

import os
import sys
import subprocess
from pathlib import Path
from cryptography.fernet import Fernet


def generate_encryption_key():
    """Generate a Fernet encryption key"""
    return Fernet.generate_key().decode()


def generate_access_token():
    """Generate a secure random access token"""
    try:
        result = subprocess.run(
            ["openssl", "rand", "-hex", "32"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        import secrets
        return secrets.token_hex(32)


def setup_env():
    """Setup .env file with security credentials"""
    backend_dir = Path(__file__).parent
    env_file = backend_dir / ".env"
    
    print("[SECURITY] Emergent Learning Dashboard - Security Setup")
    print("=" * 60)
    
    if env_file.exists():
        print(f"[WARNING] .env file already exists at {env_file}")
        response = input("Overwrite existing .env file? (y/n): ").lower().strip()
        if response != 'y':
            print("Setup cancelled. Using existing .env file.")
            return
    
    print("
Generating security credentials...
")
    
    encryption_key = generate_encryption_key()
    dev_token = generate_access_token()
    
    print("[OK] Generated SESSION_ENCRYPTION_KEY")
    print("[OK] Generated DEV_ACCESS_TOKEN")
    
    env_content = f"""# Session encryption key - DO NOT SHARE
SESSION_ENCRYPTION_KEY={encryption_key}

# Development mode access token - DO NOT COMMIT TO GIT
DEV_ACCESS_TOKEN={dev_token}

# Session cookie settings
SESSION_DOMAIN=localhost

# Environment
ENVIRONMENT=development

# GitHub OAuth Configuration (Optional)
# GITHUB_CLIENT_ID=your-client-id
# GITHUB_CLIENT_SECRET=your-client-secret

# Redis Configuration (Optional)
# REDIS_HOST=localhost
# REDIS_PORT=6379

# Frontend Configuration  
# FRONTEND_URL=https://app.yourdomain.com  # Production only
"""
    
    env_file.write_text(env_content)
    os.chmod(env_file, 0o600)
    
    print(f"
[SUCCESS] Created .env file at {env_file}")
    print(f"[INFO] Permissions: 0600 - readable only by owner")
    print(f"
[IMPORTANT] Never commit .env to git or share these credentials!")


if __name__ == "__main__":
    try:
        setup_env()
    except Exception as e:
        print(f"[ERROR] Setup failed: {e}")
        sys.exit(1)
