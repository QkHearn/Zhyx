#!/usr/bin/env python3
"""测试：麦克风录音 -> 转文字 -> 打印 -> TTS 复述

用法:
  1. 先启动形象: ./start.sh 或 python src/main.py
  2. 再运行: python scripts/test_mic_speak.py
  3. 开始录音后说话，按 Enter 结束
  4. 终端打印识别文字，形象会复述

依赖: pip install -r requirements.txt（含 sounddevice funasr）
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _log(msg):
    print(msg, flush=True)


def main():
    from voice.stt import start_recording, stop_recording_and_speak
    from voice.tts import speak

    def on_text(text):
        if text:
            _log("识别结果: " + text)
            speak(text)
        else:
            _log("未识别到内容（录音太短、无声音或网络问题）")

    _log("开始录音，说完后按 Enter 结束...")
    if not start_recording():
        _log("无法启动录音，请执行: ./resolve_deps.sh")
        return 1
    input()
    _log("正在识别...")
    stop_recording_and_speak(callback=on_text)
    _log("完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
