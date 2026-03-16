"""
Sub-Agent Dispatcher：管理 Sub-Agent 注册表，实现 delegate_to_agent 工具。
"""

from __future__ import annotations

from agent.logger import get_logger
from agent.sub_agent_base import SubAgentBase

_log = get_logger("dispatcher")

# Sub-Agent 全局注册表 {name → SubAgentBase 实例}
_REGISTRY: dict[str, SubAgentBase] = {}


def register_agent(agent: SubAgentBase) -> None:
    """向注册表添加一个 Sub-Agent。"""
    _REGISTRY[agent.name] = agent
    _log.info("已注册 Sub-Agent: %s (%s)", agent.name, agent.description)


def get_agent(name: str) -> SubAgentBase | None:
    return _REGISTRY.get(name)


def list_agents() -> list[str]:
    return list(_REGISTRY.keys())


def delegate_to_agent(agent_name: str, task: str, context: str = "") -> dict:
    """
    将任务委托给指定的 Sub-Agent 执行并返回结果。
    供 MainAgent 的工具注册表调用。
    """
    agent = _REGISTRY.get(agent_name)
    if agent is None:
        available = list(_REGISTRY.keys())
        return {
            "success": False,
            "error": f"未知 Sub-Agent: '{agent_name}'。可用: {available}",
        }

    _log.info("委托任务给 [%s]: %s", agent_name, task[:100])
    result = agent.execute(task=task, context=context or "")
    _log.info("[%s] 完成，步骤数: %d，成功: %s",
              agent_name, len(result.get("steps", [])), result.get("success"))
    return result
