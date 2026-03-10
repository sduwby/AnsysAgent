"""
共享工具函数：被多个工具模块共同使用的辅助函数。
"""

from __future__ import annotations
from typing import Any


def _ok(result: Any = None) -> dict:
    return {"success": True, "result": result}


def _err(msg: str) -> dict:
    return {"success": False, "error": msg}
