"""Boss直聘 Playwright 自动化模块"""

import asyncio
import json
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.config import settings


class BossBrowser:
    """Boss直聘 浏览器自动化"""

    BASE_URL = "https://www.zhipin.com"
    COOKIE_FILE = "boss_cookies.json"

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.daily_count = 0
        self.daily_limit = settings.BOSS_DAILY_APPLY_LIMIT
        self.min_delay = settings.BOSS_MIN_DELAY_SECONDS
        self.max_delay = settings.BOSS_MAX_DELAY_SECONDS

    async def _load_settings(self):
        """从数据库加载设置"""
        from backend.database.database import SessionLocal
        from backend.database.models import Setting
        db = SessionLocal()
        try:
            for key in ["daily_apply_limit", "min_delay", "max_delay"]:
                s = db.query(Setting).filter(Setting.key == key).first()
                if s and s.value:
                    if key == "daily_apply_limit":
                        self.daily_limit = int(s.value)
                    elif key == "min_delay":
                        self.min_delay = float(s.value)
                    elif key == "max_delay":
                        self.max_delay = float(s.value)
        finally:
            db.close()

    async def _random_delay(self, min_s: float = None, max_s: float = None):
        """随机延迟，模拟人类行为"""
        await asyncio.sleep(random.uniform(
            min_s or self.min_delay,
            max_s or self.max_delay,
        ))

    async def start(self):
        """启动浏览器"""
        from playwright.async_api import async_playwright

        self.playwright = await async_playwright().start()
        user_agent = random.choice(settings.BOSS_USER_AGENTS)
        cookie_path = Path(settings.DATA_DIR) / self.COOKIE_FILE

        self.browser = await self.playwright.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )

        self.context = await self.browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1366, "height": 768},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )

        # 注入反检测脚本
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh'] });
        """)

        # 尝试加载 Cookie
        if cookie_path.exists():
            cookies = json.loads(cookie_path.read_text(encoding="utf-8"))
            await self.context.add_cookies(cookies)

        self.page = await self.context.new_page()
        await self._load_settings()

    async def is_logged_in(self) -> bool:
        """检查是否已登录"""
        try:
            await self.page.goto(f"{self.BASE_URL}/web/chat", wait_until="domcontentloaded", timeout=15000)
            await self._random_delay(1, 2)
            # 检查是否有登录相关元素
            content = await self.page.content()
            return "login" not in self.page.url.lower() and "passport" not in self.page.url.lower()
        except Exception:
            return False

    async def login_by_qrcode(self):
        """二维码登录"""
        await self.page.goto(f"{self.BASE_URL}/web/user/?ka=header-login", wait_until="domcontentloaded")
        await self._random_delay(1, 2)

        # 等待用户扫码，检测登录成功
        try:
            await self.page.wait_for_url(
                lambda url: "web/chat" in url or "web/geek" in url,
                timeout=120000,  # 2分钟等待扫码
            )
            # 保存 Cookie
            cookies = await self.context.cookies()
            cookie_path = Path(settings.DATA_DIR) / self.COOKIE_FILE
            cookie_path.write_text(json.dumps(cookies, ensure_ascii=False), encoding="utf-8")
            return True
        except Exception:
            return False

    async def login_with_cookies(self, cookies_str: str):
        """使用 Cookie 字符串登录"""
        import http.cookies
        simple_cookies = http.cookies.SimpleCookie()
        simple_cookies.load(cookies_str)

        cookies = []
        for key, morsel in simple_cookies.items():
            cookies.append({
                "name": key,
                "value": morsel.value,
                "domain": ".zhipin.com",
                "path": "/",
            })

        await self.context.add_cookies(cookies)
        cookie_path = Path(settings.DATA_DIR) / self.COOKIE_FILE
        cookie_path.write_text(json.dumps(cookies, ensure_ascii=False), encoding="utf-8")
        return await self.is_logged_in()

    async def search_jobs(self, keyword: str, city: str = "") -> list[dict]:
        """搜索职位，返回职位列表"""
        search_url = f"{self.BASE_URL}/web/geek/jobs?query={keyword}"
        if city:
            search_url += f"&city={city}"

        await self.page.goto(search_url, wait_until="domcontentloaded")
        await self._random_delay(2, 4)

        jobs = []
        try:
            # 等待职位列表加载
            await self.page.wait_for_selector(".job-list-box", timeout=10000)
            await self._random_delay(1, 2)

            # 模拟滚动
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self._random_delay(1, 2)

            # 提取职位信息
            items = await self.page.query_selector_all(".job-card-wrapper")
            for item in items[:20]:  # 每页最多20个
                try:
                    title_el = await item.query_selector(".job-name")
                    company_el = await item.query_selector(".company-name")
                    salary_el = await item.query_selector(".salary")
                    info_el = await item.query_selector(".job-info")
                    link_el = await item.query_selector("a.job-card-wrapper")

                    title = await title_el.inner_text() if title_el else ""
                    company = await company_el.inner_text() if company_el else ""
                    salary = await salary_el.inner_text() if salary_el else ""
                    href = await link_el.get_attribute("href") if link_el else ""

                    # 解析薪资
                    salary_min, salary_max = self._parse_salary(salary)

                    # 获取职位 ID
                    job_id = ""
                    if href:
                        match = re.search(r'job_detail/([^.?]+)', href)
                        if match:
                            job_id = match.group(1)

                    jobs.append({
                        "job_id": job_id or title,
                        "title": title.strip(),
                        "company": company.strip(),
                        "salary_min": salary_min,
                        "salary_max": salary_max,
                        "salary_text": salary.strip(),
                        "job_url": f"{self.BASE_URL}{href}" if href else "",
                    })
                except Exception:
                    continue
        except Exception:
            pass

        return jobs

    async def get_job_detail(self, job_url: str) -> dict:
        """获取职位详情"""
        try:
            await self.page.goto(job_url, wait_until="domcontentloaded")
            await self._random_delay(1, 2)

            info = {}

            # 职位描述
            jd_el = await self.page.query_selector(".job-sec-text")
            if jd_el:
                info["jd_text"] = await jd_el.inner_text()

            # 职位标签
            tags_el = await self.page.query_selector_all(".job-tags span")
            if tags_el:
                info["tags"] = [await t.inner_text() for t in tags_el]

            return info
        except Exception as e:
            return {"error": str(e)}

    async def send_greeting(self, job_id: str, greeting: str) -> bool:
        """发送打招呼消息"""
        try:
            # 打开沟通页面
            chat_url = f"{self.BASE_URL}/web/geek/job/{job_id}"
            await self.page.goto(chat_url, wait_until="domcontentloaded")
            await self._random_delay(2, 3)

            # 查找打招呼按钮
            greet_btn = await self.page.query_selector(".btn-startchat")
            if greet_btn:
                await greet_btn.click()
                await self._random_delay(1, 2)

                # 输入框
                input_el = await self.page.query_selector(".chat-input")
                if input_el:
                    await input_el.fill(greeting)
                    await self._random_delay(0.5, 1)

                    send_btn = await self.page.query_selector(".btn-send")
                    if send_btn:
                        await send_btn.click()
                        self.daily_count += 1
                        return True
            return False
        except Exception:
            return False

    async def get_chat_messages(self) -> list[dict]:
        """获取沟通记录"""
        try:
            await self.page.goto(f"{self.BASE_URL}/web/chat", wait_until="domcontentloaded")
            await self._random_delay(2, 3)

            messages = []
            items = await self.page.query_selector_all(".chat-msg-item")
            for item in items:
                try:
                    text_el = await item.query_selector(".msg-text")
                    time_el = await item.query_selector(".msg-time")
                    if text_el:
                        messages.append({
                            "text": await text_el.inner_text(),
                            "time": await time_el.inner_text() if time_el else "",
                        })
                except Exception:
                    continue
            return messages
        except Exception:
            return []

    def _parse_salary(self, salary_text: str) -> tuple[int, int]:
        """解析薪资文本，返回 (min, max) 单位 K"""
        match = re.search(r'(\d+)[Kk]?[-~到](\d+)[Kk]', salary_text)
        if match:
            return int(match.group(1)), int(match.group(2))
        match = re.search(r'(\d+)[Kk]', salary_text)
        if match:
            return int(match.group(1)), int(match.group(1))
        return 0, 0

    async def close(self):
        """关闭浏览器"""
        if self.context:
            # 保存最新的 Cookie
            try:
                cookies = await self.context.cookies()
                cookie_path = Path(settings.DATA_DIR) / self.COOKIE_FILE
                cookie_path.write_text(json.dumps(cookies, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.close()
