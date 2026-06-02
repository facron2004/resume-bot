"""SQLAlchemy 数据模型"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, Boolean, JSON
from sqlalchemy.orm import relationship

from backend.database.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), default="")
    phone = Column(String(20), default="")
    email = Column(String(200), default="")
    title = Column(String(200), default="")          # 当前职位/目标职位
    years_exp = Column(Integer, default=0)            # 工作年限
    education = Column(String(50), default="")         # 最高学历
    salary_current = Column(String(50), default="")    # 当前薪资
    salary_expected = Column(String(50), default="")   # 期望薪资
    skills = Column(Text, default="[]")                # JSON array of skills
    summary = Column(Text, default="")                 # 个人简介/自我评价
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    work_experiences = relationship("WorkExperience", back_populates="user", cascade="all, delete-orphan")
    educations = relationship("Education", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")


class WorkExperience(Base):
    __tablename__ = "work_experiences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company = Column(String(200), default="")
    position = Column(String(200), default="")
    start_date = Column(String(20), default="")       # "2020-01"
    end_date = Column(String(20), default="")         # "2023-06" or "至今"
    description = Column(Text, default="")             # 工作描述
    technologies = Column(String(500), default="")     # 使用的技术栈
    is_current = Column(Boolean, default=False)

    user = relationship("User", back_populates="work_experiences")


class Education(Base):
    __tablename__ = "educations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    school = Column(String(200), default="")
    major = Column(String(200), default="")
    degree = Column(String(50), default="")            # 本科/硕士/博士
    start_date = Column(String(20), default="")
    end_date = Column(String(20), default="")
    gpa = Column(String(10), default="")

    user = relationship("User", back_populates="educations")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), default="")
    role = Column(String(100), default="")
    technologies = Column(String(500), default="")
    description = Column(Text, default="")
    start_date = Column(String(20), default="")
    end_date = Column(String(20), default="")
    link = Column(String(500), default="")             # 项目链接

    user = relationship("User", back_populates="projects")


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), default="")              # 简历名称
    target_position = Column(String(200), default="")   # 目标职位
    target_industry = Column(String(200), default="")   # 目标行业
    content = Column(JSON, default=dict)                # 完整的简历内容（JSON）
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="resumes")


class JobSearchConfig(Base):
    __tablename__ = "job_search_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), default="默认搜索")       # 配置名称
    keywords = Column(String(500), default="")           # 关键词，逗号分隔
    city = Column(String(100), default="")               # 城市
    min_salary = Column(String(50), default="")
    max_salary = Column(String(50), default="")
    experience_level = Column(String(50), default="")
    education_required = Column(String(50), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), unique=True, nullable=False)   # Boss直聘 职位 ID
    title = Column(String(200), default="")
    company = Column(String(200), default="")
    company_size = Column(String(100), default="")
    city = Column(String(50), default="")
    area = Column(String(100), default="")
    salary_min = Column(Integer, default=0)
    salary_max = Column(Integer, default=0)
    education_required = Column(String(50), default="")
    experience_required = Column(String(50), default="")
    jd_text = Column(Text, default="")                           # 职位描述全文
    skills_required = Column(Text, default="")                   # JSON array
    match_score = Column(Float, default=0.0)                     # AI 匹配度 0-100
    match_reason = Column(Text, default="")
    status = Column(String(20), default="待处理")                 # 待处理/已投递/不合适
    job_url = Column(String(500), default="")
    source = Column(String(50), default="boss")
    created_at = Column(DateTime, default=datetime.now)
    scraped_at = Column(DateTime, default=datetime.now)

    application = relationship("Application", back_populates="job", uselist=False)


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    chat_content = Column(Text, default="")                      # 沟通过程
    greeting_message = Column(Text, default="")                  # 打招呼消息
    status = Column(
        String(20), default="已投递",
        comment="已投递/已读/已沟通/有回复/不合适/面试邀约"
    )
    applied_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    job = relationship("Job", back_populates="application")
    resume = relationship("Resume")


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, default="")
    description = Column(String(500), default="")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
