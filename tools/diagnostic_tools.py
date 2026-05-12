"""
智能诊断与异常检测工具：提供仿真错误诊断、结果异常检测和敏感性分析功能。

功能特性：
- 仿真错误自动诊断
- 仿真结果合理性检查
- 参数敏感性分析
- 异常值检测

每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from tools.utils import _ok, _err, ok_message

# 错误模式库：正则表达式 -> (错误类型, 解决方案)
_ERROR_PATTERNS = [
    {
        "pattern": r"Convergence.*not achieved|did not converge",
        "type": "convergence",
        "message": "仿真未收敛",
        "solutions": [
            "检查网格质量，可能存在负体积或高偏斜度网格",
            "减小时间步长或松弛因子",
            "检查边界条件设置是否合理",
            "尝试使用更稳健的求解器设置",
        ],
    },
    {
        "pattern": r"Out of memory|Memory allocation failed",
        "type": "memory",
        "message": "内存不足",
        "solutions": [
            "减少网格数量或使用更粗糙的网格",
            "减少并行核心数",
            "关闭其他应用程序释放内存",
            "考虑使用分布式计算",
        ],
    },
    {
        "pattern": r"Mesh.*quality.*poor|Negative volume",
        "type": "mesh_quality",
        "message": "网格质量问题",
        "solutions": [
            "检查并修复几何模型中的小特征或间隙",
            "使用更细的网格尺寸",
            "尝试不同的网格生成方法",
            "使用网格修复工具",
        ],
    },
    {
        "pattern": r"Material.*not found|Unknown material",
        "type": "material",
        "message": "材料缺失",
        "solutions": [
            "检查材料名称拼写是否正确",
            "从材料库中选择正确的材料",
            "手动输入材料属性",
        ],
    },
    {
        "pattern": r"Boundary condition.*conflict|Incompatible boundary",
        "type": "boundary",
        "message": "边界条件冲突",
        "solutions": [
            "检查边界条件是否重叠",
            "确保边界条件覆盖所有必要的面",
            "检查边界条件的物理合理性",
        ],
    },
    {
        "pattern": r"License.*error|License.*expired",
        "type": "license",
        "message": "许可证错误",
        "solutions": [
            "检查 Ansys 许可证是否有效",
            "确认许可证服务器连接",
            "联系 IT 部门检查许可证配置",
        ],
    },
    {
        "pattern": r"Geometry.*invalid|Invalid geometry",
        "type": "geometry",
        "message": "几何模型无效",
        "solutions": [
            "检查几何模型是否有孔洞或间隙",
            "修复几何中的小特征",
            "尝试使用不同的几何导入格式",
        ],
    },
    {
        "pattern": r"Solution.*failed|Simulation.*failed",
        "type": "solver",
        "message": "求解器失败",
        "solutions": [
            "检查求解器设置是否合理",
            "查看详细的错误日志",
            "尝试使用不同的求解器",
        ],
    },
    {
        "pattern": r"Divergence detected",
        "type": "divergence",
        "message": "计算发散",
        "solutions": [
            "减小时间步长",
            "降低松弛因子",
            "检查初始条件设置",
            "使用更稳定的求解器",
        ],
    },
    {
        "pattern": r"Timeout|Timed out",
        "type": "timeout",
        "message": "计算超时",
        "solutions": [
            "增加超时时间限制",
            "简化模型或使用更粗糙的网格",
            "检查系统资源使用情况",
        ],
    },
]


# ---------------------------------------------------------------------------
# 工具：diagnose_error - 诊断仿真错误
# ---------------------------------------------------------------------------

def diagnose_error(
    error_message: str,
    context: Optional[str] = None,
    tool_name: Optional[str] = None,
) -> dict:
    """
    根据错误消息自动诊断问题并提供解决方案。

    Args:
        error_message: 错误消息
        context: 额外上下文信息（如仿真类型、操作步骤）
        tool_name: 出错的工具名称
    """
    try:
        matched_patterns = []
        
        for pattern_info in _ERROR_PATTERNS:
            if re.search(pattern_info["pattern"], error_message, re.IGNORECASE):
                matched_patterns.append({
                    "type": pattern_info["type"],
                    "message": pattern_info["message"],
                    "solutions": pattern_info["solutions"],
                })
        
        if matched_patterns:
            primary_match = matched_patterns[0]
            return _ok({
                "diagnosed": True,
                "error_type": primary_match["type"],
                "error_message": primary_match["message"],
                "solutions": primary_match["solutions"],
                "all_matches": matched_patterns,
                "context": context,
                "tool_name": tool_name,
                "message": f"错误诊断: {primary_match['message']}",
            })
        else:
            # 通用诊断建议
            generic_solutions = [
                "查看详细的错误日志以获取更多信息",
                "检查仿真设置是否合理",
                "尝试简化模型或使用默认设置",
                "搜索 Ansys 文档或社区寻找类似问题",
            ]
            
            return _ok({
                "diagnosed": False,
                "error_type": "unknown",
                "error_message": "无法自动识别的错误",
                "solutions": generic_solutions,
                "context": context,
                "tool_name": tool_name,
                "original_error": error_message,
                "message": "无法自动诊断错误，请查看详细信息",
            })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：validate_simulation_setup - 验证仿真设置
# ---------------------------------------------------------------------------

def validate_simulation_setup(
    setup_type: str,
    parameters: dict,
) -> dict:
    """
    验证仿真设置的合理性。

    Args:
        setup_type: 仿真类型（如 "cfd", "structural", "thermal", "emag"）
        parameters: 仿真参数字典
    """
    try:
        issues = []
        warnings = []
        
        if setup_type == "cfd":
            # CFD 设置验证
            if parameters.get("mesh_quality", {}).get("min_orthogonal_quality", 1.0) < 0.1:
                issues.append("网格正交质量过低，可能导致收敛问题")
            
            if parameters.get("turbulence_model") == "k-epsilon" and parameters.get("y_plus_target", 30) < 30:
                warnings.append("k-epsilon 模型通常需要 y+ > 30")
            
            if parameters.get("inlet_velocity", 0) > 100:
                warnings.append("入口速度过高，请检查是否合理")
        
        elif setup_type == "structural":
            # 结构设置验证
            if parameters.get("youngs_modulus", 0) <= 0:
                issues.append("杨氏模量必须为正值")
            
            if parameters.get("poisson_ratio", 0.3) >= 0.5:
                issues.append("泊松比应小于 0.5")
            
            if parameters.get("max_stress", 0) > parameters.get("yield_strength", float('inf')):
                warnings.append("最大应力超过屈服强度，可能发生塑性变形")
        
        elif setup_type == "thermal":
            # 热分析设置验证
            if parameters.get("thermal_conductivity", 0) <= 0:
                issues.append("热导率必须为正值")
            
            if parameters.get("heat_transfer_coefficient", 0) < 0:
                issues.append("换热系数不能为负值")
        
        elif setup_type == "emag":
            # 电磁设置验证
            if parameters.get("frequency", 0) < 0:
                issues.append("频率不能为负值")
            
            if parameters.get("current", 0) > 1000:
                warnings.append("电流值过大，请检查是否正确")
        
        # 通用验证
        if parameters.get("mesh_count", 0) > 10_000_000:
            warnings.append("网格数量超过 1000 万，计算时间可能很长")
        
        if parameters.get("time_step", 1.0) <= 0:
            issues.append("时间步长必须为正值")
        
        return _ok({
            "valid": len(issues) == 0,
            "setup_type": setup_type,
            "issues": issues,
            "warnings": warnings,
            "issue_count": len(issues),
            "warning_count": len(warnings),
            "message": f"验证完成: {len(issues)} 个问题, {len(warnings)} 个警告",
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：analyze_sensitivity - 参数敏感性分析
# ---------------------------------------------------------------------------

def analyze_sensitivity(
    parameters: dict[str, list[float]],
    results: dict[str, list[float]],
    method: str = "correlation",
) -> dict:
    """
    分析设计参数对仿真结果的敏感性。

    Args:
        parameters: 设计参数及其取值列表 {"param_name": [values]}
        results: 结果参数及其取值列表 {"result_name": [values]}
        method: 分析方法，"correlation"（相关系数）或 "tornado"（龙卷风图）
    """
    try:
        sensitivity_results = {}
        
        if method == "correlation":
            # 使用相关系数分析
            for param_name, param_values in parameters.items():
                for result_name, result_values in results.items():
                    if len(param_values) != len(result_values):
                        continue
                    
                    # 计算皮尔逊相关系数
                    n = len(param_values)
                    mean_p = sum(param_values) / n
                    mean_r = sum(result_values) / n
                    
                    cov = sum((p - mean_p) * (r - mean_r) for p, r in zip(param_values, result_values)) / n
                    std_p = (sum((p - mean_p) ** 2 for p in param_values) / n) ** 0.5
                    std_r = (sum((r - mean_r) ** 2 for r in result_values) / n) ** 0.5
                    
                    if std_p > 0 and std_r > 0:
                        correlation = cov / (std_p * std_r)
                    else:
                        correlation = 0.0
                    
                    if param_name not in sensitivity_results:
                        sensitivity_results[param_name] = {}
                    
                    sensitivity_results[param_name][result_name] = {
                        "correlation": round(correlation, 4),
                        "sensitivity": abs(correlation),
                        "direction": "positive" if correlation > 0 else "negative" if correlation < 0 else "none",
                    }
        
        elif method == "tornado":
            # 龙卷风图分析
            for param_name, param_values in parameters.items():
                for result_name, result_values in results.items():
                    if len(param_values) < 2 or len(result_values) < 2:
                        continue
                    
                    min_param = min(param_values)
                    max_param = max(param_values)
                    
                    # 找到对应的结果
                    min_idx = param_values.index(min_param)
                    max_idx = param_values.index(max_param)
                    
                    min_result = result_values[min_idx]
                    max_result = result_values[max_idx]
                    
                    sensitivity = abs(max_result - min_result)
                    
                    if param_name not in sensitivity_results:
                        sensitivity_results[param_name] = {}
                    
                    sensitivity_results[param_name][result_name] = {
                        "min_value": min_result,
                        "max_value": max_result,
                        "range": sensitivity,
                        "sensitivity": sensitivity,
                    }
        
        # 找出最敏感的参数
        most_sensitive = {}
        for result_name in results.keys():
            max_sensitivity = 0
            most_sensitive_param = None
            
            for param_name in parameters.keys():
                if param_name in sensitivity_results and result_name in sensitivity_results[param_name]:
                    sensitivity = sensitivity_results[param_name][result_name]["sensitivity"]
                    if sensitivity > max_sensitivity:
                        max_sensitivity = sensitivity
                        most_sensitive_param = param_name
            
            if most_sensitive_param:
                most_sensitive[result_name] = {
                    "parameter": most_sensitive_param,
                    "sensitivity": max_sensitivity,
                }
        
        return _ok({
            "method": method,
            "sensitivity_results": sensitivity_results,
            "most_sensitive_parameters": most_sensitive,
            "parameter_count": len(parameters),
            "result_count": len(results),
            "message": f"敏感性分析完成，使用 {method} 方法",
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：detect_anomalies - 检测仿真结果异常
# ---------------------------------------------------------------------------

def detect_anomalies(
    results: dict[str, list[float]],
    expected_ranges: Optional[dict[str, dict[str, float]]] = None,
    method: str = "range",
) -> dict:
    """
    检测仿真结果中的异常值。

    Args:
        results: 结果数据 {"result_name": [values]}
        expected_ranges: 期望范围 {"result_name": {"min": val, "max": val}}
        method: 检测方法，"range"（范围检查）或 "statistical"（统计检查）
    """
    try:
        anomalies = {}
        
        for result_name, values in results.items():
            if not values:
                continue
            
            if method == "range":
                # 范围检查
                if expected_ranges and result_name in expected_ranges:
                    min_val = expected_ranges[result_name].get("min", float('-inf'))
                    max_val = expected_ranges[result_name].get("max", float('inf'))
                    
                    out_of_range = [v for v in values if v < min_val or v > max_val]
                    
                    if out_of_range:
                        anomalies[result_name] = {
                            "method": "range",
                            "expected_min": min_val,
                            "expected_max": max_val,
                            "anomaly_count": len(out_of_range),
                            "anomaly_values": out_of_range[:5],  # 最多显示5个
                            "total_count": len(values),
                        }
            
            elif method == "statistical":
                # 统计检查（使用 IQR 方法）
                sorted_values = sorted(values)
                n = len(sorted_values)
                
                if n >= 4:
                    q1_idx = n // 4
                    q3_idx = 3 * n // 4
                    q1 = sorted_values[q1_idx]
                    q3 = sorted_values[q3_idx]
                    iqr = q3 - q1
                    
                    lower_bound = q1 - 1.5 * iqr
                    upper_bound = q3 + 1.5 * iqr
                    
                    outliers = [v for v in values if v < lower_bound or v > upper_bound]
                    
                    if outliers:
                        anomalies[result_name] = {
                            "method": "statistical",
                            "q1": q1,
                            "q3": q3,
                            "iqr": iqr,
                            "lower_bound": lower_bound,
                            "upper_bound": upper_bound,
                            "anomaly_count": len(outliers),
                            "anomaly_values": outliers[:5],
                            "total_count": len(values),
                        }
        
        has_anomalies = len(anomalies) > 0
        
        return _ok({
            "has_anomalies": has_anomalies,
            "method": method,
            "anomalies": anomalies,
            "anomaly_count": sum(a["anomaly_count"] for a in anomalies.values()),
            "message": "检测到异常值" if has_anomalies else "未检测到异常",
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_error_history - 获取错误历史记录
# ---------------------------------------------------------------------------

def get_error_history(
    limit: int = 10,
    error_type: Optional[str] = None,
) -> dict:
    """
    获取历史错误记录。

    Args:
        limit: 返回记录数量限制
        error_type: 错误类型过滤（可选）
    """
    try:
        # 这里可以扩展为从日志或数据库中读取
        # 目前返回示例数据
        sample_errors = [
            {"timestamp": "2024-01-01 10:00:00", "type": "convergence", "message": "CFD 仿真未收敛"},
            {"timestamp": "2024-01-01 11:30:00", "type": "mesh_quality", "message": "网格质量检查失败"},
            {"timestamp": "2024-01-02 09:15:00", "type": "license", "message": "许可证服务器连接失败"},
        ]
        
        if error_type:
            sample_errors = [e for e in sample_errors if e["type"] == error_type]
        
        return _ok({
            "count": min(limit, len(sample_errors)),
            "errors": sample_errors[:limit],
            "message": f"获取 {min(limit, len(sample_errors))} 条错误记录",
        })
    except Exception as e:
        return _err(str(e))
