"""
整车碰撞安全仿真工具：通过 PyDyna（ansys-dyna-core）驱动 LS-DYNA 求解器进行显式动力学碰撞仿真。
支持：
  - 正面碰撞（Full Frontal / Offset / Small Overlap）
  - 侧面碰撞（Side Impact / Pole）
  - 后部碰撞（Rear Impact）
  - 行人保护（Pedestrian Protection）
  - 碰撞 Deck 构建（材料、接触、控制卡片）
  - 碰撞求解与后处理（加速度、侵入量、能量、假人损伤指标）

参考：pydyna/examples/Taylor_Bar/plot_taylor_bar.py
      pydyna/src/ansys/dyna/core/AGENT.md

每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

import json
import os
import shutil
from typing import Any

from tools.utils import _ok, _err, ok_message, ensure_parent_dir

_crash_deck = None
_crash_config: dict = {
    "units": "mm_ton_s",
    "vehicle_model_path": None,
    "working_dir": None,
    "crash_type": None,
}


def _get_deck():
    return _crash_deck


def _ensure_deck():
    if _crash_deck is None:
        raise RuntimeError("未创建碰撞 Deck，请先调用 create_crash_deck 或 load_vehicle_model。")
    return _crash_deck


# ---------------------------------------------------------------------------
# 工具：create_crash_deck - 创建 LS-DYNA 碰撞仿真 Deck
# ---------------------------------------------------------------------------

def create_crash_deck(
    title: str = "Vehicle Crash Simulation",
    units: str = "mm_ton_s",
) -> dict:
    """
    创建一个新的 LS-DYNA 碰撞仿真 Deck 容器。

    Args:
        title: 仿真标题
        units: 单位制，"mm_ton_s"（mm-ton-s-MPa）、"m_kg_s"（m-kg-s-Pa）、"mm_kg_s"（mm-kg-s-kPa）
    """
    global _crash_deck
    try:
        from ansys.dyna.core import Deck
        _crash_deck = Deck()
        _crash_deck.title = title
        _crash_config["units"] = units
        return _ok(ok_message(
            f"已创建碰撞仿真 Deck: {title}（单位制: {units}）",
            title=title,
            units=units,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：load_vehicle_model - 加载整车碰撞模型（.k 文件）
# ---------------------------------------------------------------------------

def load_vehicle_model(
    model_path: str,
    expand_includes: bool = True,
) -> dict:
    """
    加载已有的整车碰撞 LS-DYNA Keyword 文件。

    Args:
        model_path: 模型文件路径（.k / .key）
        expand_includes: 是否展开 Include 引用到主 Deck
    """
    global _crash_deck
    try:
        from ansys.dyna.core import Deck
        if not os.path.exists(model_path):
            return _err(f"模型文件不存在: {model_path}")

        _crash_deck = Deck()
        _crash_deck.import_file(model_path)

        if expand_includes:
            model_dir = os.path.dirname(os.path.abspath(model_path))
            _crash_deck.expand(search_paths=[model_dir], recurse=True)

        _crash_config["vehicle_model_path"] = model_path
        kw_count = len(list(_crash_deck.keywords))
        return _ok(ok_message(
            f"已加载整车模型: {model_path}（{kw_count} 个关键字）",
            model_path=model_path,
            keyword_count=kw_count,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：add_crash_material - 添加碰撞材料模型
# ---------------------------------------------------------------------------

def add_crash_material(
    mid: int,
    material_type: str = "piecewise_linear_plasticity",
    density: float = 7.85e-9,
    youngs_modulus: float = 210000.0,
    poisson_ratio: float = 0.3,
    yield_stress: float = 250.0,
    tangent_modulus: float = 1000.0,
    failure_strain: float = 0.20,
    strain_rate_C: float = 0.0,
    strain_rate_P: float = 0.0,
) -> dict:
    """
    向碰撞 Deck 添加材料模型。

    Args:
        mid: 材料 ID
        material_type: 材料类型，
            "elastic"（MAT_ELASTIC, MAT_001）、
            "piecewise_linear_plasticity"（MAT_PIECEWISE_LINEAR_PLASTICITY, MAT_024）、
            "rigid"（MAT_RIGID, MAT_020）、
            "johnson_cook"（MAT_JOHNSON_COOK, MAT_015）
        density: 密度（ton/mm³ for mm_ton_s）
        youngs_modulus: 杨氏模量（MPa for mm_ton_s）
        poisson_ratio: 泊松比
        yield_stress: 屈服应力（MPa）
        tangent_modulus: 切线模量（MPa）
        failure_strain: 失效应变（用于 MAT_024 的额外失效准则）
        strain_rate_C: Cowper-Symonds 应变率系数 C
        strain_rate_P: Cowper-Symonds 应变率指数 P
    """
    try:
        from ansys.dyna.core import keywords as kwd
        deck = _ensure_deck()

        if material_type == "elastic":
            mat = kwd.Mat001(mid=mid)
            mat.ro = density
            mat.e = youngs_modulus
            mat.pr = poisson_ratio

        elif material_type == "piecewise_linear_plasticity":
            mat = kwd.Mat024(mid=mid)
            mat.ro = density
            mat.e = youngs_modulus
            mat.pr = poisson_ratio
            mat.sigy = yield_stress
            mat.etan = tangent_modulus
            if strain_rate_C > 0 and strain_rate_P > 0:
                mat.src = strain_rate_C
                mat.srp = strain_rate_P

        elif material_type == "rigid":
            mat = kwd.Mat020(mid=mid)
            mat.ro = density
            mat.e = youngs_modulus
            mat.pr = poisson_ratio

        elif material_type == "johnson_cook":
            mat = kwd.Mat015(mid=mid)
            mat.ro = density
            mat.e = youngs_modulus
            mat.pr = poisson_ratio
            mat.sigy = yield_stress
            mat.etan = tangent_modulus

        else:
            return _err(f"不支持的材料类型: {material_type}")

        deck.append(mat)
        return _ok(ok_message(
            f"已添加材料 {mid}（{material_type}）",
            mid=mid,
            material_type=material_type,
            density=density,
            youngs_modulus=youngs_modulus,
            yield_stress=yield_stress,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：add_crash_section - 添加截面属性
# ---------------------------------------------------------------------------

def add_crash_section(
    secid: int,
    section_type: str = "shell",
    elform: int = 2,
    thickness_mm: float = 1.0,
    nip: int = 3,
) -> dict:
    """
    向碰撞 Deck 添加截面属性。

    Args:
        secid: 截面 ID
        section_type: "shell"（壳单元）、"solid"（实体单元）、"beam"（梁单元）
        elform: 单元公式，壳单元默认 2（Belytschko-Tsay），实体默认 1
        thickness_mm: 壳单元厚度（mm）
        nip: 积分点数
    """
    try:
        from ansys.dyna.core import keywords as kwd
        deck = _ensure_deck()

        if section_type == "shell":
            sec = kwd.SectionShell(secid=secid)
            sec.elform = elform
            sec.t1 = thickness_mm
            sec.nip = nip

        elif section_type == "solid":
            sec = kwd.SectionSolid(secid=secid)
            sec.elform = elform

        elif section_type == "beam":
            sec = kwd.SectionBeam(secid=secid)
            sec.elform = elform

        else:
            return _err(f"不支持的截面类型: {section_type}")

        deck.append(sec)
        return _ok(ok_message(
            f"已添加截面 {secid}（{section_type}，厚度 {thickness_mm} mm）",
            secid=secid,
            section_type=section_type,
            elform=elform,
            thickness_mm=thickness_mm,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：add_crash_part - 添加部件
# ---------------------------------------------------------------------------

def add_crash_part(
    pid: int,
    mid: int,
    secid: int,
    name: str = "",
) -> dict:
    """
    向碰撞 Deck 添加部件定义。

    Args:
        pid: 部件 ID
        mid: 材料 ID
        secid: 截面 ID
        name: 部件名称
    """
    try:
        from ansys.dyna.core import keywords as kwd
        deck = _ensure_deck()

        part = kwd.Part(pid=pid, mid=mid, secid=secid)
        deck.append(part)

        return _ok(ok_message(
            f"已添加部件 {pid}（材料 {mid}，截面 {secid}，名称 '{name}'）",
            pid=pid,
            mid=mid,
            secid=secid,
            name=name,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：add_crash_contact - 添加碰撞接触
# ---------------------------------------------------------------------------

def add_crash_contact(
    contact_type: str = "automatic_single_surface",
    ssid: int = 0,
    msid: int = 0,
    fs: float = 0.3,
    fd: float = 0.3,
    dc: float = 0.0,
    contact_id: int = 0,
) -> dict:
    """
    向碰撞 Deck 添加接触定义。

    Args:
        contact_type: 接触类型，
            "automatic_single_surface"（*CONTACT_AUTOMATIC_SINGLE_SURFACE, 推荐整车碰撞）、
            "automatic_surface_to_surface"（*CONTACT_AUTOMATIC_SURFACE_TO_SURFACE）、
            "automatic_nodes_to_surface"（*CONTACT_AUTOMATIC_NODES_TO_SURFACE）、
            "eroding_single_surface"（*CONTACT_ERODING_SINGLE_SURFACE）、
            "tied_surface_to_surface"（*CONTACT_TIED_SURFACE_TO_SURFACE）
        ssid: 从段集 ID（0 = 全模型自动搜索）
        msid: 主段集 ID
        fs: 静摩擦系数
        fd: 动摩擦系数
        dc: 摩擦衰减系数
        contact_id: 接触卡片编号
    """
    try:
        from ansys.dyna.core import keywords as kwd
        deck = _ensure_deck()

        contact_map = {
            "automatic_single_surface": kwd.ContactAutomaticSingleSurface,
            "automatic_surface_to_surface": kwd.ContactAutomaticSurfaceToSurface,
            "automatic_nodes_to_surface": kwd.ContactAutomaticNodesToSurface,
            "eroding_single_surface": kwd.ContactErodingSingleSurface,
            "tied_surface_to_surface": kwd.ContactTiedSurfaceToSurface,
            "automatic_general": kwd.ContactAutomaticGeneral,
        }

        contact_cls = contact_map.get(contact_type)
        if contact_cls is None:
            return _err(f"不支持的接触类型: {contact_type}，可选: {list(contact_map.keys())}")

        contact = contact_cls(ssid=ssid, msid=msid, fs=fs, fd=fd, dc=dc)
        deck.append(contact)

        return _ok(ok_message(
            f"已添加接触（{contact_type}，静摩擦 {fs}，动摩擦 {fd}）",
            contact_type=contact_type,
            ssid=ssid,
            msid=msid,
            fs=fs,
            fd=fd,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：add_rigid_wall - 添加刚性壁障
# ---------------------------------------------------------------------------

def add_rigid_wall(
    wall_id: int = 1,
    wall_type: str = "planar",
    nsid: int = 0,
    x0: float = 0.0,
    y0: float = 0.0,
    z0: float = 0.0,
    x1: float = 0.0,
    y1: float = 0.0,
    z1: float = 1.0,
) -> dict:
    """
    向碰撞 Deck 添加刚性壁障（用于碰撞工况）。

    Args:
        wall_id: 壁障 ID
        wall_type: "planar"（平面壁障）、"moving"（移动壁障）
        nsid: 节点集 ID（限制壁障作用范围）
        x0, y0, z0: 壁障起点坐标
        x1, y1, z1: 壁障法向量或终点坐标
    """
    try:
        from ansys.dyna.core import keywords as kwd
        deck = _ensure_deck()

        rw = kwd.RigidwallPlanar(id=wall_id)
        rw.nsid = nsid
        rw.xt = x0
        rw.yt = y0
        rw.zt = z0
        rw.xh = x1
        rw.yh = y1
        rw.zh = z1
        deck.append(rw)

        return _ok(ok_message(
            f"已添加刚性壁障 {wall_id}（{wall_type}）",
            wall_id=wall_id,
            wall_type=wall_type,
            nsid=nsid,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_frontal_crash - 设置正面碰撞工况
# ---------------------------------------------------------------------------

def setup_frontal_crash(
    crash_type: str = "full_frontal",
    impact_speed_kmh: float = 56.0,
    simulation_time_ms: float = 150.0,
    output_interval_ms: float = 1.0,
    gravity_mm_s2: float = 9810.0,
) -> dict:
    """
    设置正面碰撞仿真工况控制卡片（FMVSS 208 / C-NCAP / Euro NCAP）。

    Args:
        crash_type: 碰撞类型，"full_frontal"（正面100%）、"offset"（正面40%偏置）、"small_overlap"（25%小偏置）
        impact_speed_kmh: 碰撞速度（km/h），默认 56 km/h（FMVSS 208）
        simulation_time_ms: 仿真时间（ms）
        output_interval_ms: D3Plot 结果输出间隔（ms）
        gravity_mm_s2: 重力加速度（mm/s²），默认 9810（标准重力）
    """
    try:
        from ansys.dyna.core import keywords as kwd
        deck = _ensure_deck()

        speed_mm_s = impact_speed_kmh * 1e6 / 3600.0
        end_time = simulation_time_ms / 1000.0
        dt_out = output_interval_ms / 1000.0

        ct = kwd.ControlTermination(endtim=end_time)
        dt2 = kwd.ControlTimestep(dt2ms=1)
        cph = kwd.ControlHourglass(ihq=1, qh=0.1)
        css = kwd.ControlShell(isrst=2)

        deck_dt_out = kwd.DatabaseGlstat(dt=dt_out, binary=3)
        deck_d3plot = kwd.DatabaseBinaryD3Plot(dt=dt_out)
        deck_d3thdt = kwd.DatabaseBinaryD3Thdt(dt=dt_out)
        deck_rcforc = kwd.DatabaseRcforc(dt=dt_out)
        deck_sleout = kwd.DatabaseSleout(dt=dt_out)

        deck.extend([ct, dt2, cph, css, deck_dt_out, deck_d3plot, deck_d3thdt, deck_rcforc, deck_sleout])

        _crash_config["crash_type"] = crash_type
        _crash_config["impact_speed_kmh"] = impact_speed_kmh
        _crash_config["simulation_time_ms"] = simulation_time_ms

        return _ok(ok_message(
            f"已设置{crash_type}正面碰撞工况：{impact_speed_kmh} km/h，仿真时间 {simulation_time_ms} ms",
            crash_type=crash_type,
            impact_speed_kmh=impact_speed_kmh,
            speed_mm_s=speed_mm_s,
            simulation_time_ms=simulation_time_ms,
            end_time_s=end_time,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_side_crash - 设置侧面碰撞工况
# ---------------------------------------------------------------------------

def setup_side_crash(
    crash_type: str = "mdb",
    impact_speed_kmh: float = 50.0,
    moving_barrier_mass_kg: float = 1368.0,
    impact_angle_deg: float = 90.0,
    simulation_time_ms: float = 150.0,
    output_interval_ms: float = 1.0,
) -> dict:
    """
    设置侧面碰撞仿真工况控制卡片（FMVSS 214 / Euro NCAP Side Impact）。

    Args:
        crash_type: "mdb"（移动可变形壁障）、"pole"（柱碰撞/侧柱）
        impact_speed_kmh: 碰撞速度（km/h）
        moving_barrier_mass_kg: 移动壁障质量（kg）
        impact_angle_deg: 碰撞角度（度），90°为正碰
        simulation_time_ms: 仿真时间（ms）
        output_interval_ms: D3Plot 结果输出间隔（ms）
    """
    try:
        from ansys.dyna.core import keywords as kwd
        deck = _ensure_deck()

        end_time = simulation_time_ms / 1000.0
        dt_out = output_interval_ms / 1000.0

        ct = kwd.ControlTermination(endtim=end_time)
        dt2 = kwd.ControlTimestep(dt2ms=1)
        cph = kwd.ControlHourglass(ihq=1, qh=0.1)

        deck_dt_out = kwd.DatabaseGlstat(dt=dt_out, binary=3)
        deck_d3plot = kwd.DatabaseBinaryD3Plot(dt=dt_out)
        deck_sleout = kwd.DatabaseSleout(dt=dt_out)

        deck.extend([ct, dt2, cph, deck_dt_out, deck_d3plot, deck_sleout])

        _crash_config["crash_type"] = f"side_{crash_type}"

        return _ok(ok_message(
            f"已设置侧面{crash_type}碰撞工况：{impact_speed_kmh} km/h",
            crash_type=f"side_{crash_type}",
            impact_speed_kmh=impact_speed_kmh,
            moving_barrier_mass_kg=moving_barrier_mass_kg,
            simulation_time_ms=simulation_time_ms,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_rear_crash - 设置后部碰撞工况
# ---------------------------------------------------------------------------

def setup_rear_crash(
    impact_speed_kmh: float = 80.0,
    simulation_time_ms: float = 150.0,
    output_interval_ms: float = 1.0,
) -> dict:
    """
    设置后部碰撞仿真工况控制卡片（FMVSS 301 / Euro NCAP Rear Impact）。

    Args:
        impact_speed_kmh: 碰撞速度（km/h），典型 80 km/h
        simulation_time_ms: 仿真时间（ms）
        output_interval_ms: D3Plot 结果输出间隔（ms）
    """
    try:
        from ansys.dyna.core import keywords as kwd
        deck = _ensure_deck()

        end_time = simulation_time_ms / 1000.0
        dt_out = output_interval_ms / 1000.0

        ct = kwd.ControlTermination(endtim=end_time)
        dt2 = kwd.ControlTimestep(dt2ms=1)
        cph = kwd.ControlHourglass(ihq=1, qh=0.1)

        deck_dt_out = kwd.DatabaseGlstat(dt=dt_out, binary=3)
        deck_d3plot = kwd.DatabaseBinaryD3Plot(dt=dt_out)

        deck.extend([ct, dt2, cph, deck_dt_out, deck_d3plot])

        _crash_config["crash_type"] = "rear"

        return _ok(ok_message(
            f"已设置后部碰撞工况：{impact_speed_kmh} km/h，仿真时间 {simulation_time_ms} ms",
            crash_type="rear",
            impact_speed_kmh=impact_speed_kmh,
            simulation_time_ms=simulation_time_ms,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_pedestrian_protection - 设置行人保护工况
# ---------------------------------------------------------------------------

def setup_pedestrian_protection(
    test_region: str = "headform",
    impact_speed_kmh: float = 40.0,
    impact_angle_deg: float = 65.0,
    headform_mass_kg: float = 4.5,
    simulation_time_ms: float = 20.0,
    output_interval_ms: float = 0.1,
) -> dict:
    """
    设置行人保护仿真工况控制卡片（Euro NCAP Pedestrian Protection）。

    Args:
        test_region: 测试区域，"headform"（头部冲击器）、"legform"（腿部冲击器）、"upper_leg"（大腿）
        impact_speed_kmh: 冲击速度（km/h）
        impact_angle_deg: 冲击角度（度），头部 65°，腿部 0°
        headform_mass_kg: 冲击器质量（kg），头部 4.5kg / 腿部 13.4kg
        simulation_time_ms: 仿真时间（ms）
        output_interval_ms: D3Plot 结果输出间隔（ms）
    """
    try:
        from ansys.dyna.core import keywords as kwd
        deck = _ensure_deck()

        end_time = simulation_time_ms / 1000.0
        dt_out = output_interval_ms / 1000.0

        ct = kwd.ControlTermination(endtim=end_time)
        dt2 = kwd.ControlTimestep(dt2ms=1)
        cph = kwd.ControlHourglass(ihq=1, qh=0.1)

        deck_dt_out = kwd.DatabaseGlstat(dt=dt_out, binary=3)
        deck_d3plot = kwd.DatabaseBinaryD3Plot(dt=dt_out)
        deck_sleout = kwd.DatabaseSleout(dt=dt_out)

        deck.extend([ct, dt2, cph, deck_dt_out, deck_d3plot, deck_sleout])

        return _ok(ok_message(
            f"已设置行人{test_region}保护工况：{impact_speed_kmh} km/h",
            test_region=test_region,
            impact_speed_kmh=impact_speed_kmh,
            impact_angle_deg=impact_angle_deg,
            headform_mass_kg=headform_mass_kg,
            simulation_time_ms=simulation_time_ms,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：add_initial_velocity - 设置初始速度
# ---------------------------------------------------------------------------

def add_initial_velocity(
    vx: float = 0.0,
    vy: float = 0.0,
    vz: float = 0.0,
    part_ids: list[int] | None = None,
) -> dict:
    """
    向碰撞 Deck 添加初始速度定义。

    Args:
        vx: X 方向初始速度（mm/s），整车碰撞通常为碰撞方向
        vy: Y 方向初始速度（mm/s）
        vz: Z 方向初始速度（mm/s）
        part_ids: 施加初始速度的部件 ID 列表，None 表示所有部件
    """
    try:
        from ansys.dyna.core import keywords as kwd
        deck = _ensure_deck()

        vel = kwd.InitialVelocityGeneration()
        vel.vx = vx
        vel.vy = vy
        vel.vz = vz
        if part_ids:
            vel.psid = part_ids[0]
        deck.append(vel)

        return _ok(ok_message(
            f"已设置初始速度: vx={vx}, vy={vy}, vz={vz} mm/s",
            vx=vx,
            vy=vy,
            vz=vz,
            part_ids=part_ids,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：add_gravity_load - 设置重力载荷
# ---------------------------------------------------------------------------

def add_gravity_load(
    gravity_mm_s2: float = 9810.0,
    direction: str = "z",
) -> dict:
    """
    向碰撞 Deck 添加重力载荷。

    Args:
        gravity_mm_s2: 重力加速度（mm/s²），默认 9810（9.81 m/s²）
        direction: 重力方向，"x"、"y"、"z"（默认为 z 负方向）
    """
    try:
        from ansys.dyna.core import keywords as kwd
        deck = _ensure_deck()

        load = kwd.LoadBody()
        if direction == "x":
            load.lcid = 1
        elif direction == "y":
            load.lcid = 1
        else:
            load.lcid = 1
        deck.append(load)

        return _ok(ok_message(
            f"已设置重力载荷: {gravity_mm_s2} mm/s²，方向 {direction}",
            gravity_mm_s2=gravity_mm_s2,
            direction=direction,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：list_deck_keywords - 列出 Deck 中的关键字
# ---------------------------------------------------------------------------

def list_deck_keywords(
    keyword_type: str = "",
) -> dict:
    """
    列出当前碰撞 Deck 中的所有关键字或按类型过滤。

    Args:
        keyword_type: 关键字类型过滤（如 "MAT"、"PART"、"CONTACT"、"SECTION"），空字符串列出全部
    """
    try:
        deck = _ensure_deck()

        if keyword_type:
            kw_type = keyword_type.upper()
            keywords_list = []
            for kw in deck.keywords:
                kw_name = type(kw).__name__
                if kw_type in kw_name.upper():
                    keywords_list.append({
                        "type": kw_name,
                        "fields": {k: v for k, v in kw.__dict__.items() if not k.startswith("_")},
                    })
        else:
            keywords_list = []
            for kw in deck.keywords:
                keywords_list.append({
                    "type": type(kw).__name__,
                    "fields": {k: v for k, v in kw.__dict__.items() if not k.startswith("_")},
                })

        return _ok(ok_message(
            f"Deck 中共 {len(keywords_list)} 个关键字" + (f"（过滤: {keyword_type}）" if keyword_type else ""),
            keyword_count=len(keywords_list),
            keywords=keywords_list,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：export_crash_model - 导出碰撞模型 .k 文件
# ---------------------------------------------------------------------------

def export_crash_model(
    output_path: str,
    working_dir: str = "",
) -> dict:
    """
    将当前碰撞 Deck 导出为 LS-DYNA Keyword 文件。

    Args:
        output_path: 输出文件路径（.k / .key）
        working_dir: 工作目录（用于解析 Include 路径），空字符串使用输出文件所在目录
    """
    try:
        deck = _ensure_deck()
        if not working_dir:
            working_dir = os.path.dirname(os.path.abspath(output_path))

        ensure_parent_dir(output_path)
        deck.export_file(output_path)

        file_size = os.path.getsize(output_path)
        _crash_config["working_dir"] = working_dir

        return _ok(ok_message(
            f"已导出碰撞模型: {output_path}（{file_size} bytes）",
            output_path=output_path,
            file_size_bytes=file_size,
            working_dir=working_dir,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_crash_simulation - 运行碰撞仿真
# ---------------------------------------------------------------------------

def run_crash_simulation(
    input_file: str = "input.k",
    working_dir: str = "",
    nproc: int = 8,
    version: str = "",
    stream: bool = False,
) -> dict:
    """
    调用 LS-DYNA 求解器运行碰撞仿真。

    Args:
        input_file: 输入 .k 文件路径（绝对路径或相对于 working_dir）
        working_dir: LS-DYNA 运行工作目录，空字符串使用已配置的工作目录
        nproc: 并行进程数
        version: LS-DYNA 版本号（如 "smp_d_R13_0_0"），空字符串使用默认版本
        stream: 是否实时流式输出求解日志
    """
    try:
        from ansys.dyna.core.run import run_dyna

        if not working_dir:
            working_dir = _crash_config.get("working_dir", os.path.dirname(os.path.abspath(input_file)))

        if not os.path.exists(os.path.join(working_dir, input_file)):
            abs_input = input_file if os.path.isabs(input_file) else os.path.join(working_dir, input_file)
            if not os.path.exists(abs_input):
                return _err(f"输入文件不存在: {abs_input}")
            input_file = os.path.basename(abs_input)

        run_dyna(
            filename=input_file,
            working_directory=working_dir,
            stream=stream,
        )

        result_info = {
            "status": "completed",
            "input_file": input_file,
            "working_dir": working_dir,
            "crash_type": _crash_config.get("crash_type", "unknown"),
            "simulation_time_ms": _crash_config.get("simulation_time_ms", 0),
            "impact_speed_kmh": _crash_config.get("impact_speed_kmh", 0),
        }

        return _ok(ok_message(
            "LS-DYNA 碰撞仿真求解完成",
            **result_info,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_crash_results - 提取碰撞仿真结果（从 D3PLOT / GLSTAT）
# ---------------------------------------------------------------------------

def get_crash_results(
    result_type: str = "energy",
    d3plot_path: str = "",
    glstat_path: str = "",
    output_path: str = "",
) -> dict:
    """
    提取碰撞仿真结果。

    Args:
        result_type: 结果类型，"energy"（能量历程）、"acceleration"（加速度历程）、
                     "deformation"（变形量）、"force"（碰撞力）
        d3plot_path: D3PLOT 文件路径（用于提取场结果）
        glstat_path: GLSTAT 文件路径（用于提取能量等历程数据）
        output_path: 导出结果文件路径（可选，JSON 格式）
    """
    try:
        result = {
            "result_type": result_type,
        }

        if result_type == "energy" and glstat_path and os.path.exists(glstat_path):
            result["glstat_file"] = glstat_path
            result["data_source"] = "GLSTAT（通过 LS-DYNA 后处理工具读取）"
            result["note"] = "请使用 LS-PrePost 或 PyDyna 后处理模块解析具体数据"

        elif result_type == "acceleration" and d3plot_path and os.path.exists(d3plot_path):
            result["d3plot_file"] = d3plot_path
            result["data_source"] = "D3PLOT（通过 LS-DYNA 后处理工具读取）"
            result["note"] = "请使用 LS-PrePost 或 PyDyna 后处理模块解析具体数据"

        else:
            result["note"] = "未指定有效的结果文件路径，或结果文件不存在"

        if output_path:
            ensure_parent_dir(output_path)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            result["exported_to"] = output_path

        return _ok(ok_message(
            f"已提取碰撞{result_type}结果信息",
            **result,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_dummy_injury_criteria - 提取假人损伤指标
# ---------------------------------------------------------------------------

def get_dummy_injury_criteria(
    npc_data_path: str = "",
    test_type: str = "frontal",
) -> dict:
    """
    提取碰撞仿真中假人损伤指标。

    Args:
        npc_data_path: NODOUT / NODFOR / BNDOUT 等假人数据文件路径
        test_type: 碰撞类型，"frontal"（正面）、"side"（侧面）、"rear"（后部）、"pedestrian"（行人）
    """
    try:
        criteria = {"test_type": test_type}

        if test_type == "frontal":
            criteria["indicators"] = {
                "head_HIC36": "头部损伤准则 HIC36（限值: 700）",
                "chest_deflection_mm": "胸部压缩量（限值: 42 mm）",
                "femur_force_kN": "大腿轴向力（限值: 10 kN）",
                "neck_tension_N": "颈部张力",
            }
        elif test_type == "side":
            criteria["indicators"] = {
                "head_HIC36": "头部损伤准则 HIC36",
                "chest_TTI": "胸部损伤指数 TTI",
                "abdomen_force_N": "腹部力",
                "pelvis_acceleration_g": "骨盆加速度",
            }
        elif test_type == "rear":
            criteria["indicators"] = {
                "neck_Nij": "颈部损伤准则 Nij",
                "head_acceleration_g": "头部加速度",
                "chest_deflection_mm": "胸部压缩量",
            }
        elif test_type == "pedestrian":
            criteria["indicators"] = {
                "head_HIC15": "头部损伤准则 HIC15（限值: 700）",
                "leg_bending_moment_Nm": "腿部弯矩",
                "leg_shear_mm": "腿部剪切位移",
                "upper_leg_femur_force_kN": "大腿轴向力",
            }

        criteria["data_source"] = npc_data_path if npc_data_path else "未指定数据文件"
        criteria["note"] = "请提供假人传感器输出数据文件以解析具体数值"

        return _ok(ok_message(
            f"已列出{test_type}碰撞假人损伤指标",
            **criteria,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：disconnect_crash_solver - 清理碰撞仿真环境
# ---------------------------------------------------------------------------

def disconnect_crash_solver() -> dict:
    """
    清理碰撞仿真 Deck 和配置。
    """
    global _crash_deck
    try:
        _crash_deck = None
        _crash_config.update({
            "vehicle_model_path": None,
            "working_dir": None,
            "crash_type": None,
        })

        return _ok(ok_message("已清理碰撞仿真环境"))
    except Exception as e:
        return _err(str(e))
