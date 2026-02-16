"""Routing - Skills 注册"""

import logging


class MCPManager:
    _instance: "MCPManager | None" = None

    def __new__(cls) -> "MCPManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self._logger = logging.getLogger("zhyx.mcp")

    def scan_and_register_skills(self) -> int:
        from skills import get_registry
        from skills.chat import ChatSkill
        from skills.file_reader import FileReader
        from skills.file_writer import FileWriter
        from skills.task_planner import TaskPlanner

        reg = get_registry()
        for cls in [ChatSkill, FileReader, FileWriter, TaskPlanner]:
            reg.register(cls())
        return len(reg.list_all())


_mcp: "MCPManager | None" = None


def get_mcp() -> "MCPManager":
    global _mcp
    if _mcp is None:
        _mcp = MCPManager()
    return _mcp
