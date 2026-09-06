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
        - Windows: SIGALRM 不可用且 threading.Timer 无法中断阻塞调用，
          超时保护不生效，函数直接透传执行
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            system = platform.system()
            
            if system == "Windows":
                return func(*args, **kwargs)
            else:
                import signal
                
                def timeout_handler(signum: int, frame: Any) -> None:
                    raise TimeoutError("工具调用超时")
                
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                try:
                    signal.alarm(seconds)
                    try:
                        result = func(*args, **kwargs)
                    finally:
                        signal.alarm(0)
                finally:
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


# ---------------------------------------------------------------------------
# Parameter Validation Utilities
# ---------------------------------------------------------------------------

class ValidationError(Exception):
    """参数验证失败异常。"""
    pass


def validate_file_path(
    path: str | os.PathLike[str] | None,
    *,
    required: bool = False,
    allowed_extensions: list[str] | None = None,
    must_exist: bool = False,
    field_name: str = "path",
) -> None:
    """
    验证文件路径参数。

    Args:
        path: 文件路径
        required: 是否必填（如果为 True，None 会抛出异常）
        allowed_extensions: 允许的扩展名集合（不区分大小写）
        must_exist: 是否检查路径是否存在
        field_name: 字段名称（用于错误消息）

    Raises:
        ValidationError: 验证失败时抛出
    """
    if path is None:
        if required:
            raise ValidationError(f"{field_name} 不能为空")
        return

    path_str = str(path)
    
    # 检查空字符串
    if not path_str.strip():
        raise ValidationError(f"{field_name} 不能为空字符串")

    # 检查路径遍历攻击
    if ".." in path_str:
        raise ValidationError(f"{field_name} 不允许包含 '..'")
    
    # 检查可疑字符（防止命令注入）
    if platform.system() == "Windows":
        # Windows 下检查危险字符
        dangerous_chars = [';', '|', '&', '`', '\n', '(', ')']
        for ch in dangerous_chars:
            if ch in path_str:
                raise ValidationError(f"{field_name} 包含非法字符: {ch}")
    else:
        # Unix 下检查危险字符
        dangerous_chars = [';', '|', '&', '`', '(', ')', '\n']
        for ch in dangerous_chars:
            if ch in path_str:
                raise ValidationError(f"{field_name} 包含非法字符: {ch}")

    # 检查扩展名
    if allowed_extensions is not None:
        from pathlib import Path
        ext = Path(path_str).suffix.lower()
        if ext not in {e.lower() for e in allowed_extensions}:
            raise ValidationError(
                f"{field_name} 不支持的文件扩展名: {ext}，"
                f"允许的扩展名: {', '.join(sorted(allowed_extensions))}"
            )

    # 检查路径是否存在
    if must_exist:
        from pathlib import Path
        p = Path(path_str).resolve()
        if not p.exists():
            raise ValidationError(f"{field_name} 路径不存在: {path_str}")


def validate_numeric(
    value: Any,
    *,
    min_val: float | None = None,
    max_val: float | None = None,
    allow_zero: bool = True,
    allow_negative: bool = True,
    field_name: str = "value",
) -> float:
    """
    验证数值参数。

    Args:
        value: 待验证的数值
        min_val: 最小值（包含）
        max_val: 最大值（包含）
        allow_zero: 是否允许零值
        allow_negative: 是否允许负数
        field_name: 字段名称（用于错误消息）

    Returns:
        转换后的浮点数值

    Raises:
        ValidationError: 验证失败时抛出
    """
    # 类型检查
    if not isinstance(value, (int, float)):
        raise ValidationError(
            f"{field_name} 必须是数值类型，收到: {type(value).__name__}"
        )
    
    # NaN 检查
    import math
    if math.isnan(value) or math.isinf(value):
        raise ValidationError(f"{field_name} 不能是 NaN 或无穷大")

    val = float(value)

    # 负数检查
    if not allow_negative and val < 0:
        raise ValidationError(f"{field_name} 不能为负数")

    # 零值检查
    if not allow_zero and val == 0:
        raise ValidationError(f"{field_name} 不能为零")

    # 范围检查
    if min_val is not None and val < min_val:
        raise ValidationError(
            f"{field_name} 不能小于 {min_val}，当前值: {val}"
        )
    
    if max_val is not None and val > max_val:
        raise ValidationError(
            f"{field_name} 不能大于 {max_val}，当前值: {val}"
        )

    return val


def validate_string(
    value: str,
    *,
    max_length: int | None = None,
    min_length: int = 0,
    allow_empty: bool = True,
    pattern: str | None = None,
    field_name: str = "value",
) -> str:
    """
    验证字符串参数。

    Args:
        value: 待验证的字符串
        max_length: 最大长度
        min_length: 最小长度
        allow_empty: 是否允许空字符串
        pattern: 正则表达式模式（用于格式校验）
        field_name: 字段名称（用于错误消息）

    Returns:
        验证后的字符串

    Raises:
        ValidationError: 验证失败时抛出
    """
    if not isinstance(value, str):
        raise ValidationError(
            f"{field_name} 必须是字符串类型，收到: {type(value).__name__}"
        )

    if not allow_empty and not value.strip():
        raise ValidationError(f"{field_name} 不能为空字符串")

    if len(value) < min_length:
        raise ValidationError(
            f"{field_name} 长度不能小于 {min_length}，当前长度: {len(value)}"
        )

    if max_length is not None and len(value) > max_length:
        raise ValidationError(
            f"{field_name} 长度不能超过 {max_length}，当前长度: {len(value)}"
        )

    if pattern is not None:
        import re
        if not re.match(pattern, value):
            raise ValidationError(
                f"{field_name} 格式不正确，需要匹配模式: {pattern}"
            )

    return value


def validate_positive_float(value: Any, field_name: str = "value") -> float:
    """验证正浮点数（快捷方法）"""
    return validate_numeric(
        value,
        min_val=0.0,
        allow_zero=False,
        allow_negative=False,
        field_name=field_name,
    )


def validate_non_negative_float(value: Any, field_name: str = "value") -> float:
    """验证非负浮点数（快捷方法）"""
    return validate_numeric(
        value,
        min_val=0.0,
        allow_negative=False,
        field_name=field_name,
    )


def validate_positive_int(value: Any, field_name: str = "value") -> int:
    """验证正整数（快捷方法）"""
    if not isinstance(value, int):
        try:
            value = int(float(value))  # 支持 "3.0" 这样的字符串
        except (ValueError, TypeError):
            raise ValidationError(
                f"{field_name} 必须是整数，收到: {type(value).__name__}"
            )
    if value <= 0:
        raise ValidationError(f"{field_name} 必须是正整数，当前值: {value}")
    return value


def validate_list(value: Any, *, field_name: str = "value") -> list:
    """验证列表参数"""
    if not isinstance(value, (list, tuple)):
        raise ValidationError(
            f"{field_name} 必须是列表类型，收到: {type(value).__name__}"
        )
    return list(value)


def validate_range(
    min_val: float,
    max_val: float,
    *,
    field_name: str = "range",
) -> tuple[float, float]:
    """验证范围参数（min < max）"""
    if min_val >= max_val:
        raise ValidationError(
            f"{field_name} 的最小值 ({min_val}) 必须小于最大值 ({max_val})"
        )
    return (min_val, max_val)

