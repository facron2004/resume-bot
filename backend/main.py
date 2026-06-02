"""ResumeBot - 自动投递简历系统"""

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, PackageLoader, select_autoescape
from starlette.templating import Jinja2Templates

from backend.config import settings
from backend.database.database import init_db

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

# 配置文件上传大小限制（50MB）
import starlette.routing
app.max_request_size = 50 * 1024 * 1024

# 模板引擎
templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# 静态文件
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 认证异常处理器 — 将 LoginRequired 异常转为登录页重定向
from backend.routers.auth import LoginRequired

@app.exception_handler(LoginRequired)
async def login_required_handler(request: Request, exc: LoginRequired):
    return RedirectResponse(url="/auth/login", status_code=302)

# 注册路由
from backend.routers import auth, profiles, resumes, jobs, applications, settings as settings_router
app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(resumes.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(settings_router.router)


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/")
async def root(request: Request):
    from backend.routers.auth import get_current_user
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=302)

    from sqlalchemy.orm import Session
    from backend.database.database import SessionLocal
    from backend.database.models import Application, Job

    db = SessionLocal()
    try:
        total_applications = db.query(Application).count()
        today_applications = db.query(Application).filter(
            Application.applied_at >= __import__('datetime').datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        interview_count = db.query(Application).filter(Application.status == "面试邀约").count()
        reply_count = db.query(Application).filter(
            Application.status.in_(["已沟通", "有回复", "面试邀约"])
        ).count()
        pending_jobs = db.query(Job).filter(Job.status == "待处理").count()

        return templates.TemplateResponse(request, "dashboard.html", {
            "total_applications": total_applications,
            "today_applications": today_applications,
            "interview_count": interview_count,
            "reply_count": reply_count,
            "pending_jobs": pending_jobs,
        })
    finally:
        db.close()
