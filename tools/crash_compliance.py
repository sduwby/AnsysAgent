"""
碰撞合规评估工具：
按照 Euro NCAP / FMVSS 208 / C-NCAP 法规限值对假人损伤指标进行
自动评估与评分，并生成综合碰撞报告。
"""

from __future__ import annotations

import json
import os
from datetime import datetime

from tools.utils import _ok, _err, ok_message, ensure_parent_dir
from tools.crash_deck import _crash_config
from tools.crash_postprocess import check_energy_balance


# ===========================================================================
# ===  合规评估工具（Regulatory Compliance）
# ===========================================================================

# ---------------------------------------------------------------------------
# 工具：evaluate_ncap_frontal - Euro NCAP/FMVSS 208 正面碰撞合规评估
# ---------------------------------------------------------------------------

def evaluate_ncap_frontal(
    hic36: float | None = None,
    chest_3ms_clip_g: float | None = None,
    chest_deflection_mm: float | None = None,
    femur_force_kN: float | None = None,
    neck_tension_N: float | None = None,
    neck_compression_N: float | None = None,
    standard: str = "euro_ncap",
    output_path: str = "",
) -> dict:
    """
    根据 Euro NCAP / FMVSS 208 限值对正面碰撞假人损伤指标进行合规评估与评分。

    Args:
        hic36: 头部损伤准则 HIC36（无量纲）
        chest_3ms_clip_g: 胸部 3ms 截止加速度（g）
        chest_deflection_mm: 胸部最大压缩量（mm）
        femur_force_kN: 大腿轴向最大力（kN）
        neck_tension_N: 颈部最大张力（N）
        neck_compression_N: 颈部最大压力（N）
        standard: 评估标准，"euro_ncap"（Euro NCAP 2024）、"fmvss208"（FMVSS 208）、"cncap"（C-NCAP 2024）
        output_path: 导出 JSON 路径（可选）
    """
    try:
        limits = {
            "euro_ncap": {
                "hic36": {"limit": 700, "warning": 500},
                "chest_3ms_g": {"limit": 60, "warning": 50},
                "chest_deflection_mm": {"limit": 42, "warning": 35},
                "femur_force_kN": {"limit": 10.0, "warning": 8.0},
                "neck_tension_N": {"limit": 3300, "warning": 2700},
                "neck_compression_N": {"limit": 3800, "warning": 3100},
            },
            "fmvss208": {
                "hic36": {"limit": 700, "warning": 600},
                "chest_3ms_g": {"limit": 60, "warning": 55},
                "chest_deflection_mm": {"limit": 76.2, "warning": 60},
                "femur_force_kN": {"limit": 10.0, "warning": 9.0},
                "neck_tension_N": {"limit": 4500, "warning": 3500},
                "neck_compression_N": {"limit": 4000, "warning": 3200},
            },
            "cncap": {
                "hic36": {"limit": 700, "warning": 500},
                "chest_3ms_g": {"limit": 60, "warning": 50},
                "chest_deflection_mm": {"limit": 42, "warning": 35},
                "femur_force_kN": {"limit": 10.0, "warning": 8.0},
                "neck_tension_N": {"limit": 3300, "warning": 2700},
                "neck_compression_N": {"limit": 3800, "warning": 3100},
            },
        }

        lmt = limits.get(standard, limits["euro_ncap"])

        def _eval(name: str, value: float | None) -> dict:
            if value is None:
                return {"value": None, "status": "not_measured"}
            lim = lmt.get(name, {})
            hard = lim.get("limit", float("inf"))
            warn = lim.get("warning", float("inf"))
            if value > hard:
                status = "fail"
            elif value > warn:
                status = "warning"
            else:
                status = "pass"
            margin = round(hard - value, 3)
            return {
                "value": round(value, 3),
                "limit": hard,
                "warning_threshold": warn,
                "status": status,
                "margin": margin,
                "margin_pct": round(margin / hard * 100, 1) if hard != float("inf") else None,
            }

        evaluations = {
            "hic36": _eval("hic36", hic36),
            "chest_3ms_clip_g": _eval("chest_3ms_g", chest_3ms_clip_g),
            "chest_deflection_mm": _eval("chest_deflection_mm", chest_deflection_mm),
            "femur_force_kN": _eval("femur_force_kN", femur_force_kN),
            "neck_tension_N": _eval("neck_tension_N", neck_tension_N),
            "neck_compression_N": _eval("neck_compression_N", neck_compression_N),
        }

        measured = {k: v for k, v in evaluations.items() if v["status"] != "not_measured"}
        fail_items = [k for k, v in measured.items() if v["status"] == "fail"]
        warn_items = [k for k, v in measured.items() if v["status"] == "warning"]
        pass_items = [k for k, v in measured.items() if v["status"] == "pass"]

        overall = "fail" if fail_items else ("warning" if warn_items else "pass")
        overall_emoji = {"pass": "✅", "warning": "⚠️", "fail": "❌"}[overall]

        result = {
            "standard": standard,
            "overall": overall,
            "evaluations": evaluations,
            "fail_items": fail_items,
            "warning_items": warn_items,
            "pass_items": pass_items,
            "measured_count": len(measured),
        }

        if output_path:
            ensure_parent_dir(output_path)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            result["exported_to"] = output_path

        summary_parts = []
        if fail_items:
            summary_parts.append(f"超标: {', '.join(fail_items)}")
        if warn_items:
            summary_parts.append(f"警告: {', '.join(warn_items)}")
        summary = "；".join(summary_parts) if summary_parts else "全部通过"

        return _ok(ok_message(
            f"{standard.upper()} 正面碰撞评估 {overall_emoji}：{summary}",
            **result,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：generate_crash_report - 生成碰撞仿真综合报告
# ---------------------------------------------------------------------------

def generate_crash_report(
    report_path: str,
    crash_type: str = "frontal",
    simulation_info: dict | None = None,
    energy_balance: dict | None = None,
    intrusion_results: dict | None = None,
    dummy_results: dict | None = None,
    compliance_results: dict | None = None,
    glstat_path: str = "",
    nodout_path: str = "",
) -> dict:
    """
    汇总碰撞仿真所有结果，生成结构化 JSON 综合报告。

    可直接传入已计算的结果字典，也可指定文件路径自动解析。

    Args:
        report_path: 报告输出路径（.json）
        crash_type: 碰撞类型描述
        simulation_info: 仿真基本信息（模型、工况、求解时间等）
        energy_balance: 能量守恒检验结果（来自 check_energy_balance）
        intrusion_results: 结构侵入量结果列表（来自 get_intrusion_at_node）
        dummy_results: 假人损伤指标原始值（HIC/胸部/大腿/颈部等）
        compliance_results: 合规评估结果（来自 evaluate_ncap_frontal）
        glstat_path: GLSTAT 文件路径（若 energy_balance 为 None 时自动解析）
        nodout_path: NODOUT 文件路径（备用参考）
    """
    try:
        if energy_balance is None and glstat_path and os.path.exists(glstat_path):
            eb = check_energy_balance(glstat_path=glstat_path)
            if eb["success"]:
                energy_balance = eb["result"]

        report = {
            "report_type": "crash_simulation",
            "crash_type": crash_type,
            "generated_at": datetime.now().isoformat(),
            "crash_config": dict(_crash_config),
            "simulation_info": simulation_info or {},
            "sections": {},
        }

        if energy_balance:
            report["sections"]["energy_balance"] = {
                "title": "能量守恒检验",
                "passed": energy_balance.get("passed", False),
                "hourglass_ratio": energy_balance.get("hourglass_ratio"),
                "energy_error": energy_balance.get("energy_error"),
                "warnings": energy_balance.get("warnings", []),
            }

        if intrusion_results:
            report["sections"]["structural_intrusion"] = {
                "title": "结构侵入量",
                "results": intrusion_results if isinstance(intrusion_results, list) else [intrusion_results],
            }

        if dummy_results:
            report["sections"]["dummy_injury"] = {
                "title": "假人损伤指标",
                "raw_values": dummy_results,
            }

        if compliance_results:
            report["sections"]["compliance"] = {
                "title": "法规合规评估",
                "standard": compliance_results.get("standard", "unknown"),
                "overall": compliance_results.get("overall", "unknown"),
                "fail_items": compliance_results.get("fail_items", []),
                "warning_items": compliance_results.get("warning_items", []),
                "evaluations": compliance_results.get("evaluations", {}),
            }

        report["summary"] = {
            "total_sections": len(report["sections"]),
            "overall_pass": all(
                s.get("passed", True) if "passed" in s else
                (s.get("overall", "pass") not in ("fail",))
                for s in report["sections"].values()
            ),
        }

        ensure_parent_dir(report_path)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        file_size = os.path.getsize(report_path)
        overall_pass = report["summary"]["overall_pass"]
        status = "✅ 通过" if overall_pass else "⚠️ 需关注"

        return _ok(ok_message(
            f"碰撞报告已生成 {status}：{report_path}（{file_size} bytes，{len(report['sections'])} 个章节）",
            report_path=report_path,
            file_size_bytes=file_size,
            sections=list(report["sections"].keys()),
            overall_pass=overall_pass,
            generated_at=report["generated_at"],
        ))
    except Exception as e:
        return _err(str(e))
