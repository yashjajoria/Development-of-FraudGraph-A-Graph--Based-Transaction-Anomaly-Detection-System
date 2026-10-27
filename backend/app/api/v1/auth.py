from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from fastapi import Depends

from app.core.security import ROLES, User, current_user, login

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/login")
def do_login(body: LoginIn):
    token = login(body.username, body.password)
    if not token:
        raise HTTPException(401, "Invalid credentials")
    return {"access_token": token, "token_type": "bearer", "role": ROLES[body.username]}


@router.get("/me")
def me(u: User = Depends(current_user)):
    return {"username": u.username, "role": u.role}
