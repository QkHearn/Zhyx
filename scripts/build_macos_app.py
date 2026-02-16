#!/usr/bin/env python3
"""打包知式 Zhyx 为 macOS .app

用法:
  pip install py2app
  python scripts/build_macos_app.py py2app -A   # 开发模式（依赖外链，快速测试）
  python scripts/build_macos_app.py py2app      # 发布模式（打包依赖，体积大）
"""

import os
from setuptools import setup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

# 需打包的数据（保持 config、assets、skills、prompts 目录结构）
DATA_FILES = []
for top in ["config", "assets", "skills", "prompts"]:
    top_path = os.path.join(ROOT, top)
    if not os.path.isdir(top_path):
        continue
    for r, _, fs in os.walk(top_path):
        if "__pycache__" in r or ".git" in r:
            continue
        rel = os.path.relpath(r, ROOT)
        files = [os.path.join(r, f) for f in fs if not f.startswith(".")]
        if files:
            DATA_FILES.append((rel, files))

APP = ["src/main.py"]
OPTIONS = {
    "argv_emulation": False,
    "packages": [
        "core", "api", "mcp_client", "skills", "agent_skills", "voice", "avatar",
        "yaml", "httpx", "uvicorn", "fastapi", "pydantic",
        "edge_tts", "sounddevice", "funasr", "pywebview",
    ],
    "includes": ["mcp", "uvicorn.logging"],
    "excludes": ["tkinter"],
    "iconfile": None,  # 可选: assets/icon.icns
    "plist": {
        "CFBundleName": "Zhyx",
        "CFBundleDisplayName": "知式",
        "CFBundleIdentifier": "com.zhyx.app",
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
        "NSMicrophoneUsageDescription": "用于语音对话",
        "NSSpeechRecognitionUsageDescription": "用于语音识别",
    },
}

setup(
    name="Zhyx",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
