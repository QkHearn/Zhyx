"""Skill 基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Skill(ABC):
    name: str
    description: str
    permissions: list[str] = field(default_factory=list)
    config: dict = field(default_factory=dict)

    @abstractmethod
    def run(
        self,
        args: dict[str, Any],
        tools: Callable[[str, dict], dict] | None = None,
    ) -> dict[str, Any]:
        ...

    async def execute(self, context: dict) -> dict:
        args = context.get("args", {})
        tools = context.get("tools")
        return self.run(args, tools=tools)

    def to_tool_schema(self) -> dict:
        return {"name": self.name, "description": self.description, "parameters": {"type": "object", "properties": {}}}


class SkillBase(Skill):
    pass
