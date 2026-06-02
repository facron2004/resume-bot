"""职位搜索与管理路由"""

from urllib.parse import urlencode
from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import Job, JobSearchConfig, User
from backend.main import templates
from backend.routers.auth import login_required
from fastapi.responses import JSONResponse

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


@router.post("/scrape")
async def start_scrape(request: Request, db: Session = Depends(get_db)):
    login_required(request)
    import asyncio
    import threading

    # Check for cookie
    from backend.database.database import SessionLocal
    from backend.database.models import Setting

    cookies = db.query(Setting).filter(Setting.key == "boss_cookies").first()
    if not cookies or not cookies.value.strip():
        return JSONResponse({"started": False, "error": "请先在系统设置中配置 Boss直聘 Cookie"})

    api_key = db.query(Setting).filter(Setting.key == "deepseek_api_key").first()
    if not api_key or not api_key.value.strip():
        return JSONResponse({"started": False, "error": "请先在系统设置中配置 DeepSeek API Key"})

    # Get active search configs
    configs = db.query(JobSearchConfig).filter(JobSearchConfig.is_active == True).all()
    if not configs:
        return JSONResponse({"started": False, "error": "请先在搜索配置中添加并启用一个搜索配置"})

    def _run_scrape():
        import asyncio as aio
        loop = aio.new_event_loop()
        aio.set_event_loop(loop)
        try:
            loop.run_until_complete(_do_scrape(configs, cookies.value))
        finally:
            loop.close()

    threading.Thread(target=_run_scrape, daemon=True).start()
    return JSONResponse({"started": True})


async def _do_scrape(configs, cookies_str):
    """Background scraping task"""
    from backend.services.boss_browser import BossBrowser
    from backend.services.job_matcher import JobMatcher
    from backend.database.database import SessionLocal as SL

    async with BossBrowser() as boss:
        ok = await boss.login_with_cookies(cookies_str)
        if not ok:
            return

        matcher = JobMatcher()

        for cfg in configs:
            keywords = [k.strip() for k in cfg.keywords.split(",") if k.strip()]
            for kw in keywords:
                try:
                    jobs_data = await boss.search_jobs(kw, cfg.city or "")
                    for jd in jobs_data:
                        db2 = SL()
                        try:
                            existing = db2.query(Job).filter(Job.job_id == jd["job_id"]).first()
                            if not existing:
                                job = Job(
                                    job_id=jd["job_id"],
                                    title=jd["title"],
                                    company=jd["company"],
                                    city=cfg.city or "",
                                    salary_min=jd.get("salary_min", 0),
                                    salary_max=jd.get("salary_max", 0),
                                    job_url=jd.get("job_url", ""),
                                )
                                db2.add(job)
                                db2.commit()
                                db2.refresh(job)
                                try:
                                    detail = await boss.get_job_detail(jd.get("job_url", ""))
                                    if detail.get("jd_text"):
                                        job.jd_text = detail["jd_text"]
                                        user = db2.query(User).first()
                                        if user:
                                            score, reason = await matcher.match_job(user, job.title, job.company, detail["jd_text"])
                                            job.match_score = score
                                            job.match_reason = reason
                                            db2.commit()
                                except Exception:
                                    pass
                        finally:
                            db2.close()
                        await boss._random_delay(1, 3)
                except Exception:
                    continue
