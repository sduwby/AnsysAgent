"""
AnsysAgent 日志模块
- 按天轮转写入本地文件（logs/ansys_agent_YYYY-MM-DD.log）
- 开发模式：./logs/，打包模式：<exe同级>/logs/
- 调用 get_logger(name) 获取带名称前缀的子 logger
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

# ---------------------------------------------------------------------------
# 日志目录解析（兼容 PyInstaller frozen 模式）
# ---------------------------------------------------------------------------

def _resolve_log_dir() -> Path:
    if getattr(sys, "frozen", False):
        # 打包模式：放在 exe 同级目录
        log_dir = Path(sys.executable).parent / "logs"
    else:
        log_dir = Path(".") / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


# ---------------------------------------------------------------------------
# 初始化根 logger（只执行一次）
# ---------------------------------------------------------------------------

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_initialized = False


def setup_logging() -> None:
    """初始化文件日志，应在程序入口处调用一次。"""
    global _initialized
    if _initialized:
        return
    _initialized = True

    log_dir = _resolve_log_dir()
    log_file = log_dir / "ansys_agent.log"

    root_logger = logging.getLogger("ansys_agent")
    root_logger.setLevel(logging.DEBUG)

    # 按天轮转，保留最近 30 天
    file_handler = TimedRotatingFileHandler(
        filename=str(log_file),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root_logger.addHandler(file_handler)
    root_logger.propagate = False  # 不传播到 root，避免第三方库噪声

    root_logger.info("=" * 60)
    root_logger.info("AnsysAgent 启动，日志写入: %s", log_file.resolve())
    root_logger.info("=" * 60)


def get_logger(name: str) -> logging.Logger:
    """获取命名子 logger，格式为 ansys_agent.<name>。"""
    return logging.getLogger(f"ansys_agent.{name}")
