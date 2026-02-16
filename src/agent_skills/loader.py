"""Agent Skills 动态加载 - 符合 [Agent Skills 规范](https://agentskills.io/)

支持多目录：预置 skills/ + 可写目录（智能体运行时创建）。每次调用重新扫描，实现动态加载/卸载。
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SKILLS_DIR = ROOT / "skills"


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """解析 YAML frontmatter 与 Markdown body"""
    body = content
    meta = {}
    if content.strip().startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                import yaml
                meta = yaml.safe_load(parts[1] or "{}") or {}
            except Exception:
                pass
            body = (parts[2] or "").strip()
    return meta, body


def _get_skills_config() -> dict:
    try:
        import yaml
        cfg = ROOT / "config" / "zhyx.yaml"
        if cfg.exists():
            with open(cfg, encoding="utf-8") as f:
                d = yaml.safe_load(f) or {}
            return d.get("skills") or {}
    except Exception:
        pass
    return {}


def _get_skill_directories() -> list[Path]:
    """返回要扫描的 skills 目录列表（预置 + 可写），每次调用重新读取 config"""
    cfg = _get_skills_config()
    dirs = []
    seen = set()

    # 主目录
    path = cfg.get("directory", "skills")
    p = (ROOT / path).resolve()
    if p.exists() and p.is_dir():
        dirs.append(p)
        seen.add(str(p))

    # 可写目录（智能体创建 skill 的位置）
    writable = cfg.get("writable_directory")
    if writable:
        pw = Path(writable).expanduser().resolve()
        pw.mkdir(parents=True, exist_ok=True)
        if str(pw) not in seen:
            dirs.append(pw)
    else:
        agent_created = DEFAULT_SKILLS_DIR / "agent_created"
        agent_created.mkdir(parents=True, exist_ok=True)
        if str(agent_created) not in seen:
            dirs.append(agent_created)

    return dirs


def _get_enabled_skills() -> list[str]:
    cfg = _get_skills_config()
    enabled = cfg.get("enabled")
    if isinstance(enabled, list):
        return [str(x).strip() for x in enabled if x]
    return []


def discover_skills() -> list[dict]:
    """动态发现所有 skills（每次调用重新扫描，无缓存）"""
    out = []
    seen = set()

    for base in _get_skill_directories():
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir()):
            if not d.is_dir() or d.name.startswith("."):
                continue
            if d.name in seen:
                continue
            md = d / "SKILL.md"
            if not md.exists() or not md.is_file():
                continue
            try:
                content = md.read_text(encoding="utf-8")
                meta, _ = _parse_frontmatter(content)
                name = meta.get("name") or d.name
                seen.add(d.name)
                out.append({
                    "name": name,
                    "description": meta.get("description") or "",
                    "path": str(md),
                    "dir": str(d),
                })
            except Exception:
                pass
    return out


def get_writable_skills_dir() -> Path | None:
    """返回智能体可写入新 skill 的目录。不存在则返回默认路径供创建。"""
    cfg = _get_skills_config()
    writable = cfg.get("writable_directory")
    if writable:
        p = Path(writable).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    default = DEFAULT_SKILLS_DIR / "agent_created"
    default.mkdir(parents=True, exist_ok=True)
    return default


def get_agent_skill_context() -> str:
    """
    动态加载并返回注入 system prompt 的 skills 上下文。
    每次调用重新扫描目录，支持运行时新增/删除 skill。
    """
    enabled = _get_enabled_skills()
    all_skills = discover_skills()
    if not all_skills:
        return ""

    meta_lines = ["## 可用 Skills（动态加载）\n"]
    for s in all_skills:
        desc = (s["description"] or "")[:150]
        meta_lines.append(f"- **{s['name']}**: {desc}{'...' if len(s.get('description', '')) > 150 else ''}")

    writable = get_writable_skills_dir()
    if writable:
        meta_lines.append(
            f"\n你拥有在 `{writable}` 下创建新 Skill 的权限。"
            "遇到复杂任务时，可先编写 Python 脚本作为 Skill，包含参数处理和错误回传。"
            "写完后将其用法记录到知识库，后续类似任务直接调用。"
            "新 Skill 会被动态加载，无需重启。"
        )

    load_bodies = len(enabled) > 0
    parts = []
    for s in all_skills:
        if not load_bodies or s["name"] not in enabled:
            continue
        md_path = Path(s["path"])
        if not md_path.exists():
            continue
        try:
            content = md_path.read_text(encoding="utf-8")
            _, body = _parse_frontmatter(content)
            if body:
                parts.append(f"## Skill: {s['name']}\n{body}")
        except Exception:
            pass

    if not parts:
        return "\n".join(meta_lines)

    return "\n".join(meta_lines) + "\n\n---\n\n" + "\n\n---\n\n".join(parts)
