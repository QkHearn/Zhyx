"""FileReader - 文档读取"""

from pathlib import Path
from typing import Any, Callable

from skills.base import Skill


class FileReader(Skill):
    def __init__(self, config: dict | None = None):
        cfg = config or {}
        super().__init__(
            name=cfg.get("name", "FileReader"),
            description=cfg.get("description", "文档解析与读取"),
            permissions=cfg.get("permissions", []),
            config=cfg,
        )

    def run(
        self,
        args: dict[str, Any],
        tools: Callable[[str, dict], dict] | None = None,
    ) -> dict[str, Any]:
        path = args.get("path", "")
        encoding = args.get("encoding", "utf-8")
        if tools:
            out = tools("read_file", {"path": path})
            if "error" in out:
                return out
            return {"content": out.get("content", "")}
        try:
            content = Path(path).read_text(encoding=encoding, errors="replace")
            return {"content": content}
        except Exception as e:
            return {"error": str(e)}
