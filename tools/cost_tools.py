"""
电机成本估算工具：根据材料用量、制造工艺和供应链参数，
估算电机制造成本（材料成本 + 加工成本 + 绝缘成本 + 磁钢成本等）。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations
import math
from tools.utils import _ok, _err, append_warnings, ok_message

# 默认材料单价（2024 年参考价格，人民币/kg）
DEFAULT_MATERIAL_PRICES: dict[str, dict] = {
    "silicon_steel": {
        "name": "硅钢片",
        "price_per_kg": 12.0,
        "density_kg_m3": 7650,
    },
    "copper_wire": {
        "name": "漆包铜线",
        "price_per_kg": 75.0,
        "density_kg_m3": 8900,
    },
    "ndfeb_magnet": {
        "name": "NdFeB 永磁体",
        "price_per_kg": 350.0,
        "density_kg_m3": 7500,
    },
    "ferrite_magnet": {
        "name": "铁氧体永磁",
        "price_per_kg": 30.0,
        "density_kg_m3": 5000,
    },
    "aluminum": {
        "name": "铝合金",
        "price_per_kg": 22.0,
        "density_kg_m3": 2700,
    },
    "shaft_steel": {
        "name": "转轴钢",
        "price_per_kg": 8.0,
        "density_kg_m3": 7850,
    },
    "insulation": {
        "name": "绝缘材料",
        "price_per_kg": 80.0,
        "density_kg_m3": 1400,
    },
    "housing_aluminum": {
        "name": "机壳铝合金",
        "price_per_kg": 25.0,
        "density_kg_m3": 2700,
    },
    "bearing_steel": {
        "name": "轴承钢",
        "price_per_kg": 20.0,
        "density_kg_m3": 7850,
    },
}


# ---------------------------------------------------------------------------
# 工具：estimate_motor_cost - 估算电机制造成本
# ---------------------------------------------------------------------------

def estimate_motor_cost(
    stator_outer_diam_mm: float = 150.0,
    stator_inner_diam_mm: float = 90.0,
    rotor_outer_diam_mm: float = 88.0,
    shaft_diam_mm: float = 30.0,
    stack_length_mm: float = 100.0,
    num_slots: int = 36,
    num_poles: int = 6,
    magnet_type: str = "ndfeb",
    winding_fill_factor: float = 0.45,
    insulation_class: str = "H",
    production_volume: int = 1000,
    material_prices: dict[str, float] | None = None,
    manufacturing_region: str = "china",
) -> dict:
    """根据电机几何参数和材料用量估算制造成本。

    成本组成：
    1. 铁芯成本（硅钢片用量 × 单价）
    2. 绕组成本（铜线用量 × 单价）
    3. 永磁体成本（磁钢用量 × 单价）
    4. 结构件成本（转轴、机壳、轴承等）
    5. 绝缘成本（绝缘等级相关）
    6. 制造加工费（冲片、绕线、嵌线、装配等）

    Args:
        stator_outer_diam_mm: 定子外径（mm）
        stator_inner_diam_mm: 定子内径（mm）
        rotor_outer_diam_mm: 转子外径（mm）
        shaft_diam_mm: 转轴直径（mm）
        stack_length_mm: 叠片长度（mm）
        num_slots: 槽数
        num_poles: 极数
        magnet_type: 磁钢类型，"ndfeb"（钕铁硼）/ "ferrite"（铁氧体）
        winding_fill_factor: 绕组槽满率（0~1）
        insulation_class: 绝缘等级，"B"/"F"/"H"
        production_volume: 预估生产批量（台），影响单台分摊的工装费用
        material_prices: 自定义材料单价覆盖（元/kg），如 {"copper_wire": 80}
        manufacturing_region: 制造区域，"china"/"eu"/"us"，影响加工费系数
    """
    try:
        warnings: list[str] = []

        # 参数校验
        if stator_inner_diam_mm >= stator_outer_diam_mm:
            return _err("定子内径必须小于外径")
        if rotor_outer_diam_mm >= stator_inner_diam_mm:
            return _err("转子外径必须小于定子内径")
        if shaft_diam_mm >= rotor_outer_diam_mm:
            return _err("轴径必须小于转子外径")

        # 合并自定义价格
        prices = {}
        for key, info in DEFAULT_MATERIAL_PRICES.items():
            prices[key] = info["price_per_kg"]
        if material_prices:
            for k, v in material_prices.items():
                if k in prices:
                    prices[k] = v
                else:
                    warnings.append(f"未知材料类型 '{k}'，已忽略")

        # 区域加工费系数
        mfg_coefficients = {"china": 1.0, "eu": 2.5, "us": 2.8}
        mfg_coeff = mfg_coefficients.get(manufacturing_region, 1.0)

        # 批量折扣系数（简单对数模型）
        if production_volume >= 10000:
            batch_discount = 0.7
        elif production_volume >= 1000:
            batch_discount = 0.85
        elif production_volume >= 100:
            batch_discount = 0.95
        else:
            batch_discount = 1.0

        # 绝缘等级系数
        insulation_coefficients = {"B": 1.0, "F": 1.3, "H": 1.6}
        insul_coeff = insulation_coefficients.get(insulation_class, 1.0)

        # --- 1. 铁芯成本 ---
        # 定子铁芯
        stator_yoke_thickness = (stator_outer_diam_mm - stator_inner_diam_mm) / 2  # 简化
        stator_area_mm2 = math.pi / 4 * (stator_outer_diam_mm**2 - stator_inner_diam_mm**2)
        stator_volume_mm3 = stator_area_mm2 * stack_length_mm
        stator_volume_m3 = stator_volume_mm3 * 1e-9
        stator_mass_kg = stator_volume_m3 * DEFAULT_MATERIAL_PRICES["silicon_steel"]["density_kg_m3"]
        stator_core_cost = stator_mass_kg * prices["silicon_steel"]

        # 转子铁芯
        rotor_area_mm2 = math.pi / 4 * (rotor_outer_diam_mm**2 - shaft_diam_mm**2)
        rotor_volume_mm3 = rotor_area_mm2 * stack_length_mm
        rotor_volume_m3 = rotor_volume_mm3 * 1e-9
        rotor_mass_kg = rotor_volume_m3 * DEFAULT_MATERIAL_PRICES["silicon_steel"]["density_kg_m3"]
        rotor_core_cost = rotor_mass_kg * prices["silicon_steel"]

        iron_cost = stator_core_cost + rotor_core_cost

        # --- 2. 绕组成本 ---
        # 估算槽面积（简化为定子内表面槽总面积）
        slot_area_total_mm2 = (math.pi * stator_inner_diam_mm * stack_length_mm * 0.15
                               * (stator_yoke_thickness / stator_inner_diam_mm * 2))
        slot_area_total_mm2 = max(slot_area_total_mm2, 500)  # 下限保护
        copper_volume_mm3 = slot_area_total_mm2 * winding_fill_factor * stack_length_mm
        copper_volume_m3 = copper_volume_mm3 * 1e-9
        copper_mass_kg = copper_volume_m3 * DEFAULT_MATERIAL_PRICES["copper_wire"]["density_kg_m3"]
        winding_cost = copper_mass_kg * prices["copper_wire"]

        # --- 3. 永磁体成本 ---
        # 估算磁钢体积（简化：转子表面积的 60% 为磁钢区域）
        magnet_coverage = 0.6
        magnet_thickness_mm = (rotor_outer_diam_mm - shaft_diam_mm) * 0.15  # 简化估计
        magnet_volume_mm3 = (math.pi * rotor_outer_diam_mm * stack_length_mm
                             * magnet_coverage * magnet_thickness_mm)
        magnet_volume_m3 = magnet_volume_mm3 * 1e-9
        magnet_key = "ndfeb_magnet" if magnet_type == "ndfeb" else "ferrite_magnet"
        magnet_mass_kg = magnet_volume_m3 * DEFAULT_MATERIAL_PRICES[magnet_key]["density_kg_m3"]
        magnet_cost = magnet_mass_kg * prices[magnet_key]

        # --- 4. 结构件成本 ---
        # 转轴
        shaft_volume_m3 = math.pi / 4 * (shaft_diam_mm * 1e-3)**2 * (stack_length_mm * 1e-3 + 0.1)
        shaft_mass_kg = shaft_volume_m3 * DEFAULT_MATERIAL_PRICES["shaft_steel"]["density_kg_m3"]
        shaft_cost = shaft_mass_kg * prices["shaft_steel"]

        # 机壳（简化：外径的圆柱壳）
        housing_thickness_mm = max(stator_outer_diam_mm * 0.05, 5)
        housing_outer_diam_mm = stator_outer_diam_mm + 2 * housing_thickness_mm
        housing_volume_m3 = (math.pi / 4 * ((housing_outer_diam_mm * 1e-3)**2 - (stator_outer_diam_mm * 1e-3)**2)
                             * (stack_length_mm * 1e-3 + 0.05))
        housing_mass_kg = housing_volume_m3 * DEFAULT_MATERIAL_PRICES["housing_aluminum"]["density_kg_m3"]
        housing_cost = housing_mass_kg * prices["housing_aluminum"]

        # 轴承（按直径粗估）
        bearing_cost_per_unit = max(15, stator_outer_diam_mm * 0.3)
        bearing_cost = bearing_cost_per_unit * 2  # 驱动端 + 非驱动端

        structure_cost = shaft_cost + housing_cost + bearing_cost

        # --- 5. 绝缘成本 ---
        insulation_mass_kg = copper_mass_kg * 0.1 * insul_coeff  # 绝缘约占铜重的 10%~16%
        insulation_cost = insulation_mass_kg * prices["insulation"]

        # --- 6. 制造加工费 ---
        # 冲片 + 绕线 + 嵌线 + 装配
        stamping_cost = (stator_mass_kg + rotor_mass_kg) * 3.0 * mfg_coeff  # 冲片费
        winding_labor = num_slots * 2.0 * mfg_coeff  # 绕线/嵌线（每槽）
        assembly_cost = max(50, stator_outer_diam_mm * 0.8) * mfg_coeff  # 装配
        testing_cost = 20 * mfg_coeff  # 出厂测试

        processing_cost = (stamping_cost + winding_labor + assembly_cost + testing_cost) * batch_discount

        # --- 汇总 ---
        material_total = iron_cost + winding_cost + magnet_cost + structure_cost + insulation_cost
        total_cost = material_total + processing_cost

        # 物料用量明细
        material_usage = {
            "stator_core_kg": round(stator_mass_kg, 3),
            "rotor_core_kg": round(rotor_mass_kg, 3),
            "copper_wire_kg": round(copper_mass_kg, 3),
            "magnet_kg": round(magnet_mass_kg, 3),
            "shaft_steel_kg": round(shaft_mass_kg, 3),
            "housing_aluminum_kg": round(housing_mass_kg, 3),
            "insulation_kg": round(insulation_mass_kg, 3),
        }

        result = {
            "total_cost_CNY": round(total_cost, 2),
            "material_cost_CNY": round(material_total, 2),
            "processing_cost_CNY": round(processing_cost, 2),
            "cost_breakdown": {
                "iron_core": round(iron_cost, 2),
                "winding_copper": round(winding_cost, 2),
                "magnet": round(magnet_cost, 2),
                "structure": round(structure_cost, 2),
                "insulation": round(insulation_cost, 2),
                "processing": round(processing_cost, 2),
            },
            "cost_percentage": {
                "material_pct": round(material_total / total_cost * 100, 1),
                "processing_pct": round(processing_cost / total_cost * 100, 1),
            },
            "material_usage_kg": material_usage,
            "assumptions": {
                "magnet_type": magnet_type,
                "insulation_class": insulation_class,
                "production_volume": production_volume,
                "batch_discount": batch_discount,
                "manufacturing_region": manufacturing_region,
                "mfg_cost_coefficient": mfg_coeff,
            },
        }
        return _ok(append_warnings(result, warnings))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_default_material_prices - 获取默认材料单价
# ---------------------------------------------------------------------------

def get_default_material_prices() -> dict:
    """返回当前默认的材料单价和密度信息。"""
    return _ok({
        key: {
            "name": info["name"],
            "price_per_kg_CNY": info["price_per_kg"],
            "density_kg_m3": info["density_kg_m3"],
        }
        for key, info in DEFAULT_MATERIAL_PRICES.items()
    })


# ---------------------------------------------------------------------------
# 工具：compare_magnet_cost - 对比不同磁钢方案成本
# ---------------------------------------------------------------------------

def compare_magnet_cost(
    stator_outer_diam_mm: float = 150.0,
    stator_inner_diam_mm: float = 90.0,
    rotor_outer_diam_mm: float = 88.0,
    shaft_diam_mm: float = 30.0,
    stack_length_mm: float = 100.0,
    production_volume: int = 1000,
) -> dict:
    """对比 NdFeB 和铁氧体两种磁钢方案的成本差异，辅助选型决策。

    Args:
        stator_outer_diam_mm: 定子外径（mm）
        stator_inner_diam_mm: 定子内径（mm）
        rotor_outer_diam_mm: 转子外径（mm）
        shaft_diam_mm: 转轴直径（mm）
        stack_length_mm: 叠片长度（mm）
        production_volume: 生产批量
    """
    try:
        results = {}
        for magnet_type in ["ndfeb", "ferrite"]:
            r = estimate_motor_cost(
                stator_outer_diam_mm=stator_outer_diam_mm,
                stator_inner_diam_mm=stator_inner_diam_mm,
                rotor_outer_diam_mm=rotor_outer_diam_mm,
                shaft_diam_mm=shaft_diam_mm,
                stack_length_mm=stack_length_mm,
                magnet_type=magnet_type,
                production_volume=production_volume,
            )
            results[magnet_type] = r.get("result", r) if r.get("success") else {"error": r.get("error")}

        ndfeb = results.get("ndfeb", {})
        ferrite = results.get("ferrite", {})
        ndfeb_cost = ndfeb.get("total_cost_CNY", 0)
        ferrite_cost = ferrite.get("total_cost_CNY", 0)

        return _ok({
            "ndfeb": ndfeb,
            "ferrite": ferrite,
            "comparison": {
                "ndfeb_total_CNY": ndfeb_cost,
                "ferrite_total_CNY": ferrite_cost,
                "cost_diff_CNY": round(ndfeb_cost - ferrite_cost, 2),
                "cost_diff_pct": round((ndfeb_cost - ferrite_cost) / max(ndfeb_cost, 1) * 100, 1),
                "recommendation": "NdFeB" if ndfeb_cost < ferrite_cost else "Ferrite",
            },
        })
    except Exception as e:
        return _err(str(e))
