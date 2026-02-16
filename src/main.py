#!/usr/bin/env python3
"""知式 Zhyx - 主入口（桌面 Live2D 形象）"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv  # noqa: E402
    load_dotenv(ROOT / ".env")
except ImportError:
    pass
sys.path.insert(0, str(ROOT / "src"))

from avatar.window import run_avatar

if __name__ == "__main__":
    run_avatar()
