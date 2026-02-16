#!/usr/bin/env python3
"""下载 Anthropic 官方 skills 到 skills/

用法:
  python scripts/download_anthropic_skills.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "skills"
REPO = "https://github.com/anthropics/skills.git"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = ROOT / ".tmp_skills_clone"
    try:
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)

        # sparse clone 只拉 skills/ 目录
        subprocess.run(
            ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", REPO, str(tmp)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "sparse-checkout", "set", "skills"],
            cwd=tmp,
            check=True,
            capture_output=True,
        )

        src = tmp / "skills"
        if not src.exists():
            print("未找到 skills 目录")
            return 1

        PROTECTED = {"agent_created"}  # 智能体创建目录，不覆盖
        for item in src.iterdir():
            if item.is_dir():
                if item.name in PROTECTED:
                    continue
                dst = OUT / item.name
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(item, dst)
                print(f"  ✓ {item.name}")
            elif item.name != ".git":
                shutil.copy2(item, OUT / item.name)
                print(f"  ✓ {item.name}")

        print(f"\n已下载到 {OUT}")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"git 失败: {e.stderr.decode() if e.stderr else e}")
        return 1
    except Exception as e:
        print(f"错误: {e}")
        return 1
    finally:
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
