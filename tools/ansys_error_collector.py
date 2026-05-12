"""
Ansys 错误收集器：捕获和收集来自 Ansys 软件的错误信息。

功能特性：
- 统一的错误捕获接口
- 错误信息结构化存储
- 错误历史查询
- 与诊断工具集成

每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

import json
import re
import traceback
from datetime import datetime
from typing import Any, Optional, Callable
from functools import wraps

from tools.utils import _ok, _err

# 全局错误历史记录
_error_history: list[dict] = []
_max_history_size = 1000

# Ansys 错误模式库
_ANSYS_ERROR_PATTERNS = {
    "aedt": {
        "license": r"License.*error|Cannot checkout license",
        "convergence": r"Convergence.*not achieved|Solution.*not converging",
        "mesh": r"Mesh.*failed|Invalid mesh|Mesh quality",
        "memory": r"Out of memory|Memory allocation",
        "geometry": r"Geometry.*error|Invalid geometry",
        "material": r"Material.*not found|Unknown material",
        "boundary": r"Boundary.*error|Invalid boundary",
    },
    "fluent": {
        "divergence": r"Divergence detected|Solution diverged",
        "mesh_quality": r"Mesh.*quality.*poor|Negative volume",
        "convergence": r"Convergence.*criteria.*not met",
        "memory": r"Insufficient memory|Out of memory",
        "license": r"License.*error|Could not check out license",
    },
    "mapdl": {
        "convergence": r"Solution.*not converge|Did not converge",
        "memory": r"Insufficient memory|Memory.*error",
        "license": r"License.*error|Could not get license",
        "mesh": r"Mesh.*failed|Element.*error",
        "boundary": r"Boundary.*incompatible|Constraint.*conflict",
    },
    "icepak": {
        "convergence": r"Convergence.*not achieved|Solution.*not stable",
        "mesh": r"Mesh.*failed|Bad mesh",
        "memory": r"Out of memory|Insufficient memory",
        "thermal": r"Thermal.*error|Temperature.*invalid",
    },
}


def capture_ansi_error(func: Callable) -> Callable:
    """
    装饰器：捕获 Ansys 工具函数的错误并记录到错误历史。
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_info = _extract_error_info(e, func.__name__, args, kwargs)
            _add_error_to_history(error_info)
            
            # 尝试自动诊断
            diagnosis = _auto_diagnose(str(e), func.__name__)
            
            return _err({
                "error": str(e),
                "error_type": type(e).__name__,
                "function": func.__name__,
                "diagnosis": diagnosis,
                "error_id": error_info.get("id"),
            })
    
    return wrapper


def _extract_error_info(
    exception: Exception,
    function_name: str,
    args: tuple,
    kwargs: dict,
) -> dict:
    """提取错误信息"""
    error_str = str(exception)
    error_type = type(exception).__name__
    
    # 尝试识别 Ansys 软件类型
    ansys_tool = "unknown"
    if any(keyword in function_name.lower() for keyword in ["aedt", "maxwell", "icepak"]):
        ansys_tool = "aedt"
    elif "fluent" in function_name.lower():
        ansys_tool = "fluent"
    elif "mapdl" in function_name.lower():
        ansys_tool = "mapdl"
    
    # 提取参数信息（避免敏感信息）
    safe_kwargs = {}
    for key, value in kwargs.items():
        if key not in ["password", "token", "api_key"]:
            safe_kwargs[key] = str(value)[:100]
    
    return {
        "id": f"error_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
        "timestamp": datetime.now().isoformat(),
        "function": function_name,
        "ansys_tool": ansys_tool,
        "error_type": error_type,
        "error_message": error_str,
        "traceback": traceback.format_exc(),
        "args_count": len(args),
        "kwargs": safe_kwargs,
    }


def _add_error_to_history(error_info: dict) -> None:
    """添加错误到历史记录"""
    global _error_history
    _error_history.append(error_info)
    
    # 限制历史记录大小
    if len(_error_history) > _max_history_size:
        _error_history = _error_history[-_max_history_size:]


def _auto_diagnose(error_message: str, function_name: str) -> dict:
    """自动诊断错误"""
    # 从 function_name 推断 Ansys 工具类型
    ansys_tool = "unknown"
    if any(keyword in function_name.lower() for keyword in ["aedt", "maxwell", "icepak"]):
        ansys_tool = "aedt"
    elif "fluent" in function_name.lower():
        ansys_tool = "fluent"
    elif "mapdl" in function_name.lower():
        ansys_tool = "mapdl"
    
    # 获取对应的错误模式
    patterns = _ANSYS_ERROR_PATTERNS.get(ansys_tool, {})
    
    matched_errors = []
    for error_type, pattern in patterns.items():
        if re.search(pattern, error_message, re.IGNORECASE):
            matched_errors.append(error_type)
    
    if matched_errors:
        return {
            "diagnosed": True,
            "error_types": matched_errors,
            "primary_error": matched_errors[0],
            "suggestions": _get_suggestions(matched_errors[0], ansys_tool),
        }
    else:
        return {
            "diagnosed": False,
            "error_types": ["unknown"],
            "suggestions": ["查看详细错误日志", "检查 Ansys 软件状态", "验证输入参数"],
        }


def _get_suggestions(error_type: str, ansys_tool: str) -> list[str]:
    """获取错误修复建议"""
    suggestions = {
        "license": [
            "检查 Ansys 许可证是否有效",
            "确认许可证服务器连接正常",
            "检查是否有可用的 license",
        ],
        "convergence": [
            "减小时间步长或松弛因子",
            "检查网格质量",
            "检查边界条件设置",
            "使用更稳健的求解器设置",
        ],
        "mesh": [
            "检查几何模型质量",
            "使用更细的网格尺寸",
            "尝试不同的网格生成方法",
            "检查是否有小特征需要简化",
        ],
        "memory": [
            "减少网格数量",
            "减少并行核心数",
            "关闭其他应用程序释放内存",
            "考虑使用分布式计算",
        ],
        "divergence": [
            "减小时间步长",
            "降低松弛因子",
            "检查初始条件设置",
            "使用更稳定的求解器",
        ],
        "geometry": [
            "检查几何模型是否有孔洞或间隙",
            "修复几何中的小特征",
            "尝试使用不同的几何导入格式",
        ],
        "material": [
            "检查材料名称拼写是否正确",
            "从材料库中选择正确的材料",
            "手动输入材料属性",
        ],
        "boundary": [
            "检查边界条件是否重叠",
            "确保边界条件覆盖所有必要的面",
            "检查边界条件的物理合理性",
        ],
    }
    
    return suggestions.get(error_type, ["查看详细错误日志", "检查 Ansys 软件状态"])


# ---------------------------------------------------------------------------
# 工具：get_error_history - 获取错误历史
# ---------------------------------------------------------------------------

def get_error_history(
    limit: int = 10,
    ansys_tool: Optional[str] = None,
    error_type: Optional[str] = None,
) -> dict:
    """
    获取错误历史记录。

    Args:
        limit: 返回记录数量限制
        ansys_tool: 过滤特定 Ansys 工具（aedt/fluent/mapdl/icepak）
        error_type: 过滤特定错误类型
    """
    try:
        filtered_errors = _error_history.copy()
        
        if ansys_tool:
            filtered_errors = [e for e in filtered_errors if e.get("ansys_tool") == ansys_tool]
        
        if error_type:
            filtered_errors = [e for e in filtered_errors if error_type in e.get("error_type", "")]
        
        # 按时间倒序排列
        filtered_errors.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return _ok({
            "total_errors": len(_error_history),
            "filtered_count": len(filtered_errors),
            "errors": filtered_errors[:limit],
            "limit": limit,
            "message": f"获取 {min(limit, len(filtered_errors))} 条错误记录",
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：clear_error_history - 清空错误历史
# ---------------------------------------------------------------------------

def clear_error_history() -> dict:
    """
    清空错误历史记录。
    """
    global _error_history
    count = len(_error_history)
    _error_history = []
    return _ok({
        "cleared_count": count,
        "message": f"已清空 {count} 条错误记录",
    })


# ---------------------------------------------------------------------------
# 工具：diagnose_ansi_error - 诊断 Ansys 错误
# ---------------------------------------------------------------------------

def diagnose_ansi_error(
    error_message: str,
    ansys_tool: str = "aedt",
    context: Optional[str] = None,
) -> dict:
    """
    诊断 Ansys 错误并提供修复建议。

    Args:
        error_message: 错误消息
        ansys_tool: Ansys 工具类型（aedt/fluent/mapdl/icepak）
        context: 额外上下文信息
    """
    try:
        patterns = _ANSYS_ERROR_PATTERNS.get(ansys_tool, {})
        
        matched_errors = []
        for error_type, pattern in patterns.items():
            if re.search(pattern, error_message, re.IGNORECASE):
                matched_errors.append(error_type)
        
        if matched_errors:
            primary_error = matched_errors[0]
            suggestions = _get_suggestions(primary_error, ansys_tool)
            
            return _ok({
                "diagnosed": True,
                "ansys_tool": ansys_tool,
                "error_types": matched_errors,
                "primary_error": primary_error,
                "suggestions": suggestions,
                "context": context,
                "message": f"诊断为 {primary_error} 类型错误",
            })
        else:
            return _ok({
                "diagnosed": False,
                "ansys_tool": ansys_tool,
                "error_types": ["unknown"],
                "suggestions": [
                    "查看详细错误日志",
                    "检查 Ansys 软件状态",
                    "验证输入参数",
                    "参考 Ansys 官方文档",
                ],
                "context": context,
                "original_error": error_message,
                "message": "无法自动诊断错误类型",
            })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_error_statistics - 获取错误统计信息
# ---------------------------------------------------------------------------

def get_error_statistics() -> dict:
    """
    获取错误统计信息。
    """
    try:
        if not _error_history:
            return _ok({
                "total_errors": 0,
                "by_tool": {},
                "by_type": {},
                "recent_errors": [],
                "message": "暂无错误记录",
            })
        
        # 按工具统计
        by_tool = {}
        for error in _error_history:
            tool = error.get("ansys_tool", "unknown")
            by_tool[tool] = by_tool.get(tool, 0) + 1
        
        # 按错误类型统计
        by_type = {}
        for error in _error_history:
            error_type = error.get("error_type", "unknown")
            by_type[error_type] = by_type.get(error_type, 0) + 1
        
        # 最近的错误
        recent_errors = sorted(
            _error_history,
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )[:5]
        
        return _ok({
            "total_errors": len(_error_history),
            "by_tool": by_tool,
            "by_type": by_type,
            "recent_errors": recent_errors,
            "message": f"共有 {len(_error_history)} 条错误记录",
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 辅助函数：包装现有工具以捕获错误
# ---------------------------------------------------------------------------

def wrap_tool_with_error_capture(tool_func: Callable) -> Callable:
    """
    包装现有工具函数，自动捕获错误并记录。
    
    使用方法：
        wrapped_func = wrap_tool_with_error_capture(original_func)
        result = wrapped_func(...)
    """
    return capture_ansi_error(tool_func)


def wrap_all_tools_in_module(module) -> None:
    """
    包装模块中的所有工具函数，自动捕获错误。
    
    使用方法：
        import tools.maxwell_tools as maxwell_tools
        wrap_all_tools_in_module(maxwell_tools)
    """
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if callable(attr) and not attr_name.startswith('_'):
            if hasattr(attr, '__module__') and attr.__module__ == module.__name__:
                setattr(module, attr_name, capture_ansi_error(attr))
