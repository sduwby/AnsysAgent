"""
碰撞仿真后处理结果解析工具：
解析 LS-DYNA ASCII 输出文件（GLSTAT/NODOUT/RCFORC/BNDOUT），
计算假人损伤指标（HIC/3ms/Nij）及能量守恒检验。
"""

from __future__ import annotations

import json
import os

from tools.utils import _ok, _err, ok_message, ensure_parent_dir


# ===========================================================================
# ===  后处理结果解析工具（Post-Processing）
# ===========================================================================

# ---------------------------------------------------------------------------
# 工具：parse_glstat - 解析 GLSTAT 能量历程文件
# ---------------------------------------------------------------------------

def parse_glstat(
    glstat_path: str,
    output_path: str = "",
) -> dict:
    """
    解析 LS-DYNA ASCII GLSTAT 文件，提取全局能量历程（动能/内能/沙漏能/总能量）。

    Args:
        glstat_path: GLSTAT 文件路径
        output_path: 导出 JSON 路径（可选）
    """
    try:
        if not os.path.exists(glstat_path):
            return _err(f"GLSTAT 文件不存在: {glstat_path}")

        time_list: list[float] = []
        ke_list: list[float] = []
        ie_list: list[float] = []
        he_list: list[float] = []
        te_list: list[float] = []

        with open(glstat_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("$"):
                    continue
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        t = float(parts[0])
                        ie = float(parts[1])
                        ke = float(parts[2])
                        he = float(parts[3])
                        te = float(parts[4])
                        time_list.append(t)
                        ie_list.append(ie)
                        ke_list.append(ke)
                        he_list.append(he)
                        te_list.append(te)
                    except ValueError:
                        continue

        if not time_list:
            return _err("GLSTAT 文件中未解析到有效数据，请确认文件格式。")

        result = {
            "file": glstat_path,
            "time_s": time_list,
            "internal_energy": ie_list,
            "kinetic_energy": ke_list,
            "hourglass_energy": he_list,
            "total_energy": te_list,
            "time_steps": len(time_list),
            "end_time_s": time_list[-1],
        }

        if output_path:
            ensure_parent_dir(output_path)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            result["exported_to"] = output_path

        return _ok(ok_message(
            f"已解析 GLSTAT 文件，共 {len(time_list)} 个时间步",
            **{k: v for k, v in result.items() if k not in ("time_s", "internal_energy", "kinetic_energy", "hourglass_energy", "total_energy")},
            energy_summary={
                "max_kinetic_energy": max(ke_list) if ke_list else 0,
                "max_internal_energy": max(ie_list) if ie_list else 0,
                "max_hourglass_energy": max(he_list) if he_list else 0,
                "final_total_energy": te_list[-1] if te_list else 0,
            },
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：parse_nodout - 解析 NODOUT 节点输出文件
# ---------------------------------------------------------------------------

def parse_nodout(
    nodout_path: str,
    node_ids: list[int] | None = None,
    channels: list[str] | None = None,
    output_path: str = "",
) -> dict:
    """
    解析 LS-DYNA ASCII NODOUT 文件，提取指定节点的加速度/速度/位移时间历程。

    Args:
        nodout_path: NODOUT 文件路径
        node_ids: 需要提取的节点 ID 列表，None 表示提取全部
        channels: 需要提取的通道列表，如 ["ax","ay","az","vx","vy","vz","dx","dy","dz"]，None 表示全部
        output_path: 导出 JSON 路径（可选）
    """
    try:
        if not os.path.exists(nodout_path):
            return _err(f"NODOUT 文件不存在: {nodout_path}")

        _default_channels = ["ax", "ay", "az", "vx", "vy", "vz", "dx", "dy", "dz"]
        channels = channels or _default_channels

        data: dict[int, dict[str, list]] = {}
        time_list: list[float] = []
        current_time: float | None = None
        header_done = False

        with open(nodout_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("n o d a l") or "nodal" in line.lower():
                i += 1
                continue
            if line.startswith("t i m e") or line.lower().startswith("time"):
                parts = line.split()
                for p in parts:
                    try:
                        current_time = float(p)
                        if not time_list or abs(current_time - time_list[-1]) > 1e-15:
                            time_list.append(current_time)
                        header_done = True
                        break
                    except ValueError:
                        continue
                i += 1
                continue
            if header_done and line and not line.startswith("#") and not line.startswith("$"):
                parts = line.split()
                if len(parts) >= 7:
                    try:
                        nid = int(parts[0])
                        if node_ids is None or nid in node_ids:
                            if nid not in data:
                                data[nid] = {ch: [] for ch in _default_channels}
                            vals = [float(p) for p in parts[1:10] if p]
                            channel_keys = _default_channels[:len(vals)]
                            for ch, v in zip(channel_keys, vals):
                                data[nid][ch].append(v)
                    except (ValueError, IndexError):
                        pass
            i += 1

        if not data:
            return _err("NODOUT 文件中未解析到有效节点数据。")

        filtered = {
            nid: {ch: vals for ch, vals in node_data.items() if ch in channels}
            for nid, node_data in data.items()
        }

        result = {
            "file": nodout_path,
            "time_s": time_list,
            "nodes": {str(nid): ch_data for nid, ch_data in filtered.items()},
            "node_count": len(filtered),
            "time_steps": len(time_list),
        }

        if output_path:
            ensure_parent_dir(output_path)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            result["exported_to"] = output_path

        return _ok(ok_message(
            f"已解析 NODOUT 文件，共 {len(filtered)} 个节点，{len(time_list)} 个时间步",
            node_count=len(filtered),
            time_steps=len(time_list),
            node_ids=list(filtered.keys()),
            exported_to=result.get("exported_to"),
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：parse_rcforc - 解析 RCFORC 接触力文件
# ---------------------------------------------------------------------------

def parse_rcforc(
    rcforc_path: str,
    interface_ids: list[int] | None = None,
    output_path: str = "",
) -> dict:
    """
    解析 LS-DYNA ASCII RCFORC 文件，提取接触面反力时间历程（壁障反力）。

    Args:
        rcforc_path: RCFORC 文件路径
        interface_ids: 需要提取的接触面 ID 列表，None 表示全部
        output_path: 导出 JSON 路径（可选）
    """
    try:
        if not os.path.exists(rcforc_path):
            return _err(f"RCFORC 文件不存在: {rcforc_path}")

        interfaces: dict[int, dict] = {}
        time_list: list[float] = []

        with open(rcforc_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("$"):
                    continue
                parts = line.split()
                if len(parts) >= 8:
                    try:
                        t = float(parts[0])
                        iid = int(parts[1])
                        fx = float(parts[2])
                        fy = float(parts[3])
                        fz = float(parts[4])
                        mx = float(parts[5])
                        my = float(parts[6])
                        mz = float(parts[7])

                        if interface_ids is None or iid in interface_ids:
                            if not time_list or abs(t - time_list[-1]) > 1e-15:
                                time_list.append(t)
                            if iid not in interfaces:
                                interfaces[iid] = {"fx": [], "fy": [], "fz": [], "mx": [], "my": [], "mz": [], "resultant": []}
                            interfaces[iid]["fx"].append(fx)
                            interfaces[iid]["fy"].append(fy)
                            interfaces[iid]["fz"].append(fz)
                            interfaces[iid]["mx"].append(mx)
                            interfaces[iid]["my"].append(my)
                            interfaces[iid]["mz"].append(mz)
                            interfaces[iid]["resultant"].append((fx**2 + fy**2 + fz**2) ** 0.5)
                    except (ValueError, IndexError):
                        continue

        if not interfaces:
            return _err("RCFORC 文件中未解析到有效接触力数据。")

        peak_forces = {
            str(iid): {
                "peak_resultant_N": max(d["resultant"]) if d["resultant"] else 0,
                "peak_fx_N": max(d["fx"], key=abs) if d["fx"] else 0,
                "peak_fy_N": max(d["fy"], key=abs) if d["fy"] else 0,
                "peak_fz_N": max(d["fz"], key=abs) if d["fz"] else 0,
            }
            for iid, d in interfaces.items()
        }

        result = {
            "file": rcforc_path,
            "time_s": time_list,
            "interfaces": {str(k): v for k, v in interfaces.items()},
            "peak_forces": peak_forces,
            "interface_count": len(interfaces),
        }

        if output_path:
            ensure_parent_dir(output_path)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            result["exported_to"] = output_path

        return _ok(ok_message(
            f"已解析 RCFORC 文件，共 {len(interfaces)} 个接触面",
            interface_count=len(interfaces),
            peak_forces=peak_forces,
            exported_to=result.get("exported_to"),
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：parse_bndout - 解析 BNDOUT 边界约束力文件
# ---------------------------------------------------------------------------

def parse_bndout(
    bndout_path: str,
    output_path: str = "",
) -> dict:
    """
    解析 LS-DYNA ASCII BNDOUT 文件，提取边界约束反力时间历程。

    Args:
        bndout_path: BNDOUT 文件路径
        output_path: 导出 JSON 路径（可选）
    """
    try:
        if not os.path.exists(bndout_path):
            return _err(f"BNDOUT 文件不存在: {bndout_path}")

        time_list: list[float] = []
        fx_list: list[float] = []
        fy_list: list[float] = []
        fz_list: list[float] = []

        with open(bndout_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("$"):
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        t = float(parts[0])
                        fx = float(parts[1])
                        fy = float(parts[2])
                        fz = float(parts[3])
                        time_list.append(t)
                        fx_list.append(fx)
                        fy_list.append(fy)
                        fz_list.append(fz)
                    except ValueError:
                        continue

        if not time_list:
            return _err("BNDOUT 文件中未解析到有效数据。")

        result = {
            "file": bndout_path,
            "time_s": time_list,
            "fx_N": fx_list,
            "fy_N": fy_list,
            "fz_N": fz_list,
            "time_steps": len(time_list),
            "peak_fx_N": max(fx_list, key=abs) if fx_list else 0,
            "peak_fy_N": max(fy_list, key=abs) if fy_list else 0,
            "peak_fz_N": max(fz_list, key=abs) if fz_list else 0,
        }

        if output_path:
            ensure_parent_dir(output_path)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            result["exported_to"] = output_path

        return _ok(ok_message(
            f"已解析 BNDOUT 文件，共 {len(time_list)} 个时间步",
            time_steps=len(time_list),
            peak_fx_N=result["peak_fx_N"],
            peak_fy_N=result["peak_fy_N"],
            peak_fz_N=result["peak_fz_N"],
            exported_to=result.get("exported_to"),
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：compute_hic - 计算头部损伤准则 HIC15/HIC36
# ---------------------------------------------------------------------------

def compute_hic(
    time_s: list[float],
    acceleration_g: list[float],
    window_ms: float = 36.0,
    output_path: str = "",
) -> dict:
    """
    从头部加速度时间历程计算头部损伤准则 HIC（Head Injury Criterion）。

    HIC = max_{t1,t2} [ (t2-t1) * (1/(t2-t1) * integral(a dt, t1, t2))^2.5 ]
    限值：HIC15 ≤ 700（15ms窗口），HIC36 ≤ 700（36ms窗口，FMVSS 208）

    Args:
        time_s: 时间序列（单位：s）
        acceleration_g: 合成加速度时间历程（单位：g，重力加速度倍数）
        window_ms: 积分时间窗口（ms），15 或 36
        output_path: 导出 JSON 路径（可选）
    """
    try:
        if len(time_s) != len(acceleration_g):
            return _err("time_s 与 acceleration_g 长度不一致。")
        if len(time_s) < 2:
            return _err("时间序列至少需要 2 个数据点。")

        window_s = window_ms / 1000.0
        n = len(time_s)
        hic_max = 0.0
        t1_opt = time_s[0]
        t2_opt = time_s[0]

        for i in range(n):
            integral = 0.0
            for j in range(i + 1, n):
                dt = time_s[j] - time_s[j - 1]
                integral += 0.5 * (acceleration_g[j] + acceleration_g[j - 1]) * dt
                dt_total = time_s[j] - time_s[i]
                if dt_total <= 0:
                    continue
                if dt_total > window_s:
                    break
                avg_a = integral / dt_total
                if avg_a < 0:
                    continue
                hic = dt_total * (avg_a ** 2.5)
                if hic > hic_max:
                    hic_max = hic
                    t1_opt = time_s[i]
                    t2_opt = time_s[j]

        limit = 700.0
        passed = hic_max <= limit

        result = {
            "HIC": round(hic_max, 2),
            "window_ms": window_ms,
            "t1_s": round(t1_opt, 6),
            "t2_s": round(t2_opt, 6),
            "limit": limit,
            "passed": passed,
            "margin": round(limit - hic_max, 2),
        }

        if output_path:
            ensure_parent_dir(output_path)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            result["exported_to"] = output_path

        status = "✅ 通过" if passed else "❌ 超标"
        return _ok(ok_message(
            f"HIC{int(window_ms)} = {hic_max:.1f}（限值 {limit}）{status}",
            **result,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：compute_chest_3ms - 计算胸部 3ms 截止加速度
# ---------------------------------------------------------------------------

def compute_chest_3ms(
    time_s: list[float],
    acceleration_g: list[float],
    output_path: str = "",
) -> dict:
    """
    计算胸部 3ms 截止加速度（Chest 3ms Clip Criterion）。

    3ms Clip = 加速度时间历程中持续超过某阈值达到 3ms 的最大加速度值。
    FMVSS 208 正面碰撞限值：胸部 3ms clip ≤ 60 g。

    Args:
        time_s: 时间序列（单位：s）
        acceleration_g: 胸部合成加速度时间历程（单位：g）
        output_path: 导出 JSON 路径（可选）
    """
    try:
        if len(time_s) != len(acceleration_g):
            return _err("time_s 与 acceleration_g 长度不一致。")

        window_s = 0.003
        n = len(time_s)
        clip_max = 0.0

        unique_levels = sorted(set(round(a, 1) for a in acceleration_g), reverse=True)
        for level in unique_levels:
            duration = 0.0
            for i in range(1, n):
                if acceleration_g[i] >= level and acceleration_g[i - 1] >= level:
                    duration += time_s[i] - time_s[i - 1]
                    if duration >= window_s:
                        clip_max = level
                        break
                else:
                    duration = 0.0
            if clip_max > 0:
                break

        limit = 60.0
        passed = clip_max <= limit

        result = {
            "chest_3ms_clip_g": round(clip_max, 2),
            "limit_g": limit,
            "passed": passed,
            "margin_g": round(limit - clip_max, 2),
        }

        if output_path:
            ensure_parent_dir(output_path)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            result["exported_to"] = output_path

        status = "✅ 通过" if passed else "❌ 超标"
        return _ok(ok_message(
            f"胸部 3ms clip = {clip_max:.1f} g（限值 {limit} g）{status}",
            **result,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：compute_nij - 计算颈部损伤准则 Nij（鞭打/后碰）
# ---------------------------------------------------------------------------

def compute_nij(
    fz_N: list[float],
    my_Nm: list[float],
    dummy_size: str = "50th",
    output_path: str = "",
) -> dict:
    """
    计算颈部损伤准则 Nij（Neck Injury Criterion），主要用于后碰鞭打评估。

    Nij = Fz/Fzc + My/Myc，各象限插值计算，限值 Nij ≤ 1.0（FMVSS 202a）。

    Args:
        fz_N: 颈部轴向力时间历程（N），拉伸为正
        my_Nm: 颈部弯矩时间历程（Nm），前屈为正
        dummy_size: 假人尺寸，"50th"（50th percentile male）、"5th"（5th female）
        output_path: 导出 JSON 路径（可选）
    """
    try:
        if len(fz_N) != len(my_Nm):
            return _err("fz_N 与 my_Nm 长度不一致。")

        intercepts = {
            "50th": {"Fzt": 6806.0, "Fzc": 6160.0, "Mye": 310.0, "Myf": 135.0},
            "5th":  {"Fzt": 4287.0, "Fzc": 3880.0, "Mye": 155.0, "Myf": 67.0},
        }
        ic = intercepts.get(dummy_size, intercepts["50th"])

        nij_list = []
        for fz, my in zip(fz_N, my_Nm):
            fzc = ic["Fzt"] if fz >= 0 else ic["Fzc"]
            myc = ic["Mye"] if my >= 0 else ic["Myf"]
            nij = abs(fz) / fzc + abs(my) / myc
            nij_list.append(nij)

        nij_max = max(nij_list) if nij_list else 0.0
        nij_max_idx = nij_list.index(nij_max) if nij_list else 0
        limit = 1.0
        passed = nij_max <= limit

        result = {
            "Nij_max": round(nij_max, 4),
            "Nij_max_index": nij_max_idx,
            "dummy_size": dummy_size,
            "limit": limit,
            "passed": passed,
            "intercepts": ic,
        }

        if output_path:
            ensure_parent_dir(output_path)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            result["exported_to"] = output_path

        status = "✅ 通过" if passed else "❌ 超标"
        return _ok(ok_message(
            f"Nij_max = {nij_max:.4f}（限值 {limit}）{status}",
            **result,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：check_energy_balance - 检验能量守恒
# ---------------------------------------------------------------------------

def check_energy_balance(
    glstat_path: str = "",
    internal_energy: list[float] | None = None,
    kinetic_energy: list[float] | None = None,
    hourglass_energy: list[float] | None = None,
    total_energy: list[float] | None = None,
    hourglass_ratio_limit: float = 0.05,
) -> dict:
    """
    检验 LS-DYNA 碰撞仿真能量守恒，评估沙漏能/总能量比例是否满足要求。

    工程判据：沙漏能 / 内能 ≤ 5%（LSTC 推荐）；总能量应相对守恒（误差 < 5%）。

    Args:
        glstat_path: GLSTAT 文件路径（与直接传入列表二选一）
        internal_energy: 内能时间历程（从 parse_glstat 获取）
        kinetic_energy: 动能时间历程
        hourglass_energy: 沙漏能时间历程
        total_energy: 总能量时间历程
        hourglass_ratio_limit: 沙漏能/内能允许最大比例，默认 0.05（5%）
    """
    try:
        if glstat_path and os.path.exists(glstat_path):
            parsed = parse_glstat(glstat_path)
            if not parsed["success"]:
                return parsed
            r = parsed["result"]
            internal_energy = r.get("internal_energy", [])
            kinetic_energy = r.get("kinetic_energy", [])
            hourglass_energy = r.get("hourglass_energy", [])
            total_energy = r.get("total_energy", [])

        if not internal_energy:
            return _err("未提供能量数据，请指定 glstat_path 或直接传入能量列表。")

        ie_max = max(internal_energy) if internal_energy else 0.0
        ke_max = max(kinetic_energy) if kinetic_energy else 0.0
        he_max = max(hourglass_energy) if hourglass_energy else 0.0
        te_init = total_energy[0] if total_energy else 0.0
        te_final = total_energy[-1] if total_energy else 0.0

        hg_ratio = he_max / ie_max if ie_max > 0 else 0.0
        energy_error = abs(te_final - te_init) / abs(te_init) if abs(te_init) > 1e-10 else 0.0

        hg_ok = hg_ratio <= hourglass_ratio_limit
        energy_ok = energy_error <= 0.05
        overall_pass = hg_ok and energy_ok

        warnings = []
        if not hg_ok:
            warnings.append(f"沙漏能/内能 = {hg_ratio:.1%}，超过限值 {hourglass_ratio_limit:.0%}，建议检查单元公式或增加沙漏控制")
        if not energy_ok:
            warnings.append(f"总能量误差 = {energy_error:.1%}，超过 5%，建议检查接触穿透或时间步长")

        result = {
            "passed": overall_pass,
            "hourglass_ratio": round(hg_ratio, 4),
            "hourglass_ratio_limit": hourglass_ratio_limit,
            "hourglass_ok": hg_ok,
            "energy_error": round(energy_error, 4),
            "energy_error_ok": energy_ok,
            "max_internal_energy": round(ie_max, 2),
            "max_kinetic_energy": round(ke_max, 2),
            "max_hourglass_energy": round(he_max, 2),
            "initial_total_energy": round(te_init, 2),
            "final_total_energy": round(te_final, 2),
            "warnings": warnings,
        }

        status = "✅ 通过" if overall_pass else "⚠️ 需关注"
        return _ok(ok_message(
            f"能量守恒检验{status}：沙漏比={hg_ratio:.1%}，能量误差={energy_error:.1%}",
            **result,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_intrusion_at_node - 从 NODOUT 提取特定节点位移（结构侵入量）
# ---------------------------------------------------------------------------

def get_intrusion_at_node(
    nodout_path: str,
    node_id: int,
    direction: str = "x",
    reference_node_id: int | None = None,
    output_path: str = "",
) -> dict:
    """
    从 NODOUT 文件提取指定节点的位移作为结构侵入量。

    正面碰撞通常取 X 方向位移，侧面取 Y 方向位移。
    如果指定参考节点，则计算相对位移（侵入量 = 变形节点位移 - 参考节点位移）。

    Args:
        nodout_path: NODOUT 文件路径
        node_id: 目标节点 ID（如前围板上的关键节点）
        direction: 位移方向，"x"、"y"、"z"
        reference_node_id: 参考节点 ID（如 B 柱下端），用于计算相对侵入量
        output_path: 导出 JSON 路径（可选）
    """
    try:
        ids_to_parse = [node_id]
        if reference_node_id is not None:
            ids_to_parse.append(reference_node_id)

        ch_map = {"x": "dx", "y": "dy", "z": "dz"}
        ch = ch_map.get(direction.lower(), "dx")

        parsed = parse_nodout(nodout_path, node_ids=ids_to_parse, channels=[ch])
        if not parsed["success"]:
            return parsed

        nodes_data = parsed["result"].get("nodes", {})
        time_s = parsed["result"].get("time_s", [])

        if str(node_id) not in nodes_data:
            return _err(f"节点 {node_id} 在 NODOUT 中未找到。")

        disp_target = nodes_data[str(node_id)].get(ch, [])

        if reference_node_id is not None and str(reference_node_id) in nodes_data:
            disp_ref = nodes_data[str(reference_node_id)].get(ch, [])
            n = min(len(disp_target), len(disp_ref))
            intrusion = [abs(disp_target[i] - disp_ref[i]) for i in range(n)]
        else:
            intrusion = [abs(d) for d in disp_target]

        max_intrusion = max(intrusion) if intrusion else 0.0
        max_idx = intrusion.index(max_intrusion) if intrusion else 0
        time_at_max = time_s[max_idx] if max_idx < len(time_s) else 0.0

        result = {
            "node_id": node_id,
            "reference_node_id": reference_node_id,
            "direction": direction,
            "max_intrusion_mm": round(max_intrusion, 3),
            "time_at_max_s": round(time_at_max, 6),
            "time_s": time_s,
            "intrusion_mm": [round(v, 3) for v in intrusion],
        }

        if output_path:
            ensure_parent_dir(output_path)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            result["exported_to"] = output_path

        return _ok(ok_message(
            f"节点 {node_id} 最大侵入量 = {max_intrusion:.1f} mm（{direction} 方向，t={time_at_max:.4f}s）",
            node_id=node_id,
            direction=direction,
            max_intrusion_mm=round(max_intrusion, 3),
            time_at_max_s=round(time_at_max, 6),
            exported_to=result.get("exported_to"),
        ))
    except Exception as e:
        return _err(str(e))
