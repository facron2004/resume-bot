"""用户认证路由"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.database import get_db
from backend.database.models import Setting

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequired(Exception):
    """Raised when authentication is required; caught by exception handler in main.py"""


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def get_current_user(request: Request) -> dict | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    return verify_token(token)


def login_required(request: Request):
    """Shared dependency: returns user payload or raises LoginRequired"""
    user = get_current_user(request)
    if not user:
        raise LoginRequired()
    return user


@router.get("/login")
async def login_page(request: Request):
    if get_current_user(request):
        return RedirectResponse(url="/", status_code=302)
    return templates_login(request)


def templates_login(request: Request):
    """渲染登录页面"""
    from fastapi.responses import HTMLResponse
    from backend.main import templates
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
):
    if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
        token = create_access_token({"sub": username})
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            expires=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
        return response
    from fastapi.responses import HTMLResponse
    from backend.main import templates
    return templates.TemplateResponse(request, "login.html", {"error": "用户名或密码错误"})


@router.get("/logout")
async def logout():
    resp = RedirectResponse(url="/auth/login", status_code=302)
    resp.delete_cookie("access_token")
    return resp
