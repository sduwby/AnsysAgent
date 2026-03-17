"""
AnsysAgent 统一数据目录。

所有运行时可写文件（配置、RAG 索引、日志、技能、角色等）均存放于此目录，
避免污染项目目录或 exe 同级目录，同时解决打包模式下的路径读写不一致问题。

目录结构：
  {ANSYS_DATA_DIR}/
    .env                  ← LLM 配置（API Key、模型等）
    .rag/                 ← RAG 关键词索引
    logs/                 ← 运行日志
    skills/               ← 用户自定义技能（SKILL.md）
    roles/                ← 用户自定义角色（*.md，最多 5 个，每个最多 200 行）
    mcp_servers.json      ← MCP server 配置（首次运行自动生成含 DuckDuckGo 默认配置）
"""

from __future__ import annotations

import tempfile
from pathlib import Path

# 统一数据根目录：系统临时目录下的 .AnsysAgent 子目录
ANSYS_DATA_DIR: Path = Path(tempfile.gettempdir()) / ".AnsysAgent"
ANSYS_DATA_DIR.mkdir(parents=True, exist_ok=True)
