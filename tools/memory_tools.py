"""
Memory 工具：供 Main Agent 调用的持久化记忆接口。
"""

from __future__ import annotations

from agent.memory_manager import MemoryManager


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
