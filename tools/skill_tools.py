"""
Skill 工具：按需加载指定技能的 SKILL.md 全文内容供 LLM 使用。
"""

from __future__ import annotations

from agent.skill_manager import SkillManager
from agent.logger import get_logger

_log = get_logger("skill_tools")


def use_skill(skill_name: str) -> dict:
    """
    加载并返回指定技能的完整内容。

    返回结构：
      success=True  → {"success": True, "skill_name": ..., "content": ..., "skill_dir": ...}
      success=False → {"success": False, "error": ..., "available_skills": [...]}
    """
    manager = SkillManager.get_instance()
    skill = manager.get_skill(skill_name)

    if skill is None:
        available = [s.name for s in manager.get_available_skills()]
        _log.warning("请求的技能不存在: %s，可用: %s", skill_name, available)
        return {
            "success": False,
            "error": f"技能 '{skill_name}' 不存在。",
            "available_skills": available,
        }

    if not skill.enabled:
        return {
            "success": False,
            "error": f"技能 '{skill_name}' 当前未启用。",
        }

    # 列出技能目录中的辅助文件（排除 SKILL.md 本身）
    skill_dir = skill.location.parent
    try:
        aux_files = [str(f) for f in sorted(skill_dir.iterdir()) if f.name != "SKILL.md"]
    except Exception:
        aux_files = []

    _log.info("加载技能: %s", skill_name)
    return {
        "success": True,
        "skill_name": skill.name,
        "content": skill.content,
        "skill_dir": str(skill_dir),
        "files": aux_files,
    }
