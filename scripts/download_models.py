#!/usr/bin/env python3
"""下载 Live2D 模型到 assets/avatar/models/

用法:
  python scripts/download_models.py           # 下载全部
  python scripts/download_models.py hijiki koharu   # 下载指定模型
"""

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "assets" / "avatar" / "models"
REGISTRY = MODELS_DIR / "registry.json"

# 需要递归下载的模型（从 guansss 仓库，结构不同于 npm）
SHIZUKU_BASE = "https://cdn.jsdelivr.net/gh/guansss/pixi-live2d-display@master/test/assets/shizuku/"

# npm 模型：包名 -> (model.json 名, 版本)
NPM_MODELS = {
    "hijiki": ("hijiki.model.json", "1.0.5"),
    "koharu": ("koharu.model.json", "1.0.5"),
    "chitose": ("chitose.model.json", "1.0.5"),
    "epsilon": ("Epsilon2.1.model.json", "1.0.5"),  # 包名 epsilon2_1
    "tororo": ("tororo.model.json", "1.0.5"),
    "izumi": ("izumi.model.json", "1.0.5"),
}


def download_url(url: str, dst: Path) -> bool:
    if dst.exists():
        return True
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=60) as r:
            dst.write_bytes(r.read())
        print(f"  ✓ {dst.relative_to(MODELS_DIR)}")
        return True
    except Exception as e:
        print(f"  ✗ {dst.name}: {e}")
        return False


def collect_files_from_model_json(model_json: dict, prefix: str = "") -> list[str]:
    """从 model.json 解析所有依赖文件路径"""
    files = []
    if "model" in model_json:
        files.append(model_json["model"])
    for t in model_json.get("textures", []):
        files.append(t)
    for k, v in model_json.get("motions", {}).items():
        for m in v if isinstance(v, list) else []:
            if isinstance(m, dict) and "file" in m:
                files.append(m["file"])
    for exp in model_json.get("expressions", []):
        if isinstance(exp, dict) and "file" in exp:
            files.append(exp["file"])
    for k in ("physics", "pose"):
        if model_json.get(k):
            files.append(model_json[k])
    return files


def download_shizuku():
    """下载 shizuku（结构特殊，单独处理）"""
    out = MODELS_DIR / "shizuku"
    out.mkdir(parents=True, exist_ok=True)
    req = urllib.request.urlopen(SHIZUKU_BASE + "shizuku.model.json", timeout=30)
    model = json.loads(req.read())
    (out / "shizuku.model.json").write_text(json.dumps(model, indent=2, ensure_ascii=False))

    files = ["shizuku.moc", "shizuku.physics.json", "shizuku.pose.json"]
    for t in model.get("textures", []):
        files.append(t)
    for exp in model.get("expressions", []):
        files.append(exp["file"])
    for motions in model.get("motions", {}).values():
        for m in motions[:3]:
            files.append(m["file"])

    ok = 0
    for f in files:
        if download_url(SHIZUKU_BASE + f, out / f):
            ok += 1
    return ok


def download_npm_model(name: str) -> bool:
    """下载 npm 包中的模型"""
    if name not in NPM_MODELS:
        return False
    model_file, ver = NPM_MODELS[name]
    pkg = "epsilon2_1" if name == "epsilon" else name
    base = f"https://cdn.jsdelivr.net/npm/live2d-widget-model-{pkg}@{ver}/assets/"
    out = MODELS_DIR / name
    out.mkdir(parents=True, exist_ok=True)

    try:
        req = urllib.request.urlopen(base + model_file, timeout=30)
        model = json.loads(req.read())
    except Exception as e:
        print(f"  ✗ {name}: 无法获取 model.json - {e}")
        return False

    # 保存 model.json（epsilon 的键是 Epsilon2.1.model.json）
    dst_json = out / model_file
    dst_json.write_text(json.dumps(model, indent=2, ensure_ascii=False))

    files = collect_files_from_model_json(model)
    ok = 1  # model.json 已保存
    for f in files:
        if download_url(base + f, out / f):
            ok += 1
    return ok


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if not REGISTRY.exists():
        print("registry.json 不存在，请检查 assets/avatar/models/")
        return 1

    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    want = sys.argv[1:] if len(sys.argv) > 1 else list(reg.keys())

    for name in want:
        if name not in reg:
            print(f"跳过未知模型: {name}")
            continue
        print(f"下载 {name}...")
        if name == "shizuku":
            download_shizuku()
        else:
            download_npm_model(name)
    print("完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
