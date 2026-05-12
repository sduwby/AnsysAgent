"""
试验数据管理工具：管理整车及零部件试验数据（NVH 试验、VD 试验、结构强耐试验、零部件试验）。
支持：
  - 试验数据导入与解析（CSV、RPC、UNV、UFF 格式）
  - 试验工况管理
  - CAE-试验对标（仿真与试验结果关联）
  - 试验报告生成

每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from tools.utils import _ok, _err, ok_message, ensure_parent_dir

_test_db: dict = {
    "tests": [],
    "projects": [],
}


# ---------------------------------------------------------------------------
# 工具：create_test_project - 创建试验项目
# ---------------------------------------------------------------------------

def create_test_project(
    project_name: str,
    project_type: str = "vehicle_nvh",
    vehicle_info: str = "",
    test_date: str = "",
    test_location: str = "",
) -> dict:
    """
    创建试验项目，用于管理相关试验数据。

    Args:
        project_name: 项目名称
        project_type: 项目类型，"vehicle_nvh"（整车 NVH 试验）、"vehicle_vd"（整车 VD 试验）、
                      "vehicle_durability"（整车强耐试验）、"component_test"（零部件试验）
        vehicle_info: 车辆信息（车型、VIN 等）
        test_date: 试验日期（YYYY-MM-DD）
        test_location: 试验场地
    """
    try:
        if not test_date:
            test_date = datetime.now().strftime("%Y-%m-%d")

        project = {
            "id": len(_test_db["projects"]) + 1,
            "name": project_name,
            "type": project_type,
            "vehicle_info": vehicle_info,
            "test_date": test_date,
            "test_location": test_location,
            "created_at": datetime.now().isoformat(),
            "tests": [],
        }

        _test_db["projects"].append(project)

        return _ok(ok_message(
            f"已创建试验项目: {project_name}（{project_type}）",
            project_id=project["id"],
            **project,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：import_test_data - 导入试验数据
# ---------------------------------------------------------------------------

def import_test_data(
    data_path: str,
    data_format: str = "csv",
    test_type: str = "time_history",
    channel_names: str = "",
    sampling_rate_hz: float = 0.0,
    project_id: int = 0,
) -> dict:
    """
    导入试验数据文件。

    Args:
        data_path: 数据文件路径（.csv / .rpc / .unv / .uff / .mat）
        data_format: 数据格式，"csv"（CSV 文本）、"rpc"（RPC III 时域数据）、
                     "unv"（Universal File）、"uff"（Universal File Format）、"mat"（MATLAB）
        test_type: 数据类型，"time_history"（时域数据）、"frequency_spectrum"（频谱数据）、
                   "transfer_function"（传递函数）、"modal_data"（模态数据）
        channel_names: 通道名称列表（逗号分隔）
        sampling_rate_hz: 采样率（Hz）
        project_id: 所属项目 ID，0 表示不关联
    """
    try:
        if not os.path.exists(data_path):
            return _err(f"数据文件不存在: {data_path}")

        file_size = os.path.getsize(data_path)

        test_data = {
            "id": len(_test_db["tests"]) + 1,
            "path": data_path,
            "format": data_format,
            "test_type": test_type,
            "file_size_bytes": file_size,
            "imported_at": datetime.now().isoformat(),
        }

        if channel_names:
            test_data["channels"] = [c.strip() for c in channel_names.split(",")]
            test_data["num_channels"] = len(test_data["channels"])

        if sampling_rate_hz > 0:
            test_data["sampling_rate_hz"] = sampling_rate_hz
            test_data["nyquist_freq_hz"] = sampling_rate_hz / 2.0

        if project_id > 0:
            test_data["project_id"] = project_id
            for proj in _test_db["projects"]:
                if proj["id"] == project_id:
                    proj["tests"].append(test_data["id"])
                    break

        _test_db["tests"].append(test_data)

        return _ok(ok_message(
            f"已导入试验数据: {os.path.basename(data_path)}（{data_format}，{test_type}）",
            **test_data,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：describe_nvh_test - 描述 NVH 试验配置
# ---------------------------------------------------------------------------

def describe_nvh_test(
    test_scenario: str = "idle",
    rpm_range_start: int = 0,
    rpm_range_end: int = 0,
    speed_kmh: float = 0.0,
    road_surface: str = "",
    gear_position: str = "",
    measurement_locations: str = "",
) -> dict:
    """
    描述 NVH 试验工况配置。

    Args:
        test_scenario: 试验场景，"idle"（怠速）、"wot"（全油门加速）、"cruise"（匀速巡航）、
                       "road_noise"（路噪）、"wind_noise"（风噪）、"impact"（冲击噪声）
        rpm_range_start: 发动机转速起始（rpm）
        rpm_range_end: 发动机转速终止（rpm）
        speed_kmh: 车速（km/h）
        road_surface: 路面类型，"smooth"（光滑路面）、"rough"（粗糙路面）、"cobblestone"（鹅卵石）
        gear_position: 挡位
        measurement_locations: 测点位置描述（逗号分隔）
    """
    try:
        scenario_desc = {
            "idle": "怠速工况 - 测量发动机振动和车内噪声",
            "wot": "全油门加速（WOT）- 测量加速过程中的 NVH 特性",
            "cruise": "匀速巡航 - 测量稳态行驶 NVH 特性",
            "road_noise": "路噪 - 粗糙路面激励的车内噪声",
            "wind_noise": "风噪 - 高速行驶气动噪声",
            "impact": "冲击噪声 - 过坎、过坑等瞬态冲击",
        }

        test_config = {
            "test_scenario": test_scenario,
            "description": scenario_desc.get(test_scenario, test_scenario),
            "rpm_range": (rpm_range_start, rpm_range_end) if rpm_range_end > 0 else None,
            "speed_kmh": speed_kmh,
            "road_surface": road_surface,
            "gear_position": gear_position,
        }

        if measurement_locations:
            test_config["measurement_locations"] = [loc.strip() for loc in measurement_locations.split(",")]

        return _ok(ok_message(
            f"已描述 NVH 试验工况: {test_scenario}",
            **test_config,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：describe_vd_test - 描述 VD 试验配置
# ---------------------------------------------------------------------------

def describe_vd_test(
    test_type: str = "steady_state_cornering",
    test_standard: str = "ISO 4138",
    test_speed_kmh: float = 0.0,
    steering_input: str = "step",
    steering_angle_deg: float = 0.0,
    road_surface: str = "dry_asphalt",
) -> dict:
    """
    描述整车动力学（VD）试验配置。

    Args:
        test_type: 试验类型，"steady_state_cornering"（稳态回转）、"step_steering"（阶跃转向）、
                   "sine_sweep"（正弦扫频转向）、"lane_change"（变道）、"braking"（制动试验）
        test_standard: 试验标准（ISO 4138、ISO 7401、GB/T 6323 等）
        test_speed_kmh: 试验车速（km/h）
        steering_input: 转向输入类型，"step"（阶跃）、"ramp"（斜坡）、"sine"（正弦）、"random"（随机）
        steering_angle_deg: 转向角度（度）
        road_surface: 路面状况，"dry_asphalt"（干燥沥青）、"wet_asphalt"（湿沥青）、"ice"（冰面）
    """
    try:
        test_config = {
            "test_type": test_type,
            "test_standard": test_standard,
            "test_speed_kmh": test_speed_kmh,
            "steering_input": steering_input,
            "steering_angle_deg": steering_angle_deg,
            "road_surface": road_surface,
        }

        return _ok(ok_message(
            f"已描述 VD 试验: {test_type}（{test_standard}）",
            **test_config,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：describe_durability_test - 描述强耐试验配置
# ---------------------------------------------------------------------------

def describe_durability_test(
    test_type: str = "proving_ground",
    test_standard: str = "",
    road_types: str = "",
    total_mileage_km: float = 0.0,
    load_condition: str = "gross_weight",
) -> dict:
    """
    描述整车结构强耐试验配置。

    Args:
        test_type: 试验类型，"proving_ground"（试验场道路）、"pothole"（坑洼冲击）、
                   "curb_strike"（路缘冲击）、"torsion"（扭转载荷）、"component_fatigue"（零部件疲劳）
        test_standard: 试验标准
        road_types: 道路类型（逗号分隔，如 "belgian_block,pothole,gravel,speed_bump"）
        total_mileage_km: 总试验里程（km）
        load_condition: 载荷状态，"empty"（空载）、"half_load"（半载）、"gross_weight"（满载）
    """
    try:
        test_config = {
            "test_type": test_type,
            "test_standard": test_standard,
            "total_mileage_km": total_mileage_km,
            "load_condition": load_condition,
        }

        if road_types:
            test_config["road_types"] = [rt.strip() for rt in road_types.split(",")]

        return _ok(ok_message(
            f"已描述强耐试验: {test_type}（{total_mileage_km} km）",
            **test_config,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：correlate_cae_test - CAE-试验对标
# ---------------------------------------------------------------------------

def correlate_cae_test(
    simulation_result_path: str = "",
    test_data_path: str = "",
    correlation_method: str = "mac",
    frequency_range_hz: str = "",
    dof_mapping: str = "",
) -> dict:
    """
    CAE 仿真结果与试验数据对标分析。

    Args:
        simulation_result_path: 仿真结果文件路径
        test_data_path: 试验数据文件路径
        correlation_method: 对标方法，"mac"（Modal Assurance Criterion，模态置信准则）、
                            "frequency_error"（频率误差）、"frf_comparison"（FRF 对比）、
                            "time_history"（时域对比）
        frequency_range_hz: 分析频率范围（如 "10,500" 表示 10~500 Hz）
        dof_mapping: 自由度映射关系（JSON 格式）
    """
    try:
        corr_config = {
            "simulation_result": simulation_result_path,
            "test_data": test_data_path,
            "correlation_method": correlation_method,
        }

        method_desc = {
            "mac": "Modal Assurance Criterion (MAC) - 模态振型相关性（0~1，>0.7 为良好）",
            "frequency_error": "频率误差 - 仿真与试验固有频率偏差百分比（<5% 为良好）",
            "frf_comparison": "FRF 对比 - 频率响应函数叠加比较",
            "time_history": "时域对比 - 时间历程信号叠加比较",
        }

        corr_config["method_description"] = method_desc.get(correlation_method, correlation_method)

        if frequency_range_hz:
            parts = frequency_range_hz.split(",")
            corr_config["freq_range_hz"] = (float(parts[0]), float(parts[1]))

        return _ok(ok_message(
            f"已配置 CAE-试验对标（{correlation_method}）",
            **corr_config,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：list_test_data - 列出已导入的试验数据
# ---------------------------------------------------------------------------

def list_test_data(
    project_id: int = 0,
    test_type: str = "",
) -> dict:
    """
    列出已导入的试验数据。

    Args:
        project_id: 项目 ID 过滤，0 表示全部
        test_type: 测试类型过滤，空字符串表示全部
    """
    try:
        tests = _test_db["tests"]

        if project_id > 0:
            tests = [t for t in tests if t.get("project_id") == project_id]

        if test_type:
            tests = [t for t in tests if t.get("test_type") == test_type]

        return _ok(ok_message(
            f"共 {len(tests)} 条试验数据" + (f"（项目 {project_id}）" if project_id > 0 else ""),
            total_count=len(tests),
            tests=tests,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：list_test_projects - 列出试验项目
# ---------------------------------------------------------------------------

def list_test_projects(
    project_type: str = "",
) -> dict:
    """
    列出已创建的试验项目。

    Args:
        project_type: 项目类型过滤，空字符串表示全部
    """
    try:
        projects = _test_db["projects"]

        if project_type:
            projects = [p for p in projects if p.get("type") == project_type]

        return _ok(ok_message(
            f"共 {len(projects)} 个试验项目",
            total_count=len(projects),
            projects=projects,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：export_test_report - 导出试验报告
# ---------------------------------------------------------------------------

def export_test_report(
    project_id: int,
    output_path: str = "",
    report_format: str = "json",
) -> dict:
    """
    导出试验项目报告。

    Args:
        project_id: 项目 ID
        output_path: 输出报告文件路径
        report_format: 报告格式，"json"、"csv"
    """
    try:
        project = None
        for p in _test_db["projects"]:
            if p["id"] == project_id:
                project = p
                break

        if project is None:
            return _err(f"未找到项目 ID: {project_id}")

        project_tests = [t for t in _test_db["tests"] if t.get("project_id") == project_id]

        report = {
            "project": project,
            "tests": project_tests,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_tests": len(project_tests),
                "project_type": project.get("type", "unknown"),
            },
        }

        if output_path:
            ensure_parent_dir(output_path)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            report["exported_to"] = output_path

        return _ok(ok_message(
            f"已导出试验报告: {project['name']}（{len(project_tests)} 项测试）",
            project_name=project["name"],
            total_tests=len(project_tests),
            report_format=report_format,
        ))
    except Exception as e:
        return _err(str(e))
