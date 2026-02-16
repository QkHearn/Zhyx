"""ChatSkill - 多轮对话"""

import asyncio
from typing import Any, Callable

from skills.base import Skill
from core.chat import chat


class ChatSkill(Skill):
    def __init__(self, config: dict | None = None):
        cfg = config or {}
        super().__init__(
            name=cfg.get("name", "ChatSkill"),
            description=cfg.get("description", "多轮上下文对话"),
            permissions=cfg.get("permissions", []),
            config=cfg,
        )

    def run(
        self,
        args: dict[str, Any],
        tools: Callable[[str, dict], dict] | None = None,
    ) -> dict[str, Any]:
        message = args.get("message", "")
        history = args.get("history", [])
        try:
            reply = asyncio.run(chat(message, history))
            return {"reply": reply}
        except Exception as e:
            return {"error": str(e)}
