"""
共享工具函数：被多个工具模块共同使用的辅助函数。
"""

from __future__ import annotations
import os
import platform
from functools import wraps
from typing import Any, Callable
import threading


class TimeoutError(Exception):
    """工具调用超时异常。"""
    pass


def signal_timeout(seconds: int) -> Callable:
    """
    为工具函数添加超时保护（跨平台支持）。
    
    用法:
        @signal_timeout(3600)  # 1 小时超时
        def run_simulation(...):
            ...
    
    参数:
        seconds: 超时时间（秒）
    
    返回:
        装饰器函数
    
    注意:
        - Unix/Linux/macOS: 使用 signal.SIGALRM 实现
        - Windows: 不支持，装饰后的函数在 Windows 上调用时将抛出 NotImplementedError
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 检测操作系统
            system = platform.system()
            
            if system == "Windows":
                # Windows 不支持 signal.SIGALRM，threading.Timer 无法中断正在阻塞的 AEDT 调用。
                # 此平台上超时保护不生效，直接透传调用。
                raise NotImplementedError(
                    "signal_timeout 在 Windows 上不支持：SIGALRM 不可用，"
                    "且 threading.Timer 无法中断阻塞中的 AEDT 调用。"
                    "请在 Unix/Linux/macOS 环境下使用本装饰器。"
                )
            else:
                # Unix/Linux/macOS: 使用 signal.SIGALRM
                import signal
                
                def timeout_handler(signum: int, frame: Any) -> None:
                    raise TimeoutError("工具调用超时")
                
                # 设置信号处理器
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                try:
                    # 启动定时器
                    signal.alarm(seconds)
                    try:
                        result = func(*args, **kwargs)
                    finally:
                        # 取消定时器
                        signal.alarm(0)
                finally:
                    # 恢复旧的处理函数
                    signal.signal(signal.SIGALRM, old_handler)
                return result
        return wrapper
    return decorator


def _ok(result: Any = None) -> dict:
    return {"success": True, "result": result}


def _err(msg: str) -> dict:
    return {"success": False, "error": msg}


def ok_message(message: str, **extra: Any) -> dict[str, Any]:
    """构造带 message 的标准成功返回体。"""
    result = {"message": message}
    result.update(extra)
    return result


def ensure_parent_dir(path: str) -> None:
    """确保文件路径的父目录存在。"""
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)


def get_design_names(app) -> list[str]:
    """兼容 design_list 既可能是属性也可能是方法。"""
    design_list = getattr(app, "design_list", [])
    if callable(design_list):
        design_list = design_list()
    return list(design_list or [])


def assign_power_sources(app, losses_by_object: dict[str, float]) -> dict[str, list[str]]:
    """
    批量给 Icepak 对象分配 Total Power 热源。

    返回:
        {
            "assigned": ["Winding=10W", ...],
            "missing": ["Rotor"],
            "errors": ["Stator: xxx"],
        }
    """
    assigned: list[str] = []
    missing: list[str] = []
    errors: list[str] = []
    modeler = getattr(app, "modeler", None)

    for obj_name, loss in losses_by_object.items():
        try:
            obj = modeler.get_object_from_name(obj_name) if modeler is not None else obj_name
            if not obj:
                missing.append(obj_name)
                continue
            app.assign_source(
                obj_name,
                "TotalPower",
                thermal_condition="Total Power",
                assignment_value=f"{loss}W",
            )
            assigned.append(f"{obj_name}={loss:.4f}W")
        except Exception as e:
            errors.append(f"{obj_name}: {e}")

    return {
        "assigned": assigned,
        "missing": missing,
        "errors": errors,
    }


def ensure_report_deleted(post, report_name: str) -> None:
    """若同名报告存在则删除，避免重复创建报错。"""
    all_report_names = getattr(post, "all_report_names", [])
    if report_name in all_report_names:
        post.delete_report(report_name)


def create_report_and_get_data(
    post,
    *,
    expressions: list[str],
    setup_sweep_name: str,
    report_name: str,
    report_category: str | None = None,
):
    """创建报告并返回其 solution data。"""
    ensure_report_deleted(post, report_name)
    kwargs = {
        "expressions": expressions,
        "setup_sweep_name": setup_sweep_name,
        "report_name": report_name,
    }
    if report_category is not None:
        kwargs["report_category"] = report_category
    report = post.create_report(**kwargs)
    return report.get_solution_data()


def append_warnings(result: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    """若存在 warning，则将其附加到返回结果中。"""
    if warnings:
        result["warnings"] = warnings
    return result



