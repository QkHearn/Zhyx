"""TaskPlanner - 任务拆解"""

from typing import Any, Callable

from skills.base import Skill


class TaskPlanner(Skill):
    def __init__(self, config: dict | None = None):
        cfg = config or {}
        super().__init__(
            name=cfg.get("name", "TaskPlanner"),
            description=cfg.get("description", "任务拆解与自动执行"),
            permissions=cfg.get("permissions", []),
            config=cfg,
        )

    def run(
        self,
        args: dict[str, Any],
        tools: Callable[[str, dict], dict] | None = None,
    ) -> dict[str, Any]:
        task = args.get("task", "")
        if not task:
            return {"error": "task required"}
        return {"status": "ok", "task": task, "steps": [{"action": "chat", "args": {"message": task}}]}
