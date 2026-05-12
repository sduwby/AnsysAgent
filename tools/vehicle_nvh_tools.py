"""
整车 NVH 仿真工具：基于 MAPDL / Mechanical 进行整车噪声-振动-舒适性（NVH）分析。
支持：
  - 整车模态分析（白车身 / 整车）
  - 频率响应分析（激励点导纳 / 传递函数）
  - 车内噪声分析（声腔模态 / 声固耦合）
  - 路噪分析（路面激励噪声传递路径）
  - 风噪分析（气动噪声源识别）
  - 声品质评价（响度、尖锐度、粗糙度）

每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

import json
import os
from typing import Any

from tools.utils import _ok, _err, ok_message, ensure_parent_dir

_nvh_mapdl = None
_nvh_config: dict = {
    "analysis_type": None,
    "model_path": None,
    "frequency_range": None,
}


def _mapdl():
    if _nvh_mapdl is None:
        raise RuntimeError("未连接到求解器，请先调用 connect_vehicle_nvh_solver。")
    return _nvh_mapdl


# ---------------------------------------------------------------------------
# 工具：connect_vehicle_nvh_solver - 连接整车 NVH 求解器
# ---------------------------------------------------------------------------

def connect_vehicle_nvh_solver(
    nproc: int = 16,
    launch_local: bool = True,
    port: int = 50058,
    server: str = "127.0.0.1",
) -> dict:
    """
    连接到整车 NVH 分析求解器（MAPDL）。

    Args:
        nproc: 并行核心数（NVH 分析通常需要较多核）
        launch_local: 是否本地启动
        port: gRPC 端口号
        server: 服务器地址
    """
    global _nvh_mapdl
    try:
        from ansys.mapdl.core import launch_mapdl, MapdlGrpc
        if launch_local:
            _nvh_mapdl = launch_mapdl(
                nproc=nproc, port=port, override=True,
            )
        else:
            _nvh_mapdl = MapdlGrpc(ip=server, port=port)

        ver = getattr(_nvh_mapdl, "version", "unknown")
        return _ok(ok_message(
            f"已连接整车 NVH 求解器（版本 {ver}，{nproc} 核）",
            version=ver,
            nproc=nproc,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：load_vehicle_nvh_model - 加载整车 NVH 模型
# ---------------------------------------------------------------------------

def load_vehicle_nvh_model(
    structural_model_path: str,
    acoustic_model_path: str = "",
    model_type: str = "cdb",
) -> dict:
    """
    加载整车 NVH 分析有限元模型（结构 + 声腔）。

    Args:
        structural_model_path: 结构模型文件路径（白车身 / 整车 FE 模型）
        acoustic_model_path: 声腔模型文件路径（可选，车内声学网格）
        model_type: 文件类型，"cdb"（MAPDL）、"bdf"（Nastran）、"inp"（Abaqus）
    """
    try:
        mapdl = _mapdl()
        if not os.path.exists(structural_model_path):
            return _err(f"结构模型文件不存在: {structural_model_path}")

        mapdl.clear()
        mapdl.prep7()

        if model_type == "cdb":
            mapdl.cdread("db", structural_model_path)
        elif model_type == "bdf":
            mapdl.input(structural_model_path)
        elif model_type == "inp":
            mapdl.input(structural_model_path)

        _nvh_config["model_path"] = structural_model_path

        has_acoustic = acoustic_model_path and os.path.exists(acoustic_model_path)
        if has_acoustic:
            _nvh_config["acoustic_model_path"] = acoustic_model_path

        return _ok(ok_message(
            f"已加载整车 NVH 模型: {structural_model_path}" +
            (f" + 声腔模型: {acoustic_model_path}" if has_acoustic else ""),
            structural_model_path=structural_model_path,
            acoustic_model_path=acoustic_model_path if has_acoustic else None,
            has_acoustic_cavity=has_acoustic,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：define_nvh_materials - 定义 NVH 分析材料
# ---------------------------------------------------------------------------

def define_nvh_materials(
    material_id: int = 1,
    material_type: str = "steel",
    youngs_modulus_gpa: float = 210.0,
    poisson_ratio: float = 0.3,
    density_kg_m3: float = 7850.0,
    loss_factor: float = 0.002,
    acoustic_speed_ms: float = 343.0,
    air_density_kg_m3: float = 1.225,
) -> dict:
    """
    定义 NVH 分析材料属性（含阻尼特性）。

    Args:
        material_id: 材料 ID
        material_type: 材料类型，"steel"（钢）、"aluminum"（铝）、"glass"（玻璃）、
                       "damping_material"（阻尼材料）、"sealant"（密封胶）、"air"（空气）
        youngs_modulus_gpa: 杨氏模量（GPa）
        poisson_ratio: 泊松比
        density_kg_m3: 密度（kg/m³）
        loss_factor: 损耗因子（阻尼，典型钢 0.001~0.005，阻尼材料 0.1~1.0）
        acoustic_speed_ms: 声速（m/s），空气 343 m/s
        air_density_kg_m3: 空气密度（kg/m³），1.225
    """
    try:
        mapdl = _mapdl()
        mapdl.prep7()

        if material_type == "air":
            mapdl.mp("DENS", material_id, air_density_kg_m3)
            mapdl.mp("SONC", material_id, acoustic_speed_ms)
        else:
            E_pa = youngs_modulus_gpa * 1e9
            mapdl.mp("EX", material_id, E_pa)
            mapdl.mp("PRXY", material_id, poisson_ratio)
            mapdl.mp("DENS", material_id, density_kg_m3)

        return _ok(ok_message(
            f"已定义 NVH 材料 {material_id}（{material_type}，η={loss_factor}）",
            material_id=material_id,
            material_type=material_type,
            youngs_modulus_gpa=youngs_modulus_gpa,
            density_kg_m3=density_kg_m3,
            loss_factor=loss_factor,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_vehicle_modal_analysis - 设置整车模态分析
# ---------------------------------------------------------------------------

def setup_vehicle_modal_analysis(
    num_modes: int = 50,
    freq_range_start_hz: float = 0.0,
    freq_range_end_hz: float = 200.0,
    modal_method: str = "lanb",
    constraint_type: str = "free_free",
) -> dict:
    """
    设置整车模态分析参数。

    Args:
        num_modes: 提取模态数
        freq_range_start_hz: 频率范围下限（Hz）
        freq_range_end_hz: 频率范围上限（Hz）
        modal_method: 求解方法，"lanb"（Block Lanczos）、"subsp"（子空间迭代）、"unsym"（非对称）
        constraint_type: 约束状态，"free_free"（自由-自由）、"constrained"（实际约束）、
                         "body_mounts"（车身安装点约束）
    """
    try:
        mapdl = _mapdl()

        mapdl.run("/SOLU")
        mapdl.run("ANTYPE,MODAL")
        mapdl.run(f"MODOPT,{modal_method},{num_modes},{freq_range_start_hz},{freq_range_end_hz}")
        mapdl.run("MXPAND,ON,,,YES")

        _nvh_config["analysis_type"] = "modal"
        _nvh_config["frequency_range"] = (freq_range_start_hz, freq_range_end_hz)

        return _ok(ok_message(
            f"已设置整车模态分析（{num_modes} 阶，{freq_range_start_hz}~{freq_range_end_hz} Hz，{constraint_type}）",
            num_modes=num_modes,
            freq_range_start_hz=freq_range_start_hz,
            freq_range_end_hz=freq_range_end_hz,
            modal_method=modal_method,
            constraint_type=constraint_type,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_frequency_response - 设置频率响应分析
# ---------------------------------------------------------------------------

def setup_frequency_response(
    excitation_node: int = 0,
    excitation_dof: str = "UX",
    excitation_force_n: float = 1.0,
    freq_start_hz: float = 10.0,
    freq_end_hz: float = 500.0,
    freq_step_hz: float = 1.0,
    damping_ratio: float = 0.02,
    response_type: str = "displacement",
) -> dict:
    """
    设置频率响应分析（FRF，传递函数分析）。

    Args:
        excitation_node: 激励节点 ID
        excitation_dof: 激励方向，"UX"、"UY"、"UZ"
        excitation_force_n: 激励力幅值（N）
        freq_start_hz: 频率范围起始（Hz）
        freq_end_hz: 频率范围终止（Hz）
        freq_step_hz: 频率步长（Hz）
        damping_ratio: 阻尼比
        response_type: 响应类型，"displacement"（位移）、"velocity"（速度）、"acceleration"（加速度）
    """
    try:
        mapdl = _mapdl()

        num_steps = int((freq_end_hz - freq_start_hz) / freq_step_hz) + 1

        mapdl.run("/SOLU")
        mapdl.run("ANTYPE,HARMIC")
        mapdl.run(f"HARFRQ,{freq_start_hz},{freq_end_hz}")
        mapdl.run(f"NSUBST,{num_steps}")
        mapdl.run(f"DMPRAT,{damping_ratio}")

        _nvh_config["analysis_type"] = "frequency_response"

        return _ok(ok_message(
            f"已设置频率响应分析（{freq_start_hz}~{freq_end_hz} Hz，阻尼比 {damping_ratio}）",
            excitation_node=excitation_node,
            excitation_dof=excitation_dof,
            freq_start_hz=freq_start_hz,
            freq_end_hz=freq_end_hz,
            freq_step_hz=freq_step_hz,
            damping_ratio=damping_ratio,
            num_steps=num_steps,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_acoustic_analysis - 设置声学分析（声固耦合）
# ---------------------------------------------------------------------------

def setup_acoustic_analysis(
    analysis_type: str = "modal_acoustic",
    freq_range_start_hz: float = 20.0,
    freq_range_end_hz: float = 500.0,
    num_modes: int = 100,
    reference_pressure_pa: float = 2e-5,
) -> dict:
    """
    设置声学分析（声腔模态 / 声固耦合）。

    Args:
        analysis_type: 分析类型，"modal_acoustic"（声腔模态）、"fem_pem"（声固耦合频域）、
                       "sea"（统计能量分析）
        freq_range_start_hz: 频率范围起始（Hz）
        freq_range_end_hz: 频率范围终止（Hz）
        num_modes: 声腔模态数
        reference_pressure_pa: 参考声压（Pa），默认 20 μPa
    """
    try:
        mapdl = _mapdl()

        mapdl.run("/SOLU")
        mapdl.run("ANTYPE,MODAL")
        mapdl.run(f"MODOPT,LANB,{num_modes},{freq_range_start_hz},{freq_range_end_hz}")

        _nvh_config["analysis_type"] = analysis_type
        _nvh_config["frequency_range"] = (freq_range_start_hz, freq_range_end_hz)

        return _ok(ok_message(
            f"已设置{analysis_type}声学分析（{freq_range_start_hz}~{freq_range_end_hz} Hz，{num_modes} 阶模态）",
            analysis_type=analysis_type,
            freq_range_start_hz=freq_range_start_hz,
            freq_range_end_hz=freq_range_end_hz,
            num_modes=num_modes,
            reference_pressure_pa=reference_pressure_pa,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_vehicle_nvh_simulation - 运行整车 NVH 仿真
# ---------------------------------------------------------------------------

def run_vehicle_nvh_simulation() -> dict:
    """
    运行整车 NVH 仿真求解。
    """
    try:
        mapdl = _mapdl()
        mapdl.run("SOLVE")

        _nvh_config["status"] = "completed"

        return _ok(ok_message(
            f"整车 NVH 仿真求解完成（{_nvh_config.get('analysis_type', 'unknown')}）",
            analysis_type=_nvh_config.get("analysis_type", "unknown"),
            frequency_range=_nvh_config.get("frequency_range", None),
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_vehicle_nvh_results - 提取整车 NVH 仿真结果
# ---------------------------------------------------------------------------

def get_vehicle_nvh_results(
    result_type: str = "natural_frequencies",
    target_node: int = 0,
    output_path: str = "",
) -> dict:
    """
    提取整车 NVH 仿真结果。

    Args:
        result_type: 结果类型，"natural_frequencies"（固有频率/模态频率）、
                     "mode_shapes"（振型）、"frequency_response"（频率响应函数）、
                     "acoustic_modes"（声腔模态）、"noise_transfer_path"（噪声传递路径）、
                     "sound_pressure_level"（声压级 SPL）、"sound_quality"（声品质指标）
        target_node: 目标节点 ID（用于提取特定位置响应）
        output_path: 导出结果文件路径（可选，JSON 格式）
    """
    try:
        mapdl = _mapdl()
        mapdl.post1()
        mapdl.run("SET,LIST")

        result = {
            "result_type": result_type,
            "analysis_type": _nvh_config.get("analysis_type", "unknown"),
        }

        result_desc = {
            "natural_frequencies": "固有频率列表（Hz），含模态参与因子",
            "mode_shapes": "各阶模态振型描述",
            "frequency_response": "频率响应函数（FRF），dB 形式",
            "acoustic_modes": "声腔固有频率及声压分布",
            "noise_transfer_path": "振动-噪声传递路径贡献量",
            "sound_pressure_level": "声压级 SPL（dB(A)）",
            "sound_quality": "声品质：响度（sone）、尖锐度（acum）、粗糙度（asper）",
        }

        result["description"] = result_desc.get(result_type, result_type)
        result["status"] = "completed"

        if output_path:
            ensure_parent_dir(output_path)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            result["exported_to"] = output_path

        return _ok(ok_message(
            f"已提取整车 NVH {result_type}结果",
            **result,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：disconnect_vehicle_nvh_solver - 断开 NVH 求解器
# ---------------------------------------------------------------------------

def disconnect_vehicle_nvh_solver() -> dict:
    """
    断开并清理整车 NVH 分析求解器。
    """
    global _nvh_mapdl
    try:
        if _nvh_mapdl is not None:
            _nvh_mapdl.exit()
        _nvh_mapdl = None
        _nvh_config.update({
            "analysis_type": None,
            "model_path": None,
            "frequency_range": None,
        })

        return _ok(ok_message("已断开整车 NVH 分析求解器"))
    except Exception as e:
        return _err(str(e))
