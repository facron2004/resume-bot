"""职位搜索与管理路由"""

from urllib.parse import urlencode
from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import Job, JobSearchConfig, User
from backend.main import templates
from backend.routers.auth import login_required

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _jback(msg: str, path: str = "/jobs/config") -> str:
    return f"{path}?{urlencode({'msg': msg, 'type': 'success'})}"


@router.get("")
async def job_list(
    request: Request,
    page: int = Query(1, ge=1),
    status: str = Query(""),
    sort: str = Query("match_score"),
    db: Session = Depends(get_db),
):
    login_required(request)
    page_size = 20
    query = db.query(Job)

    if status:
        query = query.filter(Job.status == status)

    if sort == "match_score":
        query = query.order_by(Job.match_score.desc())
    else:
        query = query.order_by(Job.created_at.desc())

    total = query.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    jobs = query.offset((page - 1) * page_size).limit(page_size).all()

    return templates.TemplateResponse(request, "jobs/list.html", {
        "jobs": jobs,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "status": status,
        "sort": sort,
    })


@router.get("/config")
async def search_config_page(request: Request, db: Session = Depends(get_db)):
    login_required(request)
    configs = db.query(JobSearchConfig).all()
    return templates.TemplateResponse(request, "jobs/config.html", {"configs": configs})


@router.post("/config/save")
async def save_search_config(
    request: Request,
    name: str = Form(""),
    keywords: str = Form(""),
    city: str = Form(""),
    min_salary: str = Form(""),
    max_salary: str = Form(""),
    experience_level: str = Form(""),
    education_required: str = Form(""),
    db: Session = Depends(get_db),
):
    login_required(request)
    user = db.query(User).first()
    if not user:
        user = User()
        db.add(user)
        db.commit()
        db.refresh(user)

    config = JobSearchConfig(
        user_id=user.id,
        name=name,
        keywords=keywords,
        city=city,
        min_salary=min_salary,
        max_salary=max_salary,
        experience_level=experience_level,
        education_required=education_required,
    )
    db.add(config)
    db.commit()
    return RedirectResponse(url=_jback("搜索配置已保存"), status_code=302)


@router.post("/config/{config_id}/delete")
async def delete_search_config(request: Request, config_id: int, db: Session = Depends(get_db)):
    login_required(request)
    config = db.query(JobSearchConfig).filter(JobSearchConfig.id == config_id).first()
    if config:
        db.delete(config)
        db.commit()
    return RedirectResponse(url=_jback("配置已删除"), status_code=302)


@router.post("/config/{config_id}/toggle")
async def toggle_search_config(request: Request, config_id: int, db: Session = Depends(get_db)):
    login_required(request)
    config = db.query(JobSearchConfig).filter(JobSearchConfig.id == config_id).first()
    if config:
        config.is_active = not config.is_active
        db.commit()
    return RedirectResponse(url=_jback("配置状态已更新"), status_code=302)


@router.post("/{job_id}/update-status")
async def update_job_status(
    request: Request,
    job_id: int,
    status: str = Form(""),
    db: Session = Depends(get_db),
):
    login_required(request)
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        job.status = status
        db.commit()
    return RedirectResponse(url=_jback("已标记为不合适", "/jobs"), status_code=302)
