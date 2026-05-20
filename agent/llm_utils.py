"""
LLM 调用共享工具：fallback 判断、payment 检测等。

供 ChatAgent 和 SubAgentBase 共同使用，避免重复定义。
"""

from __future__ import annotations

from openai import RateLimitError, APIStatusError

FALLBACK_STATUS_CODES = frozenset({429, 402, 503})


def is_fallback_error(exc: Exception) -> bool:
    """判断异常是否应触发回退到下一个提供商。"""
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, APIStatusError) and exc.status_code in FALLBACK_STATUS_CODES:
        return True
    return False


def is_payment_error(exc: Exception) -> bool:
    """判断是否为余额不足错误 (402)。"""
    return isinstance(exc, APIStatusError) and exc.status_code == 402
