#!/usr/bin/env python3
"""测试形象说话：传入字符串，形象会说出来

用法:
  1. 先启动形象: ./start.sh 或 python src/main.py
  2. 再运行: python scripts/test_speak.py
  3. 或带参数: python scripts/test_speak.py 你好我是米拉
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from voice.tts import speak

if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "你好我是米拉"
    print(f"形象说: {text}")
    result = speak(text)
    if result:
        print("已触发，形象窗口会播放（需先启动 avatar）")
    else:
        print("失败，请安装: pip install edge-tts")
