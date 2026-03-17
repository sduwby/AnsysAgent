"""
AnsysAgent 统一数据目录。

所有运行时可写文件（配置、RAG 索引、日志、技能、角色等）均存放于此目录，
避免污染项目目录或 exe 同级目录，同时解决打包模式下的路径读写不一致问题。

默认位置：
  - 优先使用环境变量 ANSYS_AGENT_HOME
  - 否则使用 ~/.AnsysAgent

目录结构：
  {ANSYS_DATA_DIR}/
    .env                  ← LLM 配置（API Key、模型等）
    .rag/                 ← RAG 关键词索引
    knowledge/            ← 用户扩展知识库（official / internal）
    logs/                 ← 运行日志
    skills/               ← 用户自定义技能（SKILL.md）
    roles/                ← 用户自定义角色（*.md，最多 5 个，每个最多 200 行）
    mcp_servers.json      ← MCP server 配置（首次运行自动生成含 DuckDuckGo 默认配置）
"""

from __future__ import annotations

import os
from pathlib import Path


def _resolve_data_dir() -> Path:
    custom_dir = os.getenv("ANSYS_AGENT_HOME", "").strip()
    if custom_dir:
        return Path(custom_dir).expanduser()
    return Path.home() / ".AnsysAgent"


ANSYS_DATA_DIR: Path = _resolve_data_dir()
ANSYS_DATA_DIR.mkdir(parents=True, exist_ok=True)
