#!/bin/bash
# macOS 打包脚本
# 用法：bash build.sh
# 输出：dist/ansys-agent（可执行文件）

set -e

echo "📦 安装依赖..."
pip install -r requirements.txt
pip install pyinstaller

echo "🔨 打包中..."
pyinstaller ansys-agent.spec --clean

echo "✅ 完成！可执行文件：dist/ansys-agent"
echo "   运行：./dist/ansys-agent"
