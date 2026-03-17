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
