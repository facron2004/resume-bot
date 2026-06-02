"""简历管理路由 - 支持 AI 生成、PDF/DOCX 上传、AI 编辑"""

import json
from urllib.parse import urlencode
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import Resume, User
from backend.main import templates
from backend.routers.auth import login_required
from backend.services.resume_generator import ResumeGenerator
from backend.services.resume_parser import ResumeParser

router = APIRouter(prefix="/resumes", tags=["resumes"])


def _flash(path: str, msg: str, type_: str = "success") -> str:
    return f"{path}?{urlencode({'msg': msg, 'type': type_})}"


@router.get("")
async def resume_list(request: Request, db: Session = Depends(get_db)):
    login_required(request)
    resumes = db.query(Resume).order_by(Resume.updated_at.desc()).all()
    return templates.TemplateResponse(request, "resumes/list.html", {"resumes": resumes})


@router.get("/create")
async def create_resume_page(request: Request, db: Session = Depends(get_db)):
    login_required(request)
    user = db.query(User).first()
    return templates.TemplateResponse(request, "resumes/create.html", {"user": user})


# --- AI 生成简历 ---
@router.post("/generate")
async def generate_resume(
    request: Request,
    target_position: str = Form(""),
    target_industry: str = Form(""),
    name: str = Form(""),
    db: Session = Depends(get_db),
):
    login_required(request)
    user = db.query(User).first()
    if not user:
        return RedirectResponse(url="/profiles", status_code=302)

    generator = ResumeGenerator()
    resume_content = await generator.generate_resume(user, target_position, target_industry)

    resume = Resume(
        user_id=user.id,
        name=name or f"{target_position}简历",
        target_position=target_position,
        target_industry=target_industry,
        content=resume_content,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return RedirectResponse(url=_flash(f"/resumes/{resume.id}/preview", "简历已生成"), status_code=302)


# --- 上传简历文件 (PDF/DOCX) ---
@router.post("/upload")
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    target_position: str = Form(""),
    name: str = Form(""),
    use_ai: bool = Form(True),
    db: Session = Depends(get_db),
):
    login_required(request)
    user = db.query(User).first()
    if not user:
        user = User()
        db.add(user)
        db.commit()
        db.refresh(user)

    # 检查文件类型
    filename = file.filename or "resume.pdf"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("pdf", "docx", "doc"):
        return templates.TemplateResponse(request, "resumes/create.html", {
            "user": user,
            "error": f"不支持的文件格式: .{ext}，仅支持 PDF 和 DOCX",
        })

    # 读取并解析文件
    content = await file.read()
    parser = ResumeParser()
    saved_path = await parser.save_upload(content, filename)
    raw_text = await parser.parse_file(saved_path)

    if use_ai:
        # AI 优化简历内容
        generator = ResumeGenerator()
        resume_content = await generator.enhance_from_text(
            raw_text=raw_text,
            target_position=target_position or "",
            user_name=name or "",
        )
    else:
        # 直接使用解析结果
        resume_content = await parser.extract_structured_data(raw_text)
        if target_position:
            resume_content["title"] = target_position

    resume = Resume(
        user_id=user.id,
        name=name or f"上传简历 - {filename}",
        target_position=target_position or resume_content.get("title", ""),
        content=resume_content,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return RedirectResponse(url=_flash(f"/resumes/{resume.id}/preview", "简历已上传并优化"), status_code=302)


# --- AI 编辑简历 ---
@router.post("/{resume_id}/ai-edit")
async def ai_edit_resume(
    request: Request,
    resume_id: int,
    edit_instruction: str = Form(""),
    db: Session = Depends(get_db),
):
    login_required(request)
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        return RedirectResponse(url="/resumes", status_code=302)

    user = db.query(User).first()
    generator = ResumeGenerator()

    updated_content = await generator.edit_resume(
        current_content=resume.content,
        instruction=edit_instruction,
        user=user,
    )

    resume.content = updated_content
    resume.version = (resume.version or 1) + 1
    db.commit()
    return RedirectResponse(url=_flash(f"/resumes/{resume.id}/preview", "简历已更新"), status_code=302)


@router.get("/{resume_id}/preview")
async def preview_resume(request: Request, resume_id: int, db: Session = Depends(get_db)):
    login_required(request)
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        return RedirectResponse(url="/resumes", status_code=302)
    return templates.TemplateResponse(request, "resumes/preview.html", {"resume": resume})


@router.post("/{resume_id}/activate")
async def activate_resume(request: Request, resume_id: int, db: Session = Depends(get_db)):
    login_required(request)
    db.query(Resume).filter(Resume.is_active == True).update({"is_active": False})
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if resume:
        resume.is_active = True
        db.commit()
    return RedirectResponse(url=_flash("/resumes", "已设为使用中"), status_code=302)


@router.post("/{resume_id}/delete")
async def delete_resume(request: Request, resume_id: int, db: Session = Depends(get_db)):
    login_required(request)
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if resume:
        db.delete(resume)
        db.commit()
    return RedirectResponse(url=_flash("/resumes", "简历已删除"), status_code=302)
