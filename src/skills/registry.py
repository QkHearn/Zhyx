"""Skill 注册与发现"""

from typing import Callable

from skills.base import Skill


class SkillRegistry:
    _instance: "SkillRegistry | None" = None

    def __new__(cls) -> "SkillRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills: dict[str, Skill] = {}
        return cls._instance

    def register(self, skill: Skill) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def list_all(self) -> list[Skill]:
        return list(self._skills.values())

    def run(self, name: str, args: dict, tools: Callable[[str, dict], dict] | None = None) -> dict:
        skill = self.get(name)
        if not skill:
            return {"error": f"skill not found: {name}"}
        return skill.run(args, tools=tools)

    def clear(self) -> None:
        self._skills.clear()


_registry: SkillRegistry | None = None


def get_registry() -> SkillRegistry:
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry
