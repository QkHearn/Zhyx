#!/usr/bin/env bash
# 知式 Zhyx - 安装依赖
# 用法: ./resolve_deps.sh

set -e
cd "$(dirname "$0")"

echo "安装 Python 依赖..."
pip install -r requirements.txt

echo "FunASR 语音识别需 PyTorch，未安装则执行: pip install torch torchaudio"
echo "Office MCP 需 uv: brew install uv"
