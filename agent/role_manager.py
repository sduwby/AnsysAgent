"""
Role 管理器：管理用户自定义角色（system prompt 附加片段）。

持久化目录：{ANSYS_DATA_DIR}/roles/
文件格式：Markdown（.md），每个文件为一个 role。

限制：
  - 最多 5 个 role 文件
  - 每个文件最多 200 行
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from agent.paths import ANSYS_DATA_DIR
from agent.logger import get_logger

_log = get_logger("role_manager")

ROLES_DIR: Path = ANSYS_DATA_DIR / "roles"
MAX_ROLES = 5
MAX_LINES = 200

# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _sanitize_name(name: str) -> str:
    """将 role 名称规范化为合法文件名（小写，只保留字母数字和连字符）。"""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9\u4e00-\u9fff\-_]", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "unnamed"


def _role_path(name: str) -> Path:
    return ROLES_DIR / f"{_sanitize_name(name)}.md"


# ---------------------------------------------------------------------------
# RoleManager
# ---------------------------------------------------------------------------

class RoleManager:
    """Role 文件的 CRUD 管理器（无状态，每次操作直接读写磁盘）。"""

    def __init__(self) -> None:
        ROLES_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def list_roles(self) -> list[str]:
        """返回所有 role 名称（不含 .md 扩展名）。"""
        return sorted(p.stem for p in ROLES_DIR.glob("*.md"))

    def get_role(self, name: str) -> Optional[str]:
        """返回 role 文件内容，不存在则返回 None。"""
        path = _role_path(name)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def get_roles_prompt(self) -> str:
        """
        加载所有 role 文件内容并合并为系统提示注入片段。
        返回空字符串表示无 role。
        """
        roles = self.list_roles()
        if not roles:
            return ""
        parts = ["## 当前激活的用户角色定义（请在回复时遵守以下角色设定）\n"]
        for name in roles:
            content = self.get_role(name)
            if content:
                parts.append(f"### Role: {name}\n{content.strip()}\n")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------

    def add_role(self, name: str, content: str) -> tuple[bool, str]:
        """
        新增 role。
        返回 (success: bool, message: str)。
        """
        existing = self.list_roles()

        # 检查上限
        if len(existing) >= MAX_ROLES:
            return False, f"已达到最大 role 数量限制（{MAX_ROLES} 个），请先删除一个后再添加。"

        # 检查重名
        safe_name = _sanitize_name(name)
        if safe_name in existing:
            return False, f"Role '{safe_name}' 已存在，请使用 change 命令修改。"

        # 检查行数
        lines = content.splitlines()
        if len(lines) > MAX_LINES:
            return False, f"内容超过行数限制（{len(lines)} 行，最多 {MAX_LINES} 行）。"

        _role_path(name).write_text(content, encoding="utf-8")
        _log.info("已添加 role: %s", safe_name)
        return True, f"Role '{safe_name}' 已创建。"

    def update_role(self, name: str, content: str) -> tuple[bool, str]:
        """
        更新已有 role 的内容。
        返回 (success: bool, message: str)。
        """
        safe_name = _sanitize_name(name)
        path = _role_path(name)
        if not path.exists():
            return False, f"Role '{safe_name}' 不存在，请使用 add 命令创建。"

        lines = content.splitlines()
        if len(lines) > MAX_LINES:
            return False, f"内容超过行数限制（{len(lines)} 行，最多 {MAX_LINES} 行）。"

        path.write_text(content, encoding="utf-8")
        _log.info("已更新 role: %s", safe_name)
        return True, f"Role '{safe_name}' 已更新。"

    def delete_role(self, name: str) -> tuple[bool, str]:
        """
        删除 role 文件。
        返回 (success: bool, message: str)。
        """
        safe_name = _sanitize_name(name)
        path = _role_path(name)
        if not path.exists():
            return False, f"Role '{safe_name}' 不存在。"
        path.unlink()
        _log.info("已删除 role: %s", safe_name)
        return True, f"Role '{safe_name}' 已删除。"
