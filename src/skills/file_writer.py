"""FileWriter - 文档生成"""

from pathlib import Path
from typing import Any, Callable

from skills.base import Skill


class FileWriter(Skill):
    def __init__(self, config: dict | None = None):
        cfg = config or {}
        super().__init__(
            name=cfg.get("name", "FileWriter"),
            description=cfg.get("description", "文档生成与写入"),
            permissions=cfg.get("permissions", []),
            config=cfg,
        )

    def run(
        self,
        args: dict[str, Any],
        tools: Callable[[str, dict], dict] | None = None,
    ) -> dict[str, Any]:
        path = args.get("path", "")
        content = args.get("content", "")
        if not path or not content:
            return {"error": "path and content required"}
        try:
            Path(path).write_text(content, encoding="utf-8")
            return {"status": "ok", "path": path}
        except Exception as e:
            return {"error": str(e)}
