# 知式 · Zhyx

> 本地优先数字人智能中枢 | Local-first Digital Human

[![CI](https://github.com/QKHearn/zhyx/actions/workflows/ci.yml/badge.svg)](https://github.com/QKHearn/zhyx/actions)

## 快速开始

```bash
./resolve_deps.sh     # 安装依赖
pip install torch torchaudio  # FunASR 语音识别所需
cp .env.sample .env   # 填写 ZHYX_LLM_API_KEY 等
./start.sh            # 启动桌面形象
```

**退出**：在小球上右键 → 退出；或终端中 `Ctrl+C`。

**可选系统依赖**：Office Skills 需 LibreOffice（`brew install libreoffice`），PDF 需 poppler（`brew install poppler`）

## 配置

- **敏感信息**：通过 `.env` 或环境变量设置，勿写入仓库  
  - `ZHYX_LLM_URL`、`ZHYX_LLM_MODEL`、`ZHYX_LLM_API_KEY`
- **示例**：`config/zhyx.yaml.example`、`.env.sample`
- **检查**：`python scripts/check_env.py`

## API（可选）

若需单独启动 HTTP API 服务（供外部调用），可运行 `scripts/start_api.sh` 或：

```bash
python -c "import sys; sys.path.insert(0,'src'); from dotenv import load_dotenv; load_dotenv(); import uvicorn; from api import app; uvicorn.run(app, host='0.0.0.0', port=8000)" 
```

## macOS 应用打包

打包为 `.app` 见 [docs/macOS_打包.md](docs/macOS_打包.md)。

## 架构

```
输入(Text/Voice/File/API) → MCP 多通道 → Skills(Chat/FileReader/FileWriter/TaskPlanner) → 输出
```
