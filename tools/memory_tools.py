"""
Memory 工具：供 Main Agent 调用的持久化记忆接口。
"""

from __future__ import annotations

from agent.memory_manager import MemoryManager
from tools.utils import _err, _ok


def list_memories(query: str = "", top_k: int = 10) -> dict:
    manager = MemoryManager()
    items = manager.find_relevant_memories(query, top_k=top_k) if query.strip() else manager.list_memories()[:top_k]
    return {
        "success": True,
        "result": [
            {
                "name": item.name,
                "type": item.memory_type,
                "description": item.description,
                "path": str(item.path),
            }
            for item in items
        ],
    }


def read_memory(name: str) -> dict:
    manager = MemoryManager()
    item = manager.get_memory(name)
    if item is None:
        return {"success": False, "error": f"memory '{name}' 不存在"}
    return {
        "success": True,
        "result": {
            "name": item.name,
            "type": item.memory_type,
            "description": item.description,
            "content": item.content,
            "path": str(item.path),
        },
    }


def save_memory(
    name: str,
    content: str,
    memory_type: str,
    description: str,
    update_index: bool = True,
) -> dict:
    manager = MemoryManager()
    ok, msg = manager.save_memory(
        name=name,
        content=content,
        memory_type=memory_type,
        description=description,
        update_index=update_index,
    )
    if not ok:
        return {"success": False, "error": msg}
    item = manager.get_memory(name)
    return {
        "success": True,
        "result": {
            "message": msg,
            "path": str(item.path) if item else "",
        },
    }


def delete_memory(name: str, remove_from_index: bool = True) -> dict:
    manager = MemoryManager()
    ok, msg = manager.delete_memory(name, remove_from_index=remove_from_index)
    if not ok:
        return {"success": False, "error": msg}
    return {"success": True, "result": msg}



def save_simulation_case(
    name: str,
    task_description: str,
    key_params: dict,
    key_results: dict,
    lessons_learned: str = "",
    tags: list[str] | None = None,
) -> dict:
    """
    仿真完成后自动沉淀仿真案例到 Memory，形成可检索的历史案例库。

    将任务描述、关键参数、核心结果和经验教训以 Markdown 格式保存，
    支持后续通过 search_simulation_cases 检索类似案例。

    Args:
        name: 案例名称（例如："PMSM-48s8p-转矩优化"）
        task_description: 仿真任务的自然语言描述
        key_params: 关键设计参数 dict
        key_results: 核心仿真结果 dict
        lessons_learned: 经验教训或结论（可选）
        tags: 标签列表，用于辅助分类检索（可选）
    """
    from datetime import datetime
    from agent.memory_manager import MemoryManager

    if not name.strip():
        return _err("name 不能为空")
    if not task_description.strip():
        return _err("task_description 不能为空")
    if not key_params:
        return _err("key_params 不能为空")
    if not key_results:
        return _err("key_results 不能为空")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tag_str = ", ".join(tags) if tags else ""
    NL = "\n"

    # 构建 Markdown 案例内容
    lines = [
        f"## 任务描述{NL}{task_description}",
        "",
        "## 关键参数",
    ]
    for k, v in key_params.items():
        lines.append(f"- **{k}**: {v}")
    lines.extend(["", "## 核心结果"])
    for k, v in key_results.items():
        lines.append(f"- **{k}**: {v}")
    if lessons_learned.strip():
        lines.extend(["", "## 经验教训", lessons_learned.strip()])
    if tag_str:
        lines.extend(["", f"## 标签{NL}{tag_str}"])
    lines.extend(["", f"---{NL}*案例记录时间: {timestamp}*"])

    content_md = "\n".join(lines)

    description = f"仿真案例: {task_description[:80]}" + (f" [{tag_str}]" if tag_str else "")

    manager = MemoryManager()
    ok, msg = manager.save_memory(
        name=f"case-{name}",
        content=content_md,
        memory_type="simulation_case",
        description=description,
    )
    if not ok:
        return _err(msg)
    item = manager.get_memory(f"case-{name}")
    return _ok({
        "message": f"仿真案例 '{name}' 已沉淀到记忆库",
        "path": str(item.path) if item else "",
    })


def search_simulation_cases(
    query: str = "",
    top_k: int = 5,
) -> dict:
    """
    从历史案例库中检索与当前任务相关的仿真案例。

    Args:
        query: 检索关键词（例如："PMSM 转矩优化"、"热分析 温度"）
        top_k: 返回最相关的案例数量，默认 5
    """
    from agent.memory_manager import MemoryManager

    manager = MemoryManager()

    if query.strip():
        all_relevant = manager.find_relevant_memories(query, top_k=top_k * 3)
        cases = [m for m in all_relevant if m.memory_type == "simulation_case"][:top_k]
    else:
        all_mem = manager.list_memories()
        cases = [m for m in all_mem if m.memory_type == "simulation_case"][:top_k]

    return _ok({
        "count": len(cases),
        "cases": [
            {
                "name": c.name,
                "description": c.description,
                "path": str(c.path),
                "content_preview": c.content[:500],
            }
            for c in cases
        ],
    })
