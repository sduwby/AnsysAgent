"""
仿真流程模板系统：提供标准化的仿真流程模板管理功能。

功能特性：
- 预设仿真流程模板（电机设计、整车碰撞、CFD分析等）
- 用户自定义模板支持
- 模板验证和质量检查
- 批量执行模板

每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from tools.utils import _ok, _err, ok_message, ensure_parent_dir

# 预设模板定义
_PRESET_TEMPLATES = {
    "motor_design": {
        "name": "电机设计标准流程",
        "description": "从几何建模到性能分析的完整电机设计流程",
        "domain": "电机设计",
        "steps": [
            {"tool": "connect_aedt", "params": {}},
            {"tool": "create_maxwell_project", "params": {"project_name": "MotorDesign"}},
            {"tool": "create_motor_geometry", "params": {"slots": 36, "poles": 6}},
            {"tool": "assign_material", "params": {"material_name": "1008 Steel"}},
            {"tool": "setup_winding", "params": {"winding_type": "distributed"}},
            {"tool": "add_solution_setup", "params": {"setup_type": "Magnetostatic"}},
            {"tool": "setup_length_mesh", "params": {"max_length": 1}},
            {"tool": "run_simulation", "params": {}},
            {"tool": "get_torque", "params": {}},
            {"tool": "get_back_emf", "params": {}},
            {"tool": "get_inductance", "params": {}},
            {"tool": "create_field_plot", "params": {"quantity": "B"}},
        ],
    },
    "motor_em_thermal": {
        "name": "电机电磁-热耦合分析",
        "description": "电磁仿真与热分析的耦合迭代流程",
        "domain": "电机设计",
        "steps": [
            {"tool": "connect_aedt", "params": {}},
            {"tool": "create_maxwell_project", "params": {"project_name": "EMThermal"}},
            {"tool": "create_motor_geometry", "params": {}},
            {"tool": "assign_material", "params": {}},
            {"tool": "setup_winding", "params": {}},
            {"tool": "add_solution_setup", "params": {"setup_type": "Transient"}},
            {"tool": "run_simulation", "params": {}},
            {"tool": "get_losses", "params": {}},
            {"tool": "connect_icepak", "params": {}},
            {"tool": "link_maxwell_to_icepak", "params": {}},
            {"tool": "run_em_thermal_iteration", "params": {"max_iterations": 5}},
            {"tool": "get_temperature_results", "params": {}},
        ],
    },
    "vehicle_crash": {
        "name": "整车碰撞安全分析",
        "description": "LS-DYNA正面碰撞仿真流程",
        "domain": "整车仿真",
        "steps": [
            {"tool": "connect_crash_solver", "params": {}},
            {"tool": "create_crash_deck", "params": {"deck_name": "FrontalCrash"}},
            {"tool": "load_vehicle_model", "params": {}},
            {"tool": "setup_frontal_crash", "params": {"velocity": 50}},
            {"tool": "add_initial_velocity", "params": {}},
            {"tool": "export_crash_model", "params": {}},
            {"tool": "run_crash_simulation", "params": {}},
            {"tool": "get_crash_results", "params": {}},
            {"tool": "get_dummy_injury_criteria", "params": {}},
        ],
    },
    "vehicle_cfd": {
        "name": "整车CFD外流场分析",
        "description": "空气动力学仿真流程",
        "domain": "整车仿真",
        "steps": [
            {"tool": "connect_fluent", "params": {}},
            {"tool": "read_fluent_mesh", "params": {}},
            {"tool": "setup_fluid_models", "params": {"model": "k-epsilon"}},
            {"tool": "define_boundary_conditions", "params": {"velocity": 120}},
            {"tool": "setup_fluent_solver", "params": {}},
            {"tool": "initialize_fluent", "params": {}},
            {"tool": "run_fluent_simulation", "params": {}},
            {"tool": "get_fluent_results", "params": {}},
            {"tool": "get_aero_coefficients", "params": {}},
        ],
    },
    "structural_analysis": {
        "name": "结构强度分析",
        "description": "静力学分析流程",
        "domain": "结构分析",
        "steps": [
            {"tool": "connect_mapdl", "params": {}},
            {"tool": "import_geometry", "params": {}},
            {"tool": "assign_material", "params": {}},
            {"tool": "mesh_model", "params": {}},
            {"tool": "apply_boundary_conditions", "params": {}},
            {"tool": "apply_loads", "params": {}},
            {"tool": "run_structural_analysis", "params": {}},
            {"tool": "get_stress_results", "params": {}},
            {"tool": "get_displacement_results", "params": {}},
        ],
    },
    "nvh_analysis": {
        "name": "NVH噪声振动分析",
        "description": "完整NVH链路分析流程",
        "domain": "NVH",
        "steps": [
            {"tool": "connect_aedt", "params": {}},
            {"tool": "create_maxwell_project", "params": {"project_name": "NVH_Analysis"}},
            {"tool": "create_motor_geometry", "params": {}},
            {"tool": "setup_winding", "params": {}},
            {"tool": "add_solution_setup", "params": {"setup_type": "Magnetostatic"}},
            {"tool": "run_simulation", "params": {}},
            {"tool": "get_em_force", "params": {}},
            {"tool": "connect_mechanical", "params": {}},
            {"tool": "import_maxwell_forces", "params": {}},
            {"tool": "run_modal_analysis", "params": {"num_modes": 20}},
            {"tool": "run_harmonic_analysis", "params": {}},
            {"tool": "get_vibration_results", "params": {}},
        ],
    },
}

# 模板存储路径
def _get_template_dir() -> Path:
    """获取模板存储目录"""
    from agent.paths import get_ansys_data_dir
    return Path(get_ansys_data_dir()) / "templates"


# ---------------------------------------------------------------------------
# 工具：list_templates - 列出所有可用模板
# ---------------------------------------------------------------------------

def list_templates() -> dict:
    """
    列出所有可用的仿真流程模板。
    """
    try:
        templates = []
        
        # 添加预设模板
        for template_id, template in _PRESET_TEMPLATES.items():
            templates.append({
                "id": template_id,
                "name": template["name"],
                "description": template["description"],
                "domain": template["domain"],
                "source": "preset",
                "step_count": len(template["steps"]),
            })
        
        # 添加用户自定义模板
        template_dir = _get_template_dir()
        if template_dir.exists():
            for file in template_dir.glob("*.json"):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        user_template = json.load(f)
                    templates.append({
                        "id": file.stem,
                        "name": user_template.get("name", file.stem),
                        "description": user_template.get("description", ""),
                        "domain": user_template.get("domain", "自定义"),
                        "source": "user",
                        "step_count": len(user_template.get("steps", [])),
                    })
                except Exception:
                    pass
        
        return _ok({
            "count": len(templates),
            "templates": templates,
            "message": f"找到 {len(templates)} 个模板",
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_template - 获取模板详情
# ---------------------------------------------------------------------------

def get_template(template_id: str) -> dict:
    """
    获取指定模板的详细信息。

    Args:
        template_id: 模板ID
    """
    try:
        # 先检查预设模板
        if template_id in _PRESET_TEMPLATES:
            return _ok({
                "id": template_id,
                "source": "preset",
                **_PRESET_TEMPLATES[template_id],
            })
        
        # 检查用户自定义模板
        template_dir = _get_template_dir()
        template_file = template_dir / f"{template_id}.json"
        
        if template_file.exists():
            with open(template_file, 'r', encoding='utf-8') as f:
                template = json.load(f)
            return _ok({
                "id": template_id,
                "source": "user",
                **template,
            })
        
        return _err(f"模板不存在: {template_id}")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：save_template - 保存自定义模板
# ---------------------------------------------------------------------------

def save_template(
    template_id: str,
    name: str,
    description: str,
    domain: str,
    steps: list[dict],
    overwrite: bool = False,
) -> dict:
    """
    保存用户自定义模板。

    Args:
        template_id: 模板ID（用于唯一标识）
        name: 模板名称
        description: 模板描述
        domain: 所属领域
        steps: 步骤列表，每个步骤包含 tool 和 params
        overwrite: 是否覆盖已存在的模板
    """
    try:
        # 检查是否为预设模板
        if template_id in _PRESET_TEMPLATES:
            return _err(f"无法修改预设模板: {template_id}")
        
        template_dir = _get_template_dir()
        template_dir.mkdir(parents=True, exist_ok=True)
        
        template_file = template_dir / f"{template_id}.json"
        
        if template_file.exists() and not overwrite:
            return _err(f"模板已存在: {template_id}，使用 overwrite=True 覆盖")
        
        # 验证步骤格式
        for i, step in enumerate(steps):
            if "tool" not in step:
                return _err(f"步骤 {i} 缺少 'tool' 字段")
            if "params" not in step:
                return _err(f"步骤 {i} 缺少 'params' 字段")
        
        template = {
            "name": name,
            "description": description,
            "domain": domain,
            "steps": steps,
            "created_at": os.path.getctime(template_file) if template_file.exists() else None,
        }
        
        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2, ensure_ascii=False)
        
        return _ok(ok_message(
            f"模板 '{template_id}' 已保存",
            template_id=template_id,
            name=name,
            step_count=len(steps),
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：delete_template - 删除自定义模板
# ---------------------------------------------------------------------------

def delete_template(template_id: str) -> dict:
    """
    删除用户自定义模板。

    Args:
        template_id: 模板ID
    """
    try:
        if template_id in _PRESET_TEMPLATES:
            return _err(f"无法删除预设模板: {template_id}")
        
        template_dir = _get_template_dir()
        template_file = template_dir / f"{template_id}.json"
        
        if not template_file.exists():
            return _err(f"模板不存在: {template_id}")
        
        template_file.unlink()
        return _ok(ok_message(f"模板 '{template_id}' 已删除"))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：validate_template - 验证模板有效性
# ---------------------------------------------------------------------------

def validate_template(template_id: str) -> dict:
    """
    验证模板的有效性，检查工具是否存在。

    Args:
        template_id: 模板ID
    """
    try:
        from agent.tool_definitions import TOOL_REGISTRY
        
        template = get_template(template_id)
        if not template["success"]:
            return template
        
        template_data = template["result"]
        steps = template_data.get("steps", [])
        
        validation_results = []
        all_valid = True
        
        for i, step in enumerate(steps):
            tool_name = step.get("tool")
            params = step.get("params", {})
            
            if tool_name not in TOOL_REGISTRY:
                validation_results.append({
                    "step": i,
                    "tool": tool_name,
                    "valid": False,
                    "error": f"工具不存在: {tool_name}",
                })
                all_valid = False
            else:
                validation_results.append({
                    "step": i,
                    "tool": tool_name,
                    "valid": True,
                    "params": list(params.keys()),
                })
        
        return _ok({
            "valid": all_valid,
            "template_id": template_id,
            "step_count": len(steps),
            "valid_steps": sum(1 for r in validation_results if r["valid"]),
            "validation_results": validation_results,
            "message": "模板验证完成",
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：execute_template - 执行模板
# ---------------------------------------------------------------------------

def execute_template(
    template_id: str,
    params: Optional[dict] = None,
) -> dict:
    """
    执行指定的仿真流程模板。

    Args:
        template_id: 模板ID
        params: 额外参数，将覆盖模板中的默认参数
    """
    try:
        from agent.tool_definitions import TOOL_REGISTRY
        
        template = get_template(template_id)
        if not template["success"]:
            return template
        
        template_data = template["result"]
        steps = template_data.get("steps", [])
        
        execution_results = []
        success_count = 0
        fail_count = 0
        
        for i, step in enumerate(steps):
            tool_name = step.get("tool")
            step_params = step.get("params", {}).copy()
            
            # 合并用户参数
            if params:
                step_params.update(params.get(tool_name, {}))
            
            try:
                if tool_name not in TOOL_REGISTRY:
                    execution_results.append({
                        "step": i,
                        "tool": tool_name,
                        "success": False,
                        "error": f"工具不存在: {tool_name}",
                    })
                    fail_count += 1
                    continue
                
                tool_func = TOOL_REGISTRY[tool_name]
                result = tool_func(**step_params)
                
                execution_results.append({
                    "step": i,
                    "tool": tool_name,
                    "success": result.get("success", False),
                    "result": result.get("result"),
                    "message": result.get("message") or result.get("error"),
                })
                
                if result.get("success"):
                    success_count += 1
                else:
                    fail_count += 1
                    # 可选：遇到失败时停止执行
                    # break
            
            except Exception as e:
                execution_results.append({
                    "step": i,
                    "tool": tool_name,
                    "success": False,
                    "error": str(e),
                })
                fail_count += 1
        
        return _ok({
            "template_id": template_id,
            "template_name": template_data.get("name"),
            "total_steps": len(steps),
            "success_count": success_count,
            "fail_count": fail_count,
            "results": execution_results,
            "message": f"模板执行完成，成功 {success_count} 步，失败 {fail_count} 步",
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：create_template_from_history - 从对话历史创建模板
# ---------------------------------------------------------------------------

def create_template_from_history(
    template_id: str,
    name: str,
    description: str,
    domain: str,
    history_steps: list[dict],
) -> dict:
    """
    从对话历史中提取工具调用序列创建模板。

    Args:
        template_id: 新模板ID
        name: 模板名称
        description: 模板描述
        domain: 所属领域
        history_steps: 历史步骤列表，每个步骤包含 tool 和 params
    """
    try:
        # 提取工具调用序列
        steps = []
        for step in history_steps:
            tool_name = step.get("tool")
            params = step.get("params", {})
            
            if tool_name:
                steps.append({
                    "tool": tool_name,
                    "params": params,
                })
        
        return save_template(
            template_id=template_id,
            name=name,
            description=description,
            domain=domain,
            steps=steps,
            overwrite=False,
        )
    except Exception as e:
        return _err(str(e))
