#!/usr/bin/env python3
"""检查 LLM/TTS 等环境变量和实际生效配置"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

def main():
    print("=== 环境变量 ===")
    for k in ("ZHYX_LLM_URL", "ZHYX_LLM_MODEL", "ZHYX_LLM_API_KEY"):
        v = os.environ.get(k)
        print(f"  {k}: {repr(v) if v else '(未设置)'}")

    print("\n=== 实际生效的 LLM 配置 ===")
    try:
        from core.chat import _get_llm_config
        cfg = _get_llm_config()
        print(f"  url: {cfg.get('url')}")
        print(f"  model: {cfg.get('model')}")
        print(f"  api_format: {cfg.get('api_format')}")
        print(f"  api_key: {'(已设置)' if cfg.get('api_key') else '(空)'}")
        url = cfg.get("url", "")
        if "11434" in url or "localhost" in url:
            print("\n  ⚠ 当前指向 Ollama (localhost:11434)。若不用 Ollama，请：")
            print("     unset ZHYX_LLM_URL")
            print("  或在 .env / shell 中设置 ZHYX_LLM_URL 为智谱等云端地址")
    except Exception as e:
        print(f"  加载失败: {e}")

if __name__ == "__main__":
    main()
