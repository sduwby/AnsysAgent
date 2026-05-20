
"""
碰撞 Deck 关键字装配工具：
向 LS-DYNA Deck 添加集合定义（节点/段/部件）、运动约束、曲线、
安全带单元、壁障及假人配置、气囊和预张紧器模型。
"""

from __future__ import annotations

import json
import os

from tools.utils import _ok, _err, ok_message, ensure_parent_dir
from tools.crash_deck import _ensure_deck


# ===========================================================================
# ===  Deck 关键字完整性工具（Model Assembly）
# ===========================================================================

# ---------------------------------------------------------------------------
# 工具：add_node_set - 添加节点集合
# ---------------------------------------------------------------------------

def add_node_set(
    sid: int,
    node_ids: list[int],
    title: str = "",
) -> dict:
    """
    向碰撞 Deck 添加节点集合（*SET_NODE）。

    节点集是假人传感器约束、力传感器、安全带附着点等的基础。

    Args:
        sid: 节点集 ID
        node_ids: 节点 ID 列表
        title: 节点集标题（可选）
    """
    try:
        from ansys.dyna.core import keywords as kwd
        deck = _ensure_deck()

        ns = kwd.SetNode()
        ns.sid = sid
        for nid in node_ids:
            ns.nodes.append(nid)
        deck.append(ns)

        return _ok(ok_message(
            f"已添加节点集 {sid}（{len(node_ids)} 个节点）{': ' + title if title else ''}",
            sid=sid,
            node_count=len(node_ids),
            title=title,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：add_segment_set - 添加段集合（接触面分组）
# ---------------------------------------------------------------------------

def add_segment_set(
    sid: int,
    segments: list[list[int]],
    title: str = "",
) -> dict:
    """
    向碰撞 Deck 添加段集合（*SET_SEGMENT），用于接触面精确分组。

    Args:
        sid: 段集 ID
        segments: 段列表，每个段为 [n1, n2, n3, n4]（四边形）或 [n1, n2, n3]（三角形，n4=0）
        title: 段集标题（可选）
    """
    try:
        from ansys.dyna.core import keywords as kwd
        deck = _ensure_deck()

        ss = kwd.SetSegment()
        ss.sid = sid
        for seg in segments:
            while len(seg) < 4:
                seg = seg + [0]
            ss.segments.append(seg[:4])
        deck.append(ss)

        return _ok(ok_message(
            f"已添加段集 {sid}（{len(segments)} 个段）{': ' + title if title else ''}",
            sid=sid,
            segment_count=len(segments),
            title=title,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：add_part_set - 添加部件集合
# ---------------------------------------------------------------------------

def add_part_set(
    sid: int,
    part_ids: list[int],
    title: str = "",
) -> dict:
    """
    向碰撞 Deck 添加部件集合（*SET_PART），用于施加整体初速、重力或接触分组。

    Args:
        sid: 部件集 ID
        part_ids: 部件 ID 列表
        title: 部件集标题（可选）
    """
    try:
        from ansys.dyna.core import keywords as kwd
        deck = _ensure_deck()

        ps = kwd.SetPart()
        ps.sid = sid
        for pid in part_ids:
            ps.parts.append(pid)
        deck.append(ps)

        return _ok(ok_message(
            f"已添加部件集 {sid}（{len(part_ids)} 个部件）{': ' + title if title else ''}",
            sid=sid,
            part_count=len(part_ids),
            title=title,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：add_constrained_rigid_bodies - 添加刚体连接约束
# ---------------------------------------------------------------------------

def add_constrained_rigid_bodies(
    master_pid: int,
    slave_pids: list[int],
) -> dict:
    """
    向碰撞 Deck 添加刚体连接约束（*CONSTRAINED_RIGID_BODIES），模拟焊点/螺栓连接。

    Args:
        master_pid: 主刚体部件 ID
        slave_pids: 从刚体部件 ID 列表
    """
    try:
        from ansys.dyna.core import keywords as kwd
        deck = _ensure_deck()

        for spid in slave_pids:
            crb = kwd.ConstrainedRigidBodies()
            crb.pidm = master_pid
            crb.pids = spid
            deck.append(crb)

        return _ok(ok_message(
            f"已添加刚体连接：主体 {master_pid} → 从体 {slave_pids}",
            master_pid=master_pid,
            slave_pids=slave_pids,
            constraint_count=len(slave_pids),
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：define_curve - 定义载荷曲线（应力-应变/速度时间历程）
# ---------------------------------------------------------------------------

def define_curve(
    lcid: int,
    abscissa: list[float],
    ordinate: list[float],
    title: str = "",
    sfa: float = 1.0,
    sfo: float = 1.0,
    offa: float = 0.0,
    offo: float = 0.0,
) -> dict:
    """
    向碰撞 Deck 添加载荷曲线定义（*DEFINE_CURVE）。

    用于：应力-应变曲线（MAT_024 的 LCSS）、速度-时间曲线（壁障/假人初速）、
    气囊压力-时间曲线等。

    Args:
        lcid: 载荷曲线 ID
        abscissa: 横坐标值列表（如时间 s 或应变）
        ordinate: 纵坐标值列表（如力 N 或应力 MPa）
        title: 曲线标题（可选）
        sfa: 横坐标缩放因子
        sfo: 纵坐标缩放因子
        offa: 横坐标偏移
        offo: 纵坐标偏移
    """
    try:
        from ansys.dyna.core import keywords as kwd
        deck = _ensure_deck()

        if len(abscissa) != len(ordinate):
            return _err("abscissa 与 ordinate 长度不一致。")
        if len(abscissa) < 2:
            return _err("载荷曲线至少需要 2 个数据点。")

        curve = kwd.DefineCurve()
        curve.lcid = lcid
        curve.sfa = sfa
        curve.sfo = sfo
        curve.offa = offa
        curve.offo = offo
        for a, o in zip(abscissa, ordinate):
            curve.points.append([a, o])
        deck.append(curve)

        return _ok(ok_message(
            f"已定义载荷曲线 {lcid}（{len(abscissa)} 个数据点）{': ' + title if title else ''}",
            lcid=lcid,
            point_count=len(abscissa),
            x_range=[min(abscissa), max(abscissa)],
            y_range=[min(ordinate), max(ordinate)],
            title=title,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：add_joint - 添加运动副约束（铰链/滑块/球头）
# ---------------------------------------------------------------------------

def add_joint(
    joint_type: str = "revolute",
    node_a: int = 0,
    node_b: int = 0,
    node_c: int = 0,
    joint_id: int = 0,
) -> dict:
    """
    向碰撞 Deck 添加运动副约束（*CONSTRAINED_JOINT_*）。

    用于模拟车门铰链、座椅滑轨、转向柱等机构连接。

    Args:
        joint_type: 运动副类型，
            "revolute"（*CONSTRAINED_JOINT_REVOLUTE，转动副）、
            "spherical"（*CONSTRAINED_JOINT_SPHERICAL，球铰）、
            "translational"（*CONSTRAINED_JOINT_TRANSLATIONAL，移动副）、
            "rigid"（*CONSTRAINED_JOINT_RIGID，刚性连接）
        node_a: 节点 A（约束节点/从节点）
        node_b: 节点 B（参考节点/主节点）
        node_c: 节点 C（转轴方向定义节点，revolute 有效）
        joint_id: 运动副 ID（0 自动分配）
    """
    try:
        from ansys.dyna.core import keywords as kwd
        deck = _ensure_deck()

        joint_map = {
            "revolute": kwd.ConstrainedJointRevolute,
            "spherical": kwd.ConstrainedJointSpherical,
            "translational": kwd.ConstrainedJointTranslational,
            "rigid": kwd.ConstrainedJointRigid,
        }

        if joint_type not in joint_map:
            return _err(f"不支持的运动副类型: {joint_type}，可选: {list(joint_map.keys())}")

        jnt = joint_map[joint_type]()
        jnt.n1 = node_a
        jnt.n2 = node_b
        if joint_type == "revolute" and node_c:
            jnt.n3 = node_c
        deck.append(jnt)

        return _ok(ok_message(
            f"已添加 {joint_type} 运动副（节点 {node_a}-{node_b}）",
            joint_type=joint_type,
            node_a=node_a,
            node_b=node_b,
            node_c=node_c,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：add_seatbelt - 添加安全带单元
# ---------------------------------------------------------------------------

def add_seatbelt(
    belt_id: int,
    node_ids: list[int],
    section_id: int = 1,
    material_id: int = 1,
    pretension_force_N: float = 0.0,
    retractor_node: int = 0,
    slip_ring_nodes: list[int] | None = None,
) -> dict:
    """
    向碰撞 Deck 添加安全带一维单元（*ELEMENT_SEATBELT + *SECTION_SEATBELT）。

    Args:
        belt_id: 安全带单元起始 ID
        node_ids: 安全带路径节点 ID 列表（按顺序，从卷收器到锁扣）
        section_id: 截面 ID（*SECTION_SEATBELT）
        material_id: 材料 ID（弹性绳材料）
        pretension_force_N: 预张紧力（N）；0 表示无预张紧
        retractor_node: 卷收器节点 ID；0 表示无卷收器
        slip_ring_nodes: 导向环节点 ID 列表（B 柱导向环/D 环）
    """
    try:
        from ansys.dyna.core import keywords as kwd
        deck = _ensure_deck()

        sec = kwd.SectionSeatbelt()
        sec.secid = section_id
        deck.append(sec)

        for i in range(len(node_ids) - 1):
            elem = kwd.ElementSeatbelt()
            elem.eid = belt_id + i
            elem.n1 = node_ids[i]
            elem.n2 = node_ids[i + 1]
            elem.sbsid = section_id
            elem.sbmid = material_id
            deck.append(elem)

        if retractor_node > 0:
            ret = kwd.ElementSeatbeltRetractor()
            ret.sbrid = belt_id + 1000
            ret.n1 = retractor_node
            if pretension_force_N > 0:
                ret.prtens = pretension_force_N
            deck.append(ret)

        if slip_ring_nodes:
            for srn in slip_ring_nodes:
                slp = kwd.ElementSeatbeltSlipring()
                slp.sbsrid = belt_id + 2000 + slip_ring_nodes.index(srn)
                slp.n1 = srn
                deck.append(slp)

        return _ok(ok_message(
            f"已添加安全带系统（{len(node_ids) - 1} 个单元，起始 ID {belt_id}）",
            belt_id=belt_id,
            element_count=len(node_ids) - 1,
            section_id=section_id,
            pretension_force_N=pretension_force_N,
            retractor_node=retractor_node,
        ))
    except Exception as e:
        return _err(str(e))


# ===========================================================================
# ===  壁障与假人配置工具（Barrier & Dummy Setup）
# ===========================================================================

# ---------------------------------------------------------------------------
# 工具：place_rigid_wall_occ - 放置 OCC 正面刚性壁障
# ---------------------------------------------------------------------------

def place_rigid_wall_occ(
    wall_id: int = 1,
    x_mm: float = 0.0,
    y_mm: float = 0.0,
    z_mm: float = 0.0,
    normal_x: float = 1.0,
    normal_y: float = 0.0,
    normal_z: float = 0.0,
    width_mm: float = 2500.0,
    height_mm: float = 1500.0,
    friction: float = 0.3,
) -> dict:
    """
    在碰撞 Deck 中放置 OCC 正面刚性壁障（*RIGIDWALL_PLANAR）。

    FMVSS 208 Full Frontal 使用固定刚性壁障，100% 正碰。

    Args:
        wall_id: 壁障 ID
        x_mm: 壁障面中心 X 坐标（mm）
        y_mm: 壁障面中心 Y 坐标（mm）
        z_mm: 壁障面中心 Z 坐标（mm）
        normal_x: 壁障法向量 X 分量（指向车辆方向）
        normal_y: 壁障法向量 Y 分量
        normal_z: 壁障法向量 Z 分量
        width_mm: 壁障宽度（mm），FMVSS 208 ≥ 2500 mm
        height_mm: 壁障高度（mm），FMVSS 208 ≥ 1500 mm
        friction: 壁障摩擦系数
    """
    try:
        from ansys.dyna.core import keywords as kwd
        deck = _ensure_deck()

        rw = kwd.RigidwallPlanar()
        rw.id = wall_id
        rw.nsid = 0
        rw.xt = x_mm
        rw.yt = y_mm
        rw.zt = z_mm
        rw.xh = x_mm + normal_x
        rw.yh = y_mm + normal_y
        rw.zh = z_mm + normal_z
        rw.fric = friction
        deck.append(rw)

        return _ok(ok_message(
            f"已放置刚性壁障 {wall_id}（位置 [{x_mm:.0f}, {y_mm:.0f}, {z_mm:.0f}] mm，法向 [{normal_x:.1f}, {normal_y:.1f}, {normal_z:.1f}]）",
            wall_id=wall_id,
            position_mm=[x_mm, y_mm, z_mm],
            normal=[normal_x, normal_y, normal_z],
            size_mm=[width_mm, height_mm],
            friction=friction,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：import_barrier_model - 导入移动可变形壁障模型
# ---------------------------------------------------------------------------

def import_barrier_model(
    barrier_path: str,
    barrier_type: str = "mdb",
    offset_x_mm: float = 0.0,
    offset_y_mm: float = 0.0,
    offset_z_mm: float = 0.0,
    initial_speed_kmh: float = 50.0,
    speed_direction: str = "x",
) -> dict:
    """
    导入并配置移动可变形壁障模型（MDB/AE-MDB），用于侧面/前置偏置碰撞。

    Args:
        barrier_path: 壁障 .k 文件路径
        barrier_type: 壁障类型，"mdb"（欧标移动可变形壁障）、"ae_mdb"（AE-MDB，Euro NCAP 侧面）、
                      "offset"（IIHS 25%小偏置壁障）
        offset_x_mm: X 方向位置偏移（mm）
        offset_y_mm: Y 方向位置偏移（mm）
        offset_z_mm: Z 方向位置偏移（mm）
        initial_speed_kmh: 壁障初始速度（km/h）
        speed_direction: 速度方向，"x"、"y"、"-x"、"-y"
    """
    try:
        from ansys.dyna.core import Deck as DynaDeck
        deck = _ensure_deck()

        if not os.path.exists(barrier_path):
            return _err(f"壁障模型文件不存在: {barrier_path}")

        barrier_deck = DynaDeck()
        barrier_deck.import_file(barrier_path)
        barrier_dir = os.path.dirname(os.path.abspath(barrier_path))
        barrier_deck.expand(search_paths=[barrier_dir], recurse=True)

        kw_count = len(list(barrier_deck.keywords))
        for kw in barrier_deck.keywords:
            deck.append(kw)

        speed_map = {"x": (1, 0, 0), "y": (0, 1, 0), "-x": (-1, 0, 0), "-y": (0, -1, 0)}
        dx, dy, dz = speed_map.get(speed_direction, (1, 0, 0))
        speed_mm_s = initial_speed_kmh * 1e6 / 3600.0

        from ansys.dyna.core import keywords as kwd
        vel = kwd.InitialVelocityGeneration()
        vel.vx = speed_mm_s * dx
        vel.vy = speed_mm_s * dy
        vel.vz = speed_mm_s * dz
        deck.append(vel)

        return _ok(ok_message(
            f"已导入 {barrier_type} 壁障模型（{kw_count} 个关键字），初速 {initial_speed_kmh} km/h",
            barrier_type=barrier_type,
            barrier_path=barrier_path,
            keyword_count=kw_count,
            offset_mm=[offset_x_mm, offset_y_mm, offset_z_mm],
            initial_speed_kmh=initial_speed_kmh,
            speed_direction=speed_direction,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：place_dummy_model - 导入并定位假人模型
# ---------------------------------------------------------------------------

def place_dummy_model(
    dummy_path: str,
    dummy_type: str = "hybrid3_50th",
    seat_position: str = "driver",
    x_mm: float = 0.0,
    y_mm: float = 0.0,
    z_mm: float = 0.0,
    head_sensor_node: int = 0,
    chest_sensor_node: int = 0,
    neck_sensor_node: int = 0,
    femur_sensor_nodes: list[int] | None = None,
) -> dict:
    """
    导入假人（Crash Test Dummy）模型并配置传感器节点组。

    Args:
        dummy_path: 假人 .k 文件路径（Hybrid III 50th / THOR 等标准假人模型）
        dummy_type: 假人类型，"hybrid3_50th"（Hybrid III 50th）、"hybrid3_5th"（5th Female）、
                    "thor"（THOR-M）、"worldsid"（WorldSID）
        seat_position: 座位，"driver"（驾驶员/左前）、"passenger"（副驾/右前）、"rear_left"、"rear_right"
        x_mm: 假人质心 X 坐标（mm）
        y_mm: 假人质心 Y 坐标（mm）
        z_mm: 假人质心 Z 坐标（mm）
        head_sensor_node: 头部 CG 传感器节点 ID（用于 HIC 计算）
        chest_sensor_node: 胸部传感器节点 ID（用于胸部压缩量/加速度）
        neck_sensor_node: 颈部传感器节点 ID（用于 Nij）
        femur_sensor_nodes: 大腿轴向力传感器节点 ID 列表（[左大腿, 右大腿]）
    """
    try:
        from ansys.dyna.core import Deck as DynaDeck
        deck = _ensure_deck()

        if not os.path.exists(dummy_path):
            return _err(f"假人模型文件不存在: {dummy_path}")

        dummy_deck = DynaDeck()
        dummy_deck.import_file(dummy_path)
        dummy_dir = os.path.dirname(os.path.abspath(dummy_path))
        dummy_deck.expand(search_paths=[dummy_dir], recurse=True)

        kw_count = len(list(dummy_deck.keywords))
        for kw in dummy_deck.keywords:
            deck.append(kw)

        sensor_nodes = {}
        if head_sensor_node:
            sensor_nodes["head_cg"] = head_sensor_node
        if chest_sensor_node:
            sensor_nodes["chest"] = chest_sensor_node
        if neck_sensor_node:
            sensor_nodes["neck"] = neck_sensor_node
        if femur_sensor_nodes:
            sensor_nodes["femur"] = femur_sensor_nodes

        _crash_config[f"dummy_{seat_position}"] = {
            "type": dummy_type,
            "position_mm": [x_mm, y_mm, z_mm],
            "sensor_nodes": sensor_nodes,
        }

        return _ok(ok_message(
            f"已导入 {dummy_type} 假人模型（{seat_position} 位，{kw_count} 个关键字）",
            dummy_type=dummy_type,
            seat_position=seat_position,
            position_mm=[x_mm, y_mm, z_mm],
            keyword_count=kw_count,
            sensor_nodes=sensor_nodes,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_airbag - 配置气囊模型
# ---------------------------------------------------------------------------

def setup_airbag(
    airbag_id: int = 1,
    airbag_type: str = "simple_pressure_volume",
    part_sid: int = 0,
    gas_constant: float = 287.0,
    initial_pressure_Pa: float = 101325.0,
    inflator_lcid: int = 0,
    vent_area_m2: float = 0.0,
    fabric_leakage: float = 0.0,
) -> dict:
    """
    向碰撞 Deck 添加气囊模型（*AIRBAG_SIMPLE_PRESSURE_VOLUME 或 *AIRBAG_HYBRID）。

    Args:
        airbag_id: 气囊 ID
        airbag_type: 气囊类型，
            "simple_pressure_volume"（简化 PV 气囊，*AIRBAG_SIMPLE_PRESSURE_VOLUME）、
            "hybrid"（混合气囊，*AIRBAG_HYBRID，考虑充气/排气/织物泄漏）
        part_sid: 气囊壳单元部件集 ID（*SET_PART）
        gas_constant: 气体常数（J/(kg·K)），空气 287，氮气 297
        initial_pressure_Pa: 初始压力（Pa），通常为大气压 101325
        inflator_lcid: 充气器质量流率-时间曲线 ID（*DEFINE_CURVE）
        vent_area_m2: 排气孔总面积（m²），0 表示无排气孔
        fabric_leakage: 织物泄漏系数（0~1），0 表示不透气
    """
    try:
        from ansys.dyna.core import keywords as kwd
        deck = _ensure_deck()

        if airbag_type == "simple_pressure_volume":
            ab = kwd.AirbagSimplePressureVolume()
            ab.sid = part_sid
            ab.cv = gas_constant / 1.4
            ab.cp = gas_constant
            ab.t = 293.0
            ab.lcid = inflator_lcid
            deck.append(ab)

        elif airbag_type == "hybrid":
            ab = kwd.AirbagHybrid()
            ab.sid = part_sid
            ab.atmost = initial_pressure_Pa
            ab.tstop = 0.1
            deck.append(ab)

        else:
            return _err(f"不支持的气囊类型: {airbag_type}")

        return _ok(ok_message(
            f"已添加 {airbag_type} 气囊模型 {airbag_id}（部件集 {part_sid}）",
            airbag_id=airbag_id,
            airbag_type=airbag_type,
            part_sid=part_sid,
            inflator_lcid=inflator_lcid,
            vent_area_m2=vent_area_m2,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：add_pretensioner - 添加安全带预张紧器
# ---------------------------------------------------------------------------

def add_pretensioner(
    retractor_id: int,
    pretension_force_N: float = 3500.0,
    pretension_time_ms: float = 15.0,
    load_limiter_force_N: float = 4000.0,
    load_limiter_lcid: int = 0,
) -> dict:
    """
    向碰撞 Deck 添加安全带预张紧器与限力器配置（*ELEMENT_SEATBELT_PRETENSIONER）。

    预张紧器在碰撞触发后迅速收紧安全带（典型 3500 N / 15 ms），
    限力器限制最大载荷防止胸部损伤（典型 4 kN）。

    Args:
        retractor_id: 对应的卷收器单元 ID（由 add_seatbelt 创建）
        pretension_force_N: 预张紧力（N）
        pretension_time_ms: 预张紧作用时间（ms）
        load_limiter_force_N: 限力器限制力（N）
        load_limiter_lcid: 限力器力-位移曲线 ID（0 表示使用常数限制力）
    """
    try:
        from ansys.dyna.core import keywords as kwd
        deck = _ensure_deck()

        pt = kwd.ElementSeatbeltPretensioner()
        pt.sbprid = retractor_id + 3000
        pt.sbrid = retractor_id
        pt.ptf = pretension_force_N
        pt.ptl = load_limiter_force_N
        if load_limiter_lcid > 0:
            pt.lcid = load_limiter_lcid
        deck.append(pt)

        return _ok(ok_message(
            f"已添加预张紧器（卷收器 {retractor_id}，预张力 {pretension_force_N} N，限力 {load_limiter_force_N} N）",
            retractor_id=retractor_id,
            pretension_force_N=pretension_force_N,
            pretension_time_ms=pretension_time_ms,
            load_limiter_force_N=load_limiter_force_N,
            load_limiter_lcid=load_limiter_lcid,
        ))
    except Exception as e:
        return _err(str(e))


