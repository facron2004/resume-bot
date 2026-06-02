"""投递记录管理路由"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import Application, Job
from backend.main import templates
from backend.routers.auth import login_required

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("")
async def application_list(
    request: Request,
    page: int = Query(1, ge=1),
    status: str = Query(""),
    db: Session = Depends(get_db),
):
    login_required(request)

    page_size = 20
    query = db.query(Application)

    if status:
        query = query.filter(Application.status == status)

    query = query.order_by(Application.applied_at.desc())
    total = query.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    applications = query.offset((page - 1) * page_size).limit(page_size).all()

    return templates.TemplateResponse(request, "applications/list.html", {
        "applications": applications,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "status": status,
    })
