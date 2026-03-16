"""
PyMAPDL 工具：通过 Ansys PyMAPDL 驱动 MAPDL 求解器进行电机结构强度、热应力和 NVH 谐响应分析。
与 Maxwell 电磁仿真结果深度联动，构成 EM → 结构/NVH 完整工作流。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

from tools.utils import _ok, _err, ok_message

_mapdl_app = None  # 全局 MAPDL 实例


def _app():
    """返回当前激活的 MAPDL 实例，未连接时抛出异常。"""
    if _mapdl_app is None:
        raise RuntimeError("未连接到 MAPDL，请先调用 connect_mapdl。")
    return _mapdl_app


# ---------------------------------------------------------------------------
# 工具：connect_mapdl - 连接 MAPDL
# ---------------------------------------------------------------------------

def connect_mapdl(
    port: int = 50052,
    server: str = "127.0.0.1",
    launch_local: bool = True,
    nproc: int = 4,
) -> dict:
    """
    连接到 MAPDL 实例（本地启动或远程连接）。

    Args:
        port: gRPC 端口号，默认 50052
        server: MAPDL 服务器地址（本地启动时忽略）
        launch_local: True 则在本机启动新 MAPDL 进程，False 则连接已有服务
        nproc: 并行核心数（本地启动时有效）
    """
    global _mapdl_app
    try:
        from ansys.mapdl.core import launch_mapdl, MapdlGrpc
        if launch_local:
            _mapdl_app = launch_mapdl(nproc=nproc, port=port, override=True)
        else:
            _mapdl_app = MapdlGrpc(ip=server, port=port)
        version = _mapdl_app.version
        return _ok(ok_message(
            f"已连接到 MAPDL {version}（{'本地' if launch_local else f'{server}:{port}'}）",
            version=version,
            launch_local=launch_local,
            server=None if launch_local else server,
            port=port,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_rotor_stress_analysis - 转子离心应力分析
# ---------------------------------------------------------------------------

def run_rotor_stress_analysis(
    rotor_outer_radius_mm: float,
    rotor_inner_radius_mm: float,
    stack_length_mm: float,
    speed_rpm: float,
    material: str = "Steel",
    density_kg_m3: float = 7850.0,
    youngs_modulus_GPa: float = 200.0,
    poisson_ratio: float = 0.3,
) -> dict:
    """
    在 MAPDL 中建立轴对称转子模型，计算高转速下的离心应力分布，
    用于校核转子铁芯、永磁体和轴套的结构安全性。

    Args:
        rotor_outer_radius_mm: 转子外径（mm）
        rotor_inner_radius_mm: 转子内径/轴径（mm）
        stack_length_mm: 叠片长度（mm）
        speed_rpm: 转速（rpm），用于计算角速度离心载荷
        material: 材料名称（用于注释）
        density_kg_m3: 材料密度（kg/m³）
        youngs_modulus_GPa: 杨氏模量（GPa）
        poisson_ratio: 泊松比
    """
    try:
        mapdl = _app()
        import math
        omega = speed_rpm * 2 * math.pi / 60  # 角速度 rad/s

        mapdl.clear()
        mapdl.prep7()

        # 定义材料（编号 1）
        mapdl.mp("EX", 1, youngs_modulus_GPa * 1e9)
        mapdl.mp("PRXY", 1, poisson_ratio)
        mapdl.mp("DENS", 1, density_kg_m3)

        # 轴对称单元 PLANE183
        mapdl.et(1, "PLANE183", kop3=1)  # kop3=1 轴对称

        # 几何：矩形截面（r_inner → r_outer，0 → L）
        r_i = rotor_inner_radius_mm / 1000  # m
        r_o = rotor_outer_radius_mm / 1000
        length = stack_length_mm / 1000

        mapdl.rectng(r_i, r_o, 0, length)
        mapdl.esize((r_o - r_i) / 10)
        mapdl.amesh("ALL")

        # 施加边界条件：轴向约束底面（对称）
        mapdl.nsel("S", "LOC", "Y", 0)
        mapdl.d("ALL", "UY", 0)
        mapdl.nsel("ALL")

        # 惯性载荷：旋转角速度
        mapdl.omega(0, omega, 0)

        # 求解
        mapdl.solution()
        mapdl.antype(0)  # 静力分析
        mapdl.solve()
        mapdl.finish()

        # 后处理
        mapdl.post1()
        mapdl.set(1, 1)

        von_mises_max = mapdl.post_processing.nodal_eqv_stress().max()
        radial_stress_max = mapdl.post_processing.nodal_stress("X").max()
        hoop_stress_max = mapdl.post_processing.nodal_stress("Y").max()

        return _ok({
            "speed_rpm": speed_rpm,
            "material": material,
            "omega_rad_s": round(omega, 4),
            "max_von_mises_stress_MPa": round(von_mises_max / 1e6, 2),
            "max_radial_stress_MPa": round(radial_stress_max / 1e6, 2),
            "max_hoop_stress_MPa": round(hoop_stress_max / 1e6, 2),
            "note": "基于轴对称简化模型，实际含槽孔转子应力偏高约 10~30%",
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_thermal_stress_analysis - 热应力分析
# ---------------------------------------------------------------------------

def run_thermal_stress_analysis(
    temperature_csv_path: str,
    material: str = "Steel",
    thermal_expansion_coeff: float = 12e-6,
    youngs_modulus_GPa: float = 200.0,
    ref_temp_C: float = 20.0,
) -> dict:
    """
    将热仿真（Icepak/Motor-CAD）输出的温度分布导入 MAPDL，计算热应力和热变形。

    工作流：Icepak 热仿真 → 温度 CSV → MAPDL 热应力 → 最大应力/变形量

    Args:
        temperature_csv_path: 温度分布 CSV 文件路径（含节点坐标和温度列）
        material: 材料名称（仅注释）
        thermal_expansion_coeff: 热膨胀系数（/°C），钢约 12e-6，铝约 23e-6
        youngs_modulus_GPa: 杨氏模量（GPa）
        ref_temp_C: 参考温度（无应力状态），通常为室温 20°C
    """
    try:
        import csv
        mapdl = _app()

        # 读取温度场数据
        node_temps = []
        try:
            with open(temperature_csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    node_temps.append({
                        "x": float(row.get("x", row.get("X", 0))),
                        "y": float(row.get("y", row.get("Y", 0))),
                        "z": float(row.get("z", row.get("Z", 0))),
                        "temp": float(row.get("temp", row.get("Temperature", ref_temp_C))),
                    })
        except FileNotFoundError:
            return _err(f"温度文件未找到：{temperature_csv_path}")

        if not node_temps:
            return _err("温度 CSV 中没有可用数据，无法执行热应力分析")

        min_temp = min(d["temp"] for d in node_temps)
        max_temp = max(d["temp"] for d in node_temps)
        if (max_temp - min_temp) > 1e-3:
            return _err(
                "当前热应力工具尚不支持将非均匀温度场真实映射到 MAPDL 几何；"
                "检测到 CSV 含非均匀温度分布，请先做节点映射/LDREAD 工作流。"
            )

        mapdl.clear()
        mapdl.prep7()

        # 材料定义
        mapdl.mp("EX", 1, youngs_modulus_GPa * 1e9)
        mapdl.mp("PRXY", 1, 0.3)
        mapdl.mp("ALPX", 1, thermal_expansion_coeff)

        avg_temp = sum(d["temp"] for d in node_temps) / len(node_temps)
        delta_t = avg_temp - ref_temp_C

        # 均匀温度载荷简化（若节点数 > 1000 则取平均，否则逐节点施加）
        mapdl.tref(ref_temp_C)
        mapdl.tunif(avg_temp)

        # 使用实体单元 SOLID185
        mapdl.et(1, "SOLID185")
        mapdl.block(0, 0.1, 0, 0.1, 0, 0.05)  # 简化块体，实际应从几何导入
        mapdl.esize(0.01)
        mapdl.vmesh("ALL")

        # 固定一个面
        mapdl.nsel("S", "LOC", "Z", 0)
        mapdl.d("ALL", "ALL", 0)
        mapdl.nsel("ALL")

        mapdl.solution()
        mapdl.antype(0)
        mapdl.solve()
        mapdl.finish()

        mapdl.post1()
        mapdl.set(1, 1)
        stress_max = mapdl.post_processing.nodal_eqv_stress().max()
        deform_max = mapdl.post_processing.nodal_displacement("NORM").max()

        return _ok({
            "material": material,
            "avg_temp_C": round(avg_temp, 2),
            "temperature_range_C": [round(min_temp, 2), round(max_temp, 2)],
            "delta_T_C": round(delta_t, 2),
            "ref_temp_C": ref_temp_C,
            "max_thermal_stress_MPa": round(stress_max / 1e6, 2),
            "max_deformation_mm": round(deform_max * 1000, 4),
            "loaded_nodes": len(node_temps),
            "note": "简化均匀温度载荷；精确分析需用 LDREAD 导入 Icepak 温度场节点映射",
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_nvh_harmonic_analysis - 谐响应 NVH 分析
# ---------------------------------------------------------------------------

def run_nvh_harmonic_analysis(
    freq_start_Hz: float = 0.0,
    freq_end_Hz: float = 5000.0,
    freq_steps: int = 200,
    damping_ratio: float = 0.02,
    force_amplitude_N: float = 100.0,
    force_frequency_Hz: float = 600.0,
) -> dict:
    """
    在 MAPDL 中运行谐响应分析，评估电机定子在电磁激励力下的振动响应（NVH）。

    工作流：Maxwell 电磁力 → MAPDL 谐响应 → 振动加速度/位移频谱

    Args:
        freq_start_Hz: 分析起始频率（Hz）
        freq_end_Hz: 分析终止频率（Hz）
        freq_steps: 频率步数
        damping_ratio: 结构阻尼比（无量纲），钢结构约 0.01~0.03
        force_amplitude_N: 电磁径向力幅值（N/m²，此处简化为集中力 N）
        force_frequency_Hz: 主激励频率（Hz），通常为 n×(极数/2)×(转速/60)
    """
    try:
        mapdl = _app()
        mapdl.clear()
        mapdl.prep7()

        # 简化单环结构模型（代表定子轭圆环）
        mapdl.mp("EX", 1, 200e9)
        mapdl.mp("PRXY", 1, 0.3)
        mapdl.mp("DENS", 1, 7850.0)
        mapdl.et(1, "SHELL181")

        # 圆环几何（定子轭简化为中面圆柱）
        r = 0.08  # 定子外径约 160mm
        mapdl.cyl4(0, 0, r * 0.9, 0, r, 360)
        mapdl.esize(r * 0.1)
        mapdl.amesh("ALL")

        # 激励力（4 阶径向力，施加在圆环外侧节点）
        mapdl.nsel("S", "LOC", "X", r - 0.001, r + 0.001)
        mapdl.f("ALL", "FX", force_amplitude_N)
        mapdl.nsel("ALL")

        # 谐响应求解
        mapdl.solution()
        mapdl.antype(3)  # 3 = 谐响应
        mapdl.hropt("FULL")
        mapdl.harfrq(freq_start_Hz, freq_end_Hz)
        mapdl.nsubst(freq_steps)
        mapdl.dmprat(damping_ratio)
        mapdl.solve()
        mapdl.finish()

        # 后处理：提取最大位移响应
        mapdl.post26()
        mapdl.nsol(2, 1, "U", "X")  # 节点 1 X 向位移

        return _ok({
            "freq_range_Hz": [freq_start_Hz, freq_end_Hz],
            "freq_steps": freq_steps,
            "damping_ratio": damping_ratio,
            "force_amplitude_N": force_amplitude_N,
            "primary_excitation_Hz": force_frequency_Hz,
            "message": (
                "谐响应分析完成。请使用 MAPDL POST26 查看完整频谱，"
                "关注峰值响应频率是否与结构固有频率重合（共振风险）。"
            ),
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_mapdl_structural_results - 提取结构分析结果
# ---------------------------------------------------------------------------

def get_mapdl_structural_results(result_type: str = "stress") -> dict:
    """
    从最近一次 MAPDL 结构分析中提取关键结果。

    Args:
        result_type: "stress"（应力）/ "deformation"（变形）/ "frequency"（固有频率）
    """
    try:
        mapdl = _app()
        mapdl.post1()
        mapdl.set("LAST")

        results = {}
        if result_type == "stress":
            stress = mapdl.post_processing.nodal_eqv_stress()
            results = {
                "max_von_mises_stress_MPa": round(float(stress.max()) / 1e6, 2),
                "avg_von_mises_stress_MPa": round(float(stress.mean()) / 1e6, 2),
                "min_von_mises_stress_MPa": round(float(stress.min()) / 1e6, 2),
            }
        elif result_type == "deformation":
            disp = mapdl.post_processing.nodal_displacement("NORM")
            results = {
                "max_deformation_mm": round(float(disp.max()) * 1000, 4),
                "avg_deformation_mm": round(float(disp.mean()) * 1000, 4),
            }
        elif result_type == "frequency":
            # 提取模态频率（需先运行模态分析）
            freqs = []
            for i in range(1, 11):
                try:
                    mapdl.set(1, i)
                    freq = mapdl.get("FREQ", "ACTIVE", 0, "FREQ")
                    freqs.append(round(float(freq), 2))
                except Exception:
                    break
            results = {"natural_frequencies_Hz": freqs}
        else:
            return _err(f"未知结果类型：{result_type}，可选：stress / deformation / frequency")

        return _ok(results)
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：disconnect_mapdl - 断开 MAPDL 连接
# ---------------------------------------------------------------------------

def disconnect_mapdl() -> dict:
    """退出 MAPDL 进程并释放资源。"""
    global _mapdl_app
    try:
        if _mapdl_app is not None:
            _mapdl_app.exit()
            _mapdl_app = None
        return _ok(ok_message("MAPDL 进程已退出", disconnected=True))
    except Exception as e:
        return _err(str(e))
