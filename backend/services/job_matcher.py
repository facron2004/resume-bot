"""DeepSeek AI 职位匹配服务"""

import json
from typing import Any

import httpx

from backend.config import settings
from backend.database.models import User


class JobMatcher:
    """基于 DeepSeek API 的职位匹配服务"""

    def __init__(self):
        self.api_key = ""
        self.api_base = settings.DEEPSEEK_API_BASE
        self.model = settings.DEEPSEEK_MODEL

    async def _load_api_key(self):
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

    async def _call_deepseek(self, messages: list[dict], temperature: float = 0.3) -> str:
        await self._load_api_key()
        if not self.api_key:
            return json.dumps({"error": "API Key 未配置"})

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
                    "max_tokens": 1024,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def match_job(self, user: User, job_title: str, company: str, jd_text: str) -> tuple[float, str]:
        """评分职位匹配度"""
        try:
            skills_list = json.loads(user.skills) if isinstance(user.skills, str) else (user.skills or [])
        except (json.JSONDecodeError, TypeError):
            skills_list = []

        prompt = f"""评估求职者与职位的匹配度，输出JSON。

【求职者】
目标: {user.title or '未设置'}
年限: {user.years_exp}年
学历: {user.education or '未设置'}
技能: {', '.join(skills_list) if skills_list else '未设置'}
简介: {user.summary or '未设置'}

【职位】
名称: {job_title}
公司: {company}
描述: {jd_text[:800]}

输出: {{"score": 0-100整数, "reason": "匹配理由（50字内）"}}"""

        content = await self._call_deepseek([
            {"role": "system", "content": "你是招聘顾问，评估求职匹配度。"},
            {"role": "user", "content": prompt},
        ])

        try:
            content = content.strip().strip("`").strip()
            if content.startswith("json"):
                content = content[4:].strip()
            result = json.loads(content)
            return min(100, max(0, int(result.get("score", 0)))), result.get("reason", "")
        except (json.JSONDecodeError, ValueError, KeyError):
            return 0.0, "评分失败"

    async def batch_match(self, user: User, jobs: list[dict]) -> list[dict]:
        """批量匹配职位"""
        results = []
        for job in jobs:
            score, reason = await self.match_job(
                user,
                job.get("title", ""),
                job.get("company", ""),
                job.get("jd_text", ""),
            )
            results.append({
                "job_id": job.get("id"),
                "score": score,
                "reason": reason,
            })
        return results
