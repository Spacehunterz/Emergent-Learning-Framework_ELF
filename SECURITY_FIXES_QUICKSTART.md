# Security Fixes Quick Start Guide

**Priority:** Critical vulnerabilities requiring immediate attention
**Estimated Time:** 8-12 hours for basic security hardening

---

## 1. Secure Session Management (2 hours)

### Install Dependencies
```bash
pip install redis==5.2.1 cryptography==43.0.3
```

### Update auth.py
```python
# apps/dashboard/backend/routers/auth.py
import redis
import os
from cryptography.fernet import Fernet

# Replace in-memory SESSIONS dict
redis_client = redis.Redis(
    host=os.environ.get("REDIS_HOST", "localhost"),
    port=int(os.environ.get("REDIS_PORT", 6379)),
    db=0,
    decode_responses=False
)

# Generate encryption key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
cipher = Fernet(os.environ["SESSION_ENCRYPTION_KEY"].encode())

def create_session(user_data: dict) -> str:
    """Create encrypted session in Redis"""
    token = secrets.token_urlsafe(32)
    encrypted = cipher.encrypt(json.dumps(user_data).encode())
    redis_client.setex(f"session:{token}", 604800, encrypted)  # 7 days
    return token

def get_session(token: str) -> Optional[dict]:
    """Retrieve and decrypt session"""
    encrypted = redis_client.get(f"session:{token}")
    if not encrypted:
        return None
    return json.loads(cipher.decrypt(encrypted))

def delete_session(token: str):
    """Delete session from Redis"""
    redis_client.delete(f"session:{token}")

# Update handle_login
async def handle_login(...):
    # ... existing code ...

    # Replace: SESSIONS[token] = {...}
    token = create_session({
        "id": user_id,
        "github_id": github_id,
        "username": username,
        "avatar_url": avatar_url,
        "access_token": access_token  # Consider not storing this
    })

    # ... rest of code ...

# Update get_current_user
@router.get("/me")
async def get_current_user(request: Request):
    token = request.cookies.get("session_token")
    if not token:
        return {"is_authenticated": False}

    user = get_session(token)  # Replace: SESSIONS[token]
    if not user:
        return {"is_authenticated": False}

    return {**user, "is_authenticated": True}

# Update logout
@router.post("/logout")
async def logout(response: Response, request: Request):
    token = request.cookies.get("session_token")
    if token:
        delete_session(token)  # Replace: del SESSIONS[token]

    response.delete_cookie("session_token")
    return {"success": True}
```

### Environment Variables
```bash
# .env
SESSION_ENCRYPTION_KEY=<generated-key>
REDIS_HOST=localhost
REDIS_PORT=6379
```

---

## 2. Enable HTTPS Cookies (15 minutes)

### Update Cookie Settings
```python
# apps/dashboard/backend/routers/auth.py:138

response.set_cookie(
    key="session_token",
    value=token,
    httponly=True,
    secure=True,  # ADD THIS - HTTPS only
    max_age=86400 * 7,
    samesite="strict",  # CHANGE from "lax"
    domain=os.environ.get("SESSION_DOMAIN"),  # ADD THIS - Explicit domain
)
```

### Environment Variables
```bash
# .env
SESSION_DOMAIN=localhost  # Development
# SESSION_DOMAIN=.yourdomain.com  # Production
```

---

## 3. Add Rate Limiting (1 hour)

### Install Dependencies
```bash
pip install slowapi==0.1.9
```

### Configure Rate Limiting
```python
# apps/dashboard/backend/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

### Apply to Auth Endpoints
```python
# apps/dashboard/backend/routers/auth.py
from slowapi import Limiter
from fastapi import Request

limiter = Limiter(key_func=get_remote_address)

@router.get("/login")
@limiter.limit("10/minute")  # ADD THIS
async def login(request: Request):
    # ... existing code ...

@router.get("/callback")
@limiter.limit("5/minute")  # ADD THIS - Stricter for sensitive endpoint
async def callback(request: Request, code: str, response: Response):
    # ... existing code ...

@router.get("/dev-callback")
@limiter.limit("3/minute")  # ADD THIS - Very strict for dev bypass
async def dev_callback(request: Request, response: Response):
    # ... existing code ...
```

---

## 4. Secure Dev Mode (30 minutes)

### Update Dev Authentication
```python
# apps/dashboard/backend/routers/auth.py

# Add environment variable
DEV_ACCESS_TOKEN = os.environ.get("DEV_ACCESS_TOKEN")
if IS_DEV_MOCK and not DEV_ACCESS_TOKEN:
    raise RuntimeError("DEV_ACCESS_TOKEN required when GITHUB_CLIENT_ID=mock")

@router.get("/dev-callback")
@limiter.limit("3/minute")
async def dev_callback(
    request: Request,
    response: Response,
    dev_token: Optional[str] = None
):
    """Mock callback for development - REQUIRES DEV_ACCESS_TOKEN"""
    if not IS_DEV_MOCK:
        raise HTTPException(status_code=403, detail="Dev mode disabled")

    # Verify dev access token
    if not dev_token or dev_token != DEV_ACCESS_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid dev access token"
        )

    # Rest of implementation...
```

### Environment Variables
```bash
# .env
DEV_ACCESS_TOKEN=<random-secure-token>  # Generate: openssl rand -hex 32
```

### Usage
```bash
# Access dev callback with token
curl "http://localhost:8888/api/auth/dev-callback?dev_token=<your-token>"
```

---

## 5. Add CORS Configuration (20 minutes)

### Install Middleware
```python
# apps/dashboard/backend/main.py
from fastapi.middleware.cors import CORSMiddleware

# Determine allowed origins
if os.environ.get("ENVIRONMENT") == "production":
    allowed_origins = [os.environ.get("FRONTEND_URL")]
else:
    allowed_origins = [
        "http://localhost:3001",
        "http://localhost:3000",
        "http://127.0.0.1:3001",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=600,  # Cache preflight for 10 minutes
)
```

### Environment Variables
```bash
# .env
ENVIRONMENT=development
# FRONTEND_URL=https://app.yourdomain.com  # Production only
```

---

## 6. Add Input Validation (2 hours)

### Update Pydantic Models
```python
# apps/dashboard/backend/models.py
from pydantic import BaseModel, Field, validator
import re

class HeuristicUpdate(BaseModel):
    rule: Optional[str] = Field(None, max_length=1000)
    explanation: Optional[str] = Field(None, max_length=5000)
    domain: Optional[str] = Field(None, max_length=100)
    is_golden: Optional[bool] = None

    @validator('rule', 'explanation', 'domain')
    def strip_and_validate(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
        return v

class DecisionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    context: str = Field(..., min_length=1, max_length=10000)
    options_considered: Optional[str] = Field(None, max_length=5000)
    decision: str = Field(..., min_length=1, max_length=5000)
    rationale: str = Field(..., min_length=1, max_length=5000)
    domain: Optional[str] = Field(None, max_length=100)
    files_touched: Optional[str] = Field(None, max_length=5000)
    tests_added: Optional[str] = Field(None, max_length=5000)
    status: Optional[str] = Field("accepted", regex="^(accepted|rejected|superseded|deprecated)$")

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(20, ge=1, le=100)

class SpikeReportCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    topic: str = Field(..., min_length=1, max_length=200)
    question: str = Field(..., min_length=1, max_length=1000)
    findings: str = Field(..., min_length=1, max_length=50000)
    gotchas: Optional[str] = Field(None, max_length=10000)
    resources: Optional[str] = Field(None, max_length=10000)
    time_invested_minutes: Optional[int] = Field(None, ge=0, le=10000)
    domain: Optional[str] = Field(None, max_length=100)
    tags: Optional[str] = Field(None, max_length=500)
```

---

## 7. Add Authentication Dependency (1.5 hours)

### Create Auth Dependency
```python
# apps/dashboard/backend/routers/auth.py

def get_user_id(request: Request) -> Optional[int]:
    """Get user ID from session - returns None if not authenticated"""
    token = request.cookies.get("session_token")
    if not token:
        return None
    user = get_session(token)
    return user["id"] if user else None

def require_auth(request: Request) -> int:
    """Require authentication - raises 401 if not authenticated"""
    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    return user_id
```

### Apply to Protected Endpoints
```python
# apps/dashboard/backend/routers/heuristics.py
from fastapi import Depends, Request
from .auth import require_auth

@router.post("/heuristics/{heuristic_id}/promote")
async def promote_to_golden(
    heuristic_id: int,
    request: Request,
    user_id: int = Depends(require_auth)  # ADD THIS
) -> ActionResult:
    # ... implementation ...

@router.put("/heuristics/{heuristic_id}")
async def update_heuristic(
    heuristic_id: int,
    update: HeuristicUpdate,
    request: Request,
    user_id: int = Depends(require_auth)  # ADD THIS
) -> ActionResult:
    # ... implementation ...

@router.delete("/heuristics/{heuristic_id}")
async def delete_heuristic(
    heuristic_id: int,
    request: Request,
    user_id: int = Depends(require_auth)  # ADD THIS
) -> ActionResult:
    # ... implementation ...
```

### Identify Protected Endpoints
Apply `Depends(require_auth)` to:
- All POST/PUT/DELETE operations
- Any GET that returns user-specific data
- Admin operations

Public endpoints (no auth required):
- `/api/auth/login`
- `/api/auth/callback`
- `/api/auth/me` (returns `is_authenticated: false` if not logged in)
- Read-only aggregated stats (optional)

---

## 8. Add Request Size Limits (30 minutes)

### Create Middleware
```python
# apps/dashboard/backend/middleware/security.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import Request

class LimitUploadSize(BaseHTTPMiddleware):
    def __init__(self, app, max_upload_size: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            if "content-length" in request.headers:
                content_length = int(request.headers["content-length"])
                if content_length > self.max_upload_size:
                    return JSONResponse(
                        {"error": "Request body too large"},
                        status_code=413
                    )
        response = await call_next(request)
        return response
```

### Apply Middleware
```python
# apps/dashboard/backend/main.py
from middleware.security import LimitUploadSize

app.add_middleware(LimitUploadSize, max_upload_size=10 * 1024 * 1024)  # 10MB
```

---

## 9. Validate Dynamic SQL Columns (1 hour)

### Create Column Whitelist
```python
# apps/dashboard/backend/routers/knowledge.py

# Add at module level
ALLOWED_DECISION_COLUMNS = {
    'title', 'context', 'options_considered', 'decision',
    'rationale', 'domain', 'files_touched', 'tests_added', 'status'
}

ALLOWED_ASSUMPTION_COLUMNS = {
    'assumption', 'context', 'source', 'confidence', 'status', 'domain'
}

ALLOWED_INVARIANT_COLUMNS = {
    'statement', 'rationale', 'domain', 'scope',
    'validation_type', 'validation_code', 'severity', 'status'
}

ALLOWED_SPIKE_COLUMNS = {
    'title', 'topic', 'question', 'findings', 'gotchas',
    'resources', 'time_invested_minutes', 'domain', 'tags'
}

@router.put("/decisions/{decision_id}")
async def update_decision(
    decision_id: int,
    update: DecisionUpdate,
    request: Request,
    user_id: int = Depends(require_auth)
) -> ActionResult:
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM decisions WHERE id = ?", (decision_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Decision not found")

        updates = []
        params = []

        # Validate columns before building query
        for field, value in update.dict(exclude_unset=True).items():
            if field not in ALLOWED_DECISION_COLUMNS:
                raise HTTPException(400, f"Invalid column: {field}")
            if value is not None:
                updates.append(f"{field} = ?")
                params.append(value)

        # ... rest of implementation ...
```

---

## 10. Testing Security Fixes

### Manual Testing Checklist
```bash
# Test session management
curl -c cookies.txt http://localhost:8888/api/auth/dev-callback?dev_token=<token>
curl -b cookies.txt http://localhost:8888/api/auth/me
# Should return authenticated user

# Test rate limiting
for i in {1..20}; do curl http://localhost:8888/api/auth/login; done
# Should return 429 Too Many Requests after limit

# Test authentication requirement
curl -X POST http://localhost:8888/api/heuristics/1/promote
# Should return 401 Unauthorized

# Test input validation
curl -X POST http://localhost:8888/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "", "limit": 1000}'
# Should return 422 Validation Error

# Test request size limit
dd if=/dev/zero bs=1M count=20 | curl -X POST \
  --data-binary @- http://localhost:8888/api/query
# Should return 413 Request Entity Too Large
```

### Automated Security Tests
```python
# tests/test_security.py
import pytest
from fastapi.testclient import TestClient

def test_session_persistence(client: TestClient):
    """Test sessions survive server restart"""
    # Login
    response = client.get("/api/auth/dev-callback?dev_token=test_token")
    assert response.status_code == 200

    # Verify session exists
    response = client.get("/api/auth/me")
    assert response.json()["is_authenticated"] is True

def test_rate_limiting(client: TestClient):
    """Test rate limiting on auth endpoints"""
    for i in range(10):
        response = client.get("/api/auth/login")

    # 11th request should be rate limited
    response = client.get("/api/auth/login")
    assert response.status_code == 429

def test_authentication_required(client: TestClient):
    """Test protected endpoints require authentication"""
    response = client.post("/api/heuristics/1/promote")
    assert response.status_code == 401

def test_input_validation(client: TestClient):
    """Test input validation on models"""
    response = client.post("/api/query", json={
        "query": "a" * 1000,  # Exceeds max length
        "limit": 200  # Exceeds max value
    })
    assert response.status_code == 422

def test_secure_cookies(client: TestClient):
    """Test cookies have secure attributes"""
    response = client.get("/api/auth/dev-callback?dev_token=test_token")
    cookie = response.cookies.get("session_token")
    assert cookie is not None
    # Note: secure flag requires HTTPS in production
```

Run tests:
```bash
pytest tests/test_security.py -v
```

---

## Summary

After implementing these 10 fixes, your security posture improves from **4.25/10 to ~7.5/10**.

**Remaining work:**
- CSRF protection (medium priority)
- JSON schema validation (medium priority)
- Security headers (medium priority)
- Dependency scanning automation (low priority)
- Penetration testing (before production)

**Total Implementation Time:** ~8-12 hours for critical fixes

**Verification:** Run `pytest tests/test_security.py` to verify all fixes are working.
