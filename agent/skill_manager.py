"""
Skill 管理器：扫描技能目录，解析 SKILL.md frontmatter，提供技能查询接口。

技能目录（按优先级）：
  1. {ANSYS_DATA_DIR}/skills/  ← 用户自定义技能（可写）
  2. {PROJECT_ROOT}/skills/    ← 项目内置技能（随包分发，开发时可用）

每个技能为一个子目录，包含 SKILL.md 文件，格式示例：
  ---
  name: maxwell-motor-workflow
  description: Maxwell 电机 2D 仿真标准流程
  ---
  # 完整内容...
"""

from __future__ import annotations

import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from agent.paths import ANSYS_DATA_DIR
from agent.logger import get_logger

_log = get_logger("skill_manager")

# ---------------------------------------------------------------------------
# 技能目录
# ---------------------------------------------------------------------------

_USER_SKILLS_DIR: Path = ANSYS_DATA_DIR / "skills"

if getattr(sys, "frozen", False):
    # 打包模式：内置技能在 _MEIPASS/skills/
    _BUILTIN_SKILLS_DIR: Path = Path(sys._MEIPASS) / "skills"  # type: ignore[attr-defined]
else:
    # 开发模式：项目根目录 skills/
    _BUILTIN_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class Skill:
    name: str
    description: str
    location: Path
    enabled: bool = True
    content: str = field(default="", repr=False)


# ---------------------------------------------------------------------------
# Frontmatter 解析
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """解析 YAML frontmatter，返回 (metadata_dict, body_text)。"""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip()
    return meta, text[m.end():]


# ---------------------------------------------------------------------------
# SkillManager 单例
# ---------------------------------------------------------------------------

class SkillManager:
    _instance: Optional["SkillManager"] = None

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}
        self._scan()

    @classmethod
    def get_instance(cls) -> "SkillManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _scan(self) -> None:
        """扫描所有技能目录，加载 SKILL.md 文件。用户目录优先（同名覆盖内置）。"""
        for skills_dir in [_BUILTIN_SKILLS_DIR, _USER_SKILLS_DIR]:
            if not skills_dir.exists():
                continue
            for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
                try:
                    text = skill_md.read_text(encoding="utf-8")
                    meta, _ = _parse_frontmatter(text)
                    name = meta.get("name", skill_md.parent.name)
                    skill = Skill(
                        name=name,
                        description=meta.get("description", ""),
                        location=skill_md,
                        enabled=True,
                        content=text,
                    )
                    self._skills[name] = skill
                    _log.debug("已加载技能: %s (from %s)", name, skill_md)
                except Exception as exc:
                    _log.warning("加载技能失败 %s: %s", skill_md, exc)
        _log.info("共加载 %d 个技能: %s", len(self._skills), list(self._skills))

    def get_available_skills(self) -> list[Skill]:
        return [s for s in self._skills.values() if s.enabled]

    def get_skill(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)

    def reload(self) -> None:
        """重新扫描技能目录（热加载）。"""
        self._skills.clear()
        self._scan()

    def is_user_skill(self, name: str) -> bool:
        """检查技能是否为用户自定义（非内置）。"""
        skill = self._skills.get(name)
        if skill is None:
            return False
        return str(skill.location).startswith(str(_USER_SKILLS_DIR))

    def create_user_skill(self, name: str, description: str, content: str) -> tuple[bool, str]:
        """在用户技能目录创建新技能。如已存在用户同名技能则覆盖。"""
        safe_name = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff\-_]", "-", name.strip().lower())
        safe_name = re.sub(r"-+", "-", safe_name).strip("-") or "unnamed"

        # 内置技能不允许用同名用户技能覆盖（除非用户技能已存在）
        existing = self._skills.get(safe_name)
        if existing is not None and not self.is_user_skill(safe_name):
            return False, f"'{safe_name}' 是内置技能，无法创建同名用户技能"

        skill_dir = _USER_SKILLS_DIR / safe_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        frontmatter = f"---\nname: {safe_name}\ndescription: {description}\n---\n\n"
        full_content = frontmatter + content
        (skill_dir / "SKILL.md").write_text(full_content, encoding="utf-8")

        self.reload()
        _log.info("已创建用户技能: %s", safe_name)
        return True, f"技能 '{safe_name}' 已创建"

    def delete_user_skill(self, name: str) -> tuple[bool, str]:
        """删除用户自定义技能（内置技能不可删除）。"""
        skill = self._skills.get(name)
        if skill is None:
            return False, f"技能 '{name}' 不存在"
        if not self.is_user_skill(name):
            return False, f"技能 '{name}' 是内置技能，不可删除"
        shutil.rmtree(skill.location.parent)
        self.reload()
        _log.info("已删除用户技能: %s", name)
        return True, f"技能 '{name}' 已删除"
