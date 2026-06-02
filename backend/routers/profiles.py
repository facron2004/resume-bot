"""个人信息管理路由"""

import json
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import User, WorkExperience, Education, Project
from backend.main import templates
from backend.routers.auth import login_required

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _back(msg: str = "", type_: str = "success") -> str:
    """Build redirect path with flash message"""
    base = "/profiles"
    if msg:
        return f"{base}?{urlencode({'msg': msg, 'type': type_})}"
    return base


@router.get("")
async def profile_page(request: Request, db: Session = Depends(get_db)):
    login_required(request)
    user = db.query(User).first()
    if not user:
        user = User()
        db.add(user)
        db.commit()
        db.refresh(user)

    work_exps = db.query(WorkExperience).filter(WorkExperience.user_id == user.id).all()
    educations = db.query(Education).filter(Education.user_id == user.id).all()
    projects = db.query(Project).filter(Project.user_id == user.id).all()

    return templates.TemplateResponse(request, "profiles.html", {
        "user": user,
        "work_experiences": work_exps,
        "educations": educations,
        "projects": projects,
    })


@router.post("/save")
async def save_profile(
    request: Request,
    name: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    title: str = Form(""),
    years_exp: int = Form(0),
    education: str = Form(""),
    salary_current: str = Form(""),
    salary_expected: str = Form(""),
    skills: str = Form("[]"),
    summary: str = Form(""),
    db: Session = Depends(get_db),
):
    login_required(request)
    user = db.query(User).first()
    if not user:
        user = User()
        db.add(user)
        db.commit()
        db.refresh(user)

    user.name = name
    user.phone = phone
    user.email = email
    user.title = title
    user.years_exp = years_exp
    user.education = education
    user.salary_current = salary_current
    user.salary_expected = salary_expected
    user.skills = skills
    user.summary = summary
    db.commit()
    return RedirectResponse(url=_back("基本信息已保存"), status_code=302)


@router.post("/work-experience/add")
async def add_work_experience(
    request: Request,
    company: str = Form(""),
    position: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    description: str = Form(""),
    technologies: str = Form(""),
    is_current: bool = Form(False),
    db: Session = Depends(get_db),
):
    login_required(request)
    user = db.query(User).first()
    if not user:
        user = User()
        db.add(user)
        db.commit()
        db.refresh(user)

    exp = WorkExperience(
        user_id=user.id,
        company=company,
        position=position,
        start_date=start_date,
        end_date=end_date,
        description=description,
        technologies=technologies,
        is_current=is_current,
    )
    db.add(exp)
    db.commit()
    return RedirectResponse(url=_back(f"已添加 {company}"), status_code=302)


@router.post("/work-experience/{exp_id}/delete")
async def delete_work_experience(request: Request, exp_id: int, db: Session = Depends(get_db)):
    login_required(request)
    exp = db.query(WorkExperience).filter(WorkExperience.id == exp_id).first()
    if exp:
        db.delete(exp)
        db.commit()
    return RedirectResponse(url=_back("已删除工作经历"), status_code=302)


@router.post("/education/add")
async def add_education(
    request: Request,
    school: str = Form(""),
    major: str = Form(""),
    degree: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    gpa: str = Form(""),
    db: Session = Depends(get_db),
):
    login_required(request)
    user = db.query(User).first()
    if not user:
        user = User()
        db.add(user)
        db.commit()
        db.refresh(user)

    edu = Education(
        user_id=user.id,
        school=school,
        major=major,
        degree=degree,
        start_date=start_date,
        end_date=end_date,
        gpa=gpa,
    )
    db.add(edu)
    db.commit()
    return RedirectResponse(url=_back(f"已添加 {school}"), status_code=302)


@router.post("/education/{edu_id}/delete")
async def delete_education(request: Request, edu_id: int, db: Session = Depends(get_db)):
    login_required(request)
    edu = db.query(Education).filter(Education.id == edu_id).first()
    if edu:
        db.delete(edu)
        db.commit()
    return RedirectResponse(url=_back("已删除教育经历"), status_code=302)


@router.post("/project/add")
async def add_project(
    request: Request,
    name: str = Form(""),
    role: str = Form(""),
    technologies: str = Form(""),
    description: str = Form(""),
    start_date: str = Form(""),
    end_date: str = Form(""),
    link: str = Form(""),
    db: Session = Depends(get_db),
):
    login_required(request)
    user = db.query(User).first()
    if not user:
        user = User()
        db.add(user)
        db.commit()
        db.refresh(user)

    proj = Project(
        user_id=user.id,
        name=name,
        role=role,
        technologies=technologies,
        description=description,
        start_date=start_date,
        end_date=end_date,
        link=link,
    )
    db.add(proj)
    db.commit()
    return RedirectResponse(url=_back(f"已添加项目 {name}"), status_code=302)


@router.post("/project/{proj_id}/delete")
async def delete_project(request: Request, proj_id: int, db: Session = Depends(get_db)):
    login_required(request)
    proj = db.query(Project).filter(Project.id == proj_id).first()
    if proj:
        db.delete(proj)
        db.commit()
    return RedirectResponse(url=_back("已删除项目经历"), status_code=302)
