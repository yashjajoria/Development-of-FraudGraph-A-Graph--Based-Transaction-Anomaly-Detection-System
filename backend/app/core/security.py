"""Demo JWT auth (users analyst/admin/viewer) + roles + per-user rate limit."""
import hmac
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

ROLES = {"analyst": "analyst", "admin": "admin", "viewer": "viewer"}  # username -> role
bearer = HTTPBearer(auto_error=False)


@dataclass
class User:
    username: str
    role: str


def login(username: str, password: str) -> str | None:
    if username not in ROLES or not hmac.compare_digest(password.encode(), settings.demo_password.encode()):
        return None
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_hours)
    return jwt.encode({"sub": username, "role": ROLES[username], "exp": exp}, settings.jwt_secret, "HS256")


def current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer)) -> User:
    if not cred:
        raise HTTPException(401, "Not authenticated")
    try:
        p = jwt.decode(cred.credentials, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    return User(p["sub"], p["role"])


def require_roles(*roles: str):
    def dep(u: User = Depends(current_user)) -> User:
        if u.role not in roles:
            raise HTTPException(403, f"Requires role: {' or '.join(roles)}")
        return u
    return dep


_hits: dict[str, deque] = defaultdict(deque)


def check_rate_limit(user: str) -> None:
    # ponytail: in-memory sliding window, per process; use Redis if running multiple workers
    now, q = time.monotonic(), _hits[user]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= settings.rate_limit_per_min:
        raise HTTPException(429, "Rate limit: 20 messages per minute", headers={"Retry-After": "60"})
    q.append(now)
