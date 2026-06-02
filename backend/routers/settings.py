"""系统设置路由"""

from urllib.parse import urlencode
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import Setting
from backend.main import templates
from backend.routers.auth import login_required

router = APIRouter(prefix="/settings", tags=["settings"])


def get_setting(db: Session, key: str, default: str = "") -> str:
    setting = db.query(Setting).filter(Setting.key == key).first()
    return setting.value if setting else default


def set_setting(db: Session, key: str, value: str):
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        db.add(setting)
    db.commit()


@router.get("")
async def settings_page(request: Request, db: Session = Depends(get_db)):
    login_required(request)
    return templates.TemplateResponse(request, "settings.html", {
        "deepseek_api_key": get_setting(db, "deepseek_api_key"),
        "boss_username": get_setting(db, "boss_username"),
        "boss_cookies": get_setting(db, "boss_cookies"),
        "daily_apply_limit": get_setting(db, "daily_apply_limit", "50"),
        "min_delay": get_setting(db, "min_delay", "3"),
        "max_delay": get_setting(db, "max_delay", "8"),
        "schedule_enabled": get_setting(db, "schedule_enabled", "false"),
        "schedule_time": get_setting(db, "schedule_time", "09:00"),
    })


@router.post("/save")
async def save_settings(
    request: Request,
    deepseek_api_key: str = Form(""),
    boss_username: str = Form(""),
    boss_cookies: str = Form(""),
    daily_apply_limit: str = Form("50"),
    min_delay: str = Form("3"),
    max_delay: str = Form("8"),
    schedule_enabled: str = Form("false"),
    schedule_time: str = Form("09:00"),
    db: Session = Depends(get_db),
):
    login_required(request)
    set_setting(db, "deepseek_api_key", deepseek_api_key)
    set_setting(db, "boss_username", boss_username)
    if boss_cookies.strip():
        set_setting(db, "boss_cookies", boss_cookies.strip())
    set_setting(db, "daily_apply_limit", daily_apply_limit)
    set_setting(db, "min_delay", min_delay)
    set_setting(db, "max_delay", max_delay)
    set_setting(db, "schedule_enabled", schedule_enabled)
    set_setting(db, "schedule_time", schedule_time)

    return RedirectResponse(url=f"/settings?{urlencode({'msg': '设置已保存', 'type': 'success'})}", status_code=302)


@router.post("/test-boss-login")
async def test_boss_login(
    request: Request,
    cookies: str = Form(""),
):
    login_required(request)
    if not cookies.strip():
        return JSONResponse({"ok": False, "error": "Cookie 为空"})

    try:
        from backend.services.boss_browser import BossBrowser

        async with BossBrowser() as boss:
            ok = await boss.login_with_cookies(cookies.strip())
            return JSONResponse({"ok": ok, "error": "" if ok else "Cookie 已过期或无效，请重新获取"})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)[:200]})
