"""
对话历史管理器：负责存储和管理 ChatAgent 及 SubAgent 的对话历史。

目录结构：
    {ANSYS_DATA_DIR}/chatSessionHistiry/
        {chat_id}_{timestamp}/
            {agent_type}/
                {agent_id}_{timestamp}.json
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from agent.logger import get_logger
from agent.paths import ANSYS_DATA_DIR

_log = get_logger("chat_history_manager")

CHAT_HISTORY_DIR: Path = ANSYS_DATA_DIR / "chatSessionHistiry"


def _generate_id() -> str:
    """生成唯一ID（UUID4 去掉横线，取前12位）"""
    return uuid.uuid4().hex[:12]


def _format_timestamp(dt: datetime | None = None) -> str:
    """格式化时间为 YYYYMMDD-HH:MM:SS"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y%m%d-%H:%M:%S")


def _sanitize_agent_type(agent_name: str) -> str:
    """将 agent 名称转换为合法的目录名"""
    return agent_name.lower().replace(" ", "_").replace("-", "_")


class ChatSessionHistory:
    """管理单个 ChatAgent 会话的历史记录"""

    def __init__(self, chat_id: str | None = None, chat_timestamp: str | None = None):
        self.chat_id = chat_id or _generate_id()
        self.chat_timestamp = chat_timestamp or _format_timestamp()
        self.session_dir: Path = CHAT_HISTORY_DIR / f"{self.chat_id}_{self.chat_timestamp}"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self._sub_agent_sessions: dict[str, list[SubAgentSessionHistory]] = {}

    def create_sub_agent_session(self, agent_name: str, agent_id: str | None = None, agent_timestamp: str | None = None) -> SubAgentSessionHistory:
        """创建子 Agent 的历史会话记录"""
        agent_type = _sanitize_agent_type(agent_name)
        session = SubAgentSessionHistory(
            parent_dir=self.session_dir,
            agent_type=agent_type,
            agent_id=agent_id or _generate_id(),
            agent_timestamp=agent_timestamp or _format_timestamp(),
        )
        if agent_type not in self._sub_agent_sessions:
            self._sub_agent_sessions[agent_type] = []
        self._sub_agent_sessions[agent_type].append(session)
        return session

    def save_chat_history(self, history: list[dict[str, Any]], metadata: dict[str, Any] | None = None) -> Path:
        """保存 ChatAgent 的对话历史到文件"""
        data = {
            "chat_id": self.chat_id,
            "chat_timestamp": self.chat_timestamp,
            "save_time": _format_timestamp(),
            "metadata": metadata or {},
            "messages": history,
        }
        file_path = self.session_dir / "chat_history.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        _log.info("已保存 ChatAgent 历史: %s", file_path)
        return file_path

    def save_sub_agent_history(
        self,
        agent_name: str,
        agent_id: str,
        history: list[dict[str, Any]],
        steps: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
    ) -> Path:
        """保存 SubAgent 的对话历史"""
        agent_type = _sanitize_agent_type(agent_name)
        agent_dir = self.session_dir / agent_type
        agent_dir.mkdir(parents=True, exist_ok=True)

        agent_timestamp = _format_timestamp()
        file_path = agent_dir / f"{agent_id}_{agent_timestamp}.json"

        data = {
            "agent_name": agent_name,
            "agent_id": agent_id,
            "agent_timestamp": agent_timestamp,
            "save_time": _format_timestamp(),
            "metadata": metadata or {},
            "messages": history,
            "steps": steps or [],
            "result": result or {},
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        _log.info("已保存 SubAgent 历史: %s", file_path)
        return file_path


class SubAgentSessionHistory:
    """管理单个 SubAgent 的历史记录"""

    def __init__(self, parent_dir: Path, agent_type: str, agent_id: str, agent_timestamp: str):
        self.parent_dir = parent_dir
        self.agent_type = agent_type
        self.agent_id = agent_id
        self.agent_timestamp = agent_timestamp
        self.agent_dir: Path = parent_dir / agent_type
        self.agent_dir.mkdir(parents=True, exist_ok=True)

    def save_history(
        self,
        history: list[dict[str, Any]],
        steps: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
    ) -> Path:
        """保存 SubAgent 的对话历史"""
        file_path = self.agent_dir / f"{self.agent_id}_{self.agent_timestamp}.json"

        data = {
            "agent_id": self.agent_id,
            "agent_timestamp": self.agent_timestamp,
            "save_time": _format_timestamp(),
            "metadata": metadata or {},
            "messages": history,
            "steps": steps or [],
            "result": result or {},
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        _log.info("已保存 SubAgent 历史: %s", file_path)
        return file_path


_chat_session: ChatSessionHistory | None = None


def get_chat_session() -> ChatSessionHistory:
    """获取当前的 ChatSessionHistory 实例（单例模式）"""
    global _chat_session
    if _chat_session is None:
        _chat_session = ChatSessionHistory()
    return _chat_session


def reset_chat_session() -> ChatSessionHistory:
    """重置并创建新的 ChatSessionHistory 实例"""
    global _chat_session
    _chat_session = ChatSessionHistory()
    return _chat_session


def get_chat_history_dir() -> Path:
    """获取对话历史存储目录"""
    CHAT_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    return CHAT_HISTORY_DIR
