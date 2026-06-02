#!/usr/bin/env python3
"""ResumeBot - 自动投递简历系统 启动脚本"""

import logging
import sys
from pathlib import Path

# 将项目根目录加入 Python 路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("resumebot")


def main():
    import uvicorn
    from backend.config import settings

    logger.info(f"🚀 启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📂 数据目录: {settings.DATA_DIR}")
    logger.info(f"🌐 访问地址: http://localhost:8000")

    # 启动定时任务
    try:
        from backend.services.scheduler_service import start_scheduler
        start_scheduler()
        logger.info("⏰ 定时调度器已启动")
    except Exception as e:
        logger.warning(f"⏰ 定时调度器启动失败: {e}")

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
