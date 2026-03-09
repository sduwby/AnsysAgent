# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置
# Windows: pyinstaller ansys-agent.spec
# macOS:   pyinstaller ansys-agent.spec

import sys
from pathlib import Path

block_cipher = None

# 自动找到 gpt_tokenizer 数据文件（vocab 等）
try:
    import gpt_tokenizer
    gpt_tokenizer_datas = []
    gpt_tokenizer_dir = Path(gpt_tokenizer.__file__).parent
    for f in gpt_tokenizer_dir.rglob("*"):
        if f.is_file():
            rel = str(f.relative_to(gpt_tokenizer_dir.parent))
            gpt_tokenizer_datas.append((str(f), str(Path(rel).parent)))
except ImportError:
    gpt_tokenizer_datas = []

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        # gpt_tokenizer 词表数据
        *gpt_tokenizer_datas,
        # .env.example 供用户参考（.env 本身不打包）
        (".env.example", "."),
    ],
    hiddenimports=[
        "agent.chat_agent",
        "agent.prompt",
        "tools.maxwell_tools",
        "tools.result_tools",
        "openai",
        "rich",
        "click",
        "dotenv",
        "gpt_tokenizer",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ansys-agent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,          # 保留控制台窗口（CLI 工具需要）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Windows 下生成 .exe
    icon=None,
)
