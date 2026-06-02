"""APScheduler 定时任务服务"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.database.database import SessionLocal
from backend.database.models import Setting

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def auto_apply_job():
    """定时自动投递任务"""
    logger.info("开始执行自动投递任务...")

    from backend.database.models import Job, Resume, User, Application
    from backend.services.boss_browser import BossBrowser
    from backend.services.resume_generator import ResumeGenerator

    db = SessionLocal()
    try:
        # 检查定时任务是否启用
        setting = db.query(Setting).filter(Setting.key == "schedule_enabled").first()
        if not setting or setting.value != "true":
            logger.info("定时投递未启用，跳过")
            return

        # 获取匹配度高、待处理的职位
        jobs = db.query(Job).filter(
            Job.status == "待处理",
            Job.match_score >= 60,
        ).order_by(Job.match_score.desc()).limit(30).all()

        if not jobs:
            logger.info("没有待投递的职位")
            return

        # 获取活跃简历
        resume = db.query(Resume).filter(Resume.is_active == True).first()
        if not resume:
            logger.info("没有启用中的简历")
            return

        user = db.query(User).first()
        if not user:
            logger.info("用户信息不完整")
            return

        generator = ResumeGenerator()
        async with BossBrowser() as boss:
            # 检查登录
            if not await boss.is_logged_in():
                logger.error("Boss直聘 未登录，跳过自动投递")
                return

            for job in jobs:
                try:
                    # AI 生成打招呼消息
                    greeting = await generator.generate_greeting(
                        job.title, job.company, job.jd_text, user.name or "求职者"
                    )

                    # 发送打招呼
                    success = await boss.send_greeting(job.job_id, greeting)

                    # 记录投递
                    app = Application(
                        job_id=job.id,
                        resume_id=resume.id,
                        greeting_message=greeting,
                        status="已投递" if success else "投递失败",
                    )
                    db.add(app)

                    job.status = "已投递" if success else "待处理"
                    db.commit()

                    logger.info(f"{'✅' if success else '❌'} {job.title} @ {job.company}")

                except Exception as e:
                    logger.error(f"投递失败 {job.title}: {e}")
                    db.rollback()

    except Exception as e:
        logger.error(f"自动投递任务异常: {e}")
    finally:
        db.close()

    logger.info("自动投递任务完成")


def start_scheduler():
    """启动调度器"""
    from backend.config import settings as app_settings

    # 每天 9:00 执行
    trigger = CronTrigger(
        hour=9, minute=0,
        timezone="Asia/Shanghai",
    )
    scheduler.add_job(
        auto_apply_job,
        trigger=trigger,
        id="auto_apply",
        replace_existing=True,
        name="每日自动投递",
    )

    # 读取用户设置的时间
    db = SessionLocal()
    try:
        setting = db.query(Setting).filter(Setting.key == "schedule_time").first()
        if setting and setting.value:
            parts = setting.value.split(":")
            if len(parts) == 2:
                hour, minute = int(parts[0]), int(parts[1])
                trigger = CronTrigger(hour=hour, minute=minute, timezone="Asia/Shanghai")
                scheduler.reschedule_job("auto_apply", trigger=trigger)
    except Exception:
        pass
    finally:
        db.close()

    scheduler.start()
    logger.info("定时调度器已启动")


def stop_scheduler():
    """停止调度器"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("定时调度器已停止")
