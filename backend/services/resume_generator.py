"""DeepSeek AI 简历生成服务"""

import json
from typing import Any

import httpx

from backend.config import settings
from backend.database.models import User


class ResumeGenerator:
    """基于 DeepSeek API 的简历生成器"""

    def __init__(self):
        self.api_key = ""
        self.api_base = settings.DEEPSEEK_API_BASE
        self.model = settings.DEEPSEEK_MODEL

    async def _load_api_key(self):
        """从数据库加载 API Key"""
        if self.api_key:
            return
        from backend.database.database import SessionLocal
        from backend.database.models import Setting
        db = SessionLocal()
        try:
            setting = db.query(Setting).filter(Setting.key == "deepseek_api_key").first()
            if setting and setting.value:
                self.api_key = setting.value
        finally:
            db.close()

    async def _call_deepseek(self, messages: list[dict], temperature: float = 0.7) -> str:
        """调用 DeepSeek API"""
        await self._load_api_key()
        if not self.api_key:
            return json.dumps({"error": "请先在系统设置中配置 DeepSeek API Key"})

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": 4096,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def generate_resume(self, user: User, target_position: str, target_industry: str = "") -> dict[str, Any]:
        """根据用户信息生成针对目标职位的简历"""
        # 解析技能
        try:
            skills_list = json.loads(user.skills) if isinstance(user.skills, str) else (user.skills or [])
        except (json.JSONDecodeError, TypeError):
            skills_list = []

        # 构建用户信息描述
        user_info = f"""
个人信息：
- 姓名：{user.name or '[姓名]'}
- 电话：{user.phone or ''}
- 邮箱：{user.email or ''}
- 当前/目标职位：{user.title or target_position}
- 工作年限：{user.years_exp} 年
- 学历：{user.education or ''}
- 期望薪资：{user.salary_expected or ''}
- 技能：{', '.join(skills_list)}
- 自我评价：{user.summary or ''}
"""

        # 工作经历
        if user.work_experiences:
            user_info += "\n工作经历：\n"
            for exp in user.work_experiences:
                user_info += f"- {exp.company} | {exp.position} | {exp.start_date}~{exp.end_date or '至今'}\n  描述：{exp.description or ''}\n  技术栈：{exp.technologies or ''}\n"

        # 项目经历
        if user.projects:
            user_info += "\n项目经历：\n"
            for proj in user.projects:
                user_info += f"- {proj.name}（{proj.role}）| {proj.start_date}~{proj.end_date or ''}\n  描述：{proj.description or ''}\n  技术栈：{proj.technologies or ''}\n"

        # 教育经历
        if user.educations:
            user_info += "\n教育背景：\n"
            for edu in user.educations:
                user_info += f"- {edu.school} | {edu.major} | {edu.degree} | {edu.start_date}~{edu.end_date or ''}\n"

        system_prompt = """你是一位专业的简历优化顾问。根据用户提供的个人信息和目标职位，生成一份高质量的定制简历。

请严格按照以下 JSON 格式输出（不要包含 markdown 代码块标记）：

{
  "name": "姓名",
  "phone": "电话",
  "email": "邮箱",
  "title": "目标职位",
  "summary": "简短有力的自我评价，突出与目标职位的匹配度（100字以内）",
  "skills": ["技能1", "技能2", ...],
  "work_experiences": [
    {
      "company": "公司名",
      "position": "职位",
      "period": "时间段",
      "description": "工作描述，突出成果和量化指标"
    }
  ],
  "projects": [
    {
      "name": "项目名",
      "role": "角色",
      "period": "时间段",
      "description": "项目描述，突出技术难点和贡献",
      "technologies": "技术栈"
    }
  ],
  "educations": [
    {
      "school": "学校名",
      "major": "专业",
      "degree": "学历",
      "period": "时间段"
    }
  ]
}

要求：
1. 优化工作/项目描述，突出与目标职位的相关性
2. 使用 STAR 法则（情境-任务-行动-结果）描述经历
3. 尽量量化成果（提升XX%、节省XX成本等）
4. 自我评价要针对目标职位定制
5. 不要编造不存在的信息，在原有基础上优化表述"""

        user_prompt = f"目标职位：{target_position}\n目标行业：{target_industry or '不限'}\n\n用户信息：\n{user_info}"

        content = await self._call_deepseek([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])

        # 解析返回的 JSON
        try:
            # 清理可能的 markdown 代码块标记
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0]
            content = content.strip()
            return json.loads(content)
        except json.JSONDecodeError:
            return {"error": "AI 返回格式错误", "raw": content}

    async def generate_greeting(self, job_title: str, company: str, jd_text: str, user_name: str) -> str:
        """生成个性化打招呼消息"""
        prompt = f"""你是 {user_name}，正在 Boss直聘 上找工作。请根据以下职位信息，生成一段简短、真诚的打招呼消息：

职位：{job_title}
公司：{company}
职位描述：{jd_text[:500]}

要求：
- 语气自然真诚，像是真人发的
- 简单提一下自己为什么适合这个职位
- 不要夸大其词
- 控制在 50 字以内
- 不要包含敏感信息（电话、微信等）"""

        content = await self._call_deepseek([
            {"role": "system", "content": "你是一位求职者，正在BOSS直聘上找工作。请直接输出打招呼内容，不要加引号。输出不要包含任何前缀或后缀。"},
            {"role": "user", "content": prompt},
        ], temperature=0.8)

        return content.strip().strip('"').strip("'")

    async def enhance_from_text(self, raw_text: str, target_position: str = "", user_name: str = "") -> dict[str, Any]:
        """从解析的简历文本中用 AI 优化为结构化简历"""
        system_prompt = """你是一位专业的简历优化顾问。请根据用户提供的简历文本，提取信息并优化为结构化 JSON 格式。

请严格按照以下 JSON 格式输出（不要包含 markdown 代码块标记）：

{
  "name": "姓名",
  "phone": "电话",
  "email": "邮箱",
  "title": "目标/当前职位",
  "summary": "简短有力的自我评价（100字以内）",
  "skills": ["技能1", "技能2", ...],
  "work_experiences": [
    {
      "company": "公司名",
      "position": "职位",
      "period": "时间段",
      "description": "工作描述，突出成果和量化指标"
    }
  ],
  "projects": [
    {
      "name": "项目名",
      "role": "角色",
      "period": "时间段",
      "description": "项目描述",
      "technologies": "技术栈"
    }
  ],
  "educations": [
    {
      "school": "学校名",
      "major": "专业",
      "degree": "学历",
      "period": "时间段"
    }
  ],
  "source": "uploaded"
}

要求：
1. 从文本中提取所有可识别的信息
2. 优化描述语言，使用 STAR 法则改写
3. 尽量量化成果
4. 不要编造原文中不存在的信息
5. 如果文本中有明显的个人信息（电话、邮箱等），请提取"""

        user_prompt = f"目标职位：{target_position or '未指定'}\n\n简历原文：\n{raw_text[:6000]}"

        content = await self._call_deepseek([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])

        try:
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0]
            content = content.strip()
            result = json.loads(content)
            result["raw_text"] = raw_text[:5000]
            return result
        except json.JSONDecodeError:
            return {
                "raw_text": raw_text[:5000],
                "error": "AI 解析失败，已保留原始文本",
                "name": user_name or "上传简历",
            }

    async def edit_resume(self, current_content: dict[str, Any], instruction: str, user: User = None) -> dict[str, Any]:
        """根据用户指令 AI 编辑现有简历"""
        current_json = json.dumps(current_content, ensure_ascii=False, indent=2)

        system_prompt = """你是一位专业的简历优化顾问。用户会提供当前的简历 JSON 和修改要求。
请根据要求修改简历内容，保持 JSON 格式完整。

必须保留所有原有字段结构，只修改用户要求的部分。
工作/项目描述请用 STAR 法则优化并量化成果。
不要编造用户信息中不存在的内容。

请直接输出修改后的完整 JSON，不要包含 markdown 代码块标记。"""

        user_prompt = f"""修改要求：{instruction}

当前简历 JSON：
{current_json}"""

        content = await self._call_deepseek([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ], temperature=0.7)

        try:
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0]
            content = content.strip()
            return json.loads(content)
        except json.JSONDecodeError:
            return {**current_content, "error": "AI 编辑失败，内容未变更"}

    async def match_job(self, user: User, job_title: str, company: str, jd_text: str) -> tuple[float, str]:
        """评估职位匹配度"""
        try:
            skills_list = json.loads(user.skills) if isinstance(user.skills, str) else (user.skills or [])
        except (json.JSONDecodeError, TypeError):
            skills_list = []

        prompt = f"""请评估以下求职者与职位的匹配度。

【求职者信息】
- 当前/目标职位：{user.title or '未设置'}
- 工作年限：{user.years_exp} 年
- 最高学历：{user.education or '未设置'}
- 技能：{', '.join(skills_list) if skills_list else '未设置'}
- 自我评价：{user.summary or '未设置'}

【职位信息】
- 职位：{job_title}
- 公司：{company}
- 职位描述：{jd_text[:1000]}

请输出 JSON 格式（不要 markdown 标记）：
{{
  "score": 0-100的整数，
  "reason": "简要分析匹配理由（50字以内）"
}}

评分标准：
- 90-100：完美匹配，技能和经验高度吻合
- 70-89：较好匹配，核心技能匹配
- 50-69：部分匹配，需要补充某些技能
- 0-49：匹配度低"""

        content = await self._call_deepseek([
            {"role": "system", "content": "你是一位专业的招聘顾问，负责评估求职者与职位的匹配度。"},
            {"role": "user", "content": prompt},
        ], temperature=0.3)

        # 解析评分结果
        try:
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0]
            content = content.strip()
            result = json.loads(content)
            score = min(100, max(0, int(result.get("score", 0))))
            reason = result.get("reason", "")
            return score, reason
        except (json.JSONDecodeError, ValueError, KeyError):
            return 0.0, "AI 评分失败"
