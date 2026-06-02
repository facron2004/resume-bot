# ResumeBot — AI 自动投递简历系统

基于 **FastAPI + Playwright + DeepSeek** 的 Boss直聘 自动化简历投递系统。支持 AI 简历生成、职位智能匹配、自动打招呼投递，提供 Web 管理界面全流程管控。

## 功能概览

| 模块 | 功能 |
|------|------|
| AI 简历生成 | 基于个人信息 + 目标岗位，DeepSeek 生成定制简历 |
| 简历管理 | 多版本简历管理、PDF/DOCX 上传解析、AI 在线编辑 |
| 职位抓取 | Playwright 自动搜索 Boss直聘 职位 |
| AI 匹配 | DeepSeek 对每个职位 JD 评估匹配度打分 |
| 自动投递 | 模拟人工操作：搜索 → 匹配 → 打招呼 → 投递 |
| 投递追踪 | 记录投递状态、沟通记录、数据统计 |
| 定时任务 | 每天定时执行搜索+投递 |

## 技术栈

- **后端**: Python FastAPI + SQLAlchemy + SQLite
- **自动化**: Playwright (浏览器自动化)
- **AI**: DeepSeek API (简历生成 / 职位匹配)
- **前端**: Jinja2 + Alpine.js + Tailwind CSS
- **调度**: APScheduler

## 快速开始

### 环境要求

- Python 3.10+
- Playwright 浏览器 (Chromium)

### 安装

```bash
# 克隆项目
git clone https://github.com/facron2004/resume-bot.git
cd resume-bot

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium

# 复制环境配置
cp .env.example .env
```

### 配置 `.env`

```env
# 必填：DeepSeek API Key (从 https://platform.deepseek.com 获取)
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx

# 可选覆盖默认值
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
SECRET_KEY=change-this-to-random-secret
```

### 启动

```bash
python start.py
```

打开 http://localhost:8000 ，默认账号 `admin` / `admin123`

### Docker 部署

```bash
docker-compose up -d
```

## 使用流程

1. **填写个人信息** — `/profiles` 录入工作经历、技能、教育背景
2. **AI 生成简历** — `/resumes/create` 输入目标职位，AI 生成定制简历
3. **配置 Boss 账号** — `/settings` 用浏览器扩展导出 Cookie 粘贴
4. **配置搜索** — `/jobs/config` 设置关键词、城市、薪资范围
5. **开始投递** — `/jobs` 点击抓取，AI 自动匹配+投递

## 项目结构

```
resume-bot/
├── start.py              # 启动入口
├── requirements.txt      # Python 依赖
├── backend/
│   ├── main.py           # FastAPI 应用
│   ├── config.py         # 配置管理
│   ├── database/
│   │   ├── database.py   # 数据库引擎
│   │   └── models.py     # ORM 模型
│   ├── routers/          # API 路由
│   │   ├── auth.py       # 认证
│   │   ├── profiles.py   # 个人信息
│   │   ├── resumes.py    # 简历管理
│   │   ├── jobs.py       # 职位搜索
│   │   ├── applications.py # 投递记录
│   │   └── settings.py   # 系统设置
│   ├── services/         # 业务服务
│   │   ├── boss_browser.py      # Playwright 自动化
│   │   ├── resume_generator.py  # DeepSeek 简历生成
│   │   ├── resume_parser.py     # PDF/DOCX 解析
│   │   ├── job_matcher.py       # AI 职位匹配
│   │   └── scheduler_service.py # 定时任务
│   ├── templates/        # Jinja2 模板
│   └── static/           # 静态资源
└── data/                 # 数据目录 (自动创建)
```

## 安全提示

- 数据库文件和上传的简历存储在 `data/` 目录
- 修改 `.env` 中的 `SECRET_KEY` 和 `ADMIN_PASSWORD`
- Cookie 凭证加密存储在数据库中
- 投递频率模拟人类行为，默认每天上限 50 次

## License

MIT
