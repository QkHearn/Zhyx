"""Core - LLM + 工具调度 + 路由"""
from core.chat import chat, chat_stream, chat_with_mcp_tools, run_skill, register_tool, call_tool, tools_runner
from core.routing import MCPManager, get_mcp

__all__ = ["chat", "chat_stream", "chat_with_mcp_tools", "run_skill", "register_tool", "call_tool", "tools_runner", "MCPManager", "get_mcp"]
