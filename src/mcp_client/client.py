"""MCP 客户端 - 连接 MCP 服务器，获取并调用工具

每个 MCP 服务器在独立线程+事件循环中连接，避免 anyio cancel scope 跨任务错误。
支持动态更新：每次使用前检测 mcp.servers 配置变更，若变化则自动重连。
"""

import asyncio
import hashlib
import json
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

ROOT = Path(__file__).resolve().parents[2]

# MCP 子进程 stderr 重定向到此，静默其 INFO 等日志
_DEVNULL = open(os.devnull, "w", encoding="utf-8")

# 全局会话，启动时连接，供后续复用
_global_session: "MCPToolSession | None" = None
# 创建会话时的配置指纹，用于检测变更
_config_hash_at_session: str | None = None


def _get_mcp_config() -> list[dict]:
    """从 config/zhyx.yaml 读取 mcp.servers"""
    try:
        import yaml
        cfg = ROOT / "config" / "zhyx.yaml"
        if cfg.exists():
            with open(cfg, encoding="utf-8") as f:
                d = yaml.safe_load(f) or {}
            servers = (d.get("mcp") or {}).get("servers") or []
            return servers if isinstance(servers, list) else []
    except Exception:
        pass
    return []


def _mcp_config_hash() -> str:
    """返回 mcp.servers 的指纹，用于检测配置变更"""
    servers = _get_mcp_config()
    raw = json.dumps(servers, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def reload_global_mcp_session() -> None:
    """关闭并清空全局 MCP 会话，下次使用时会按新配置重连。用于动态更新 MCP 工具。"""
    global _global_session, _config_hash_at_session
    if _global_session is not None:
        _global_session.close_sync()
        _global_session = None
        _config_hash_at_session = None


def _mcp_tool_to_openai(t: Any) -> dict:
    """将 MCP 工具转为 OpenAI function 格式"""
    if isinstance(t, dict):
        name = t.get("name") or ""
        desc = t.get("description") or ""
        schema = t.get("inputSchema") or {"type": "object", "properties": {}}
    else:
        name = getattr(t, "name", "") or ""
        desc = getattr(t, "description", "") or ""
        schema = getattr(t, "inputSchema", None) or {"type": "object", "properties": {}}
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": schema,
        },
    }


def _connect_one_server_in_thread(
    idx: int,
    srv: dict,
    tools_out: list,
    tool_to_idx: dict,
    sessions_out: list,
    loop_ref: list,
    lock: threading.Lock,
    done_events: list,
) -> None:
    """在独立线程中连接单个 MCP 服务器，拥有自己的事件循环，隔离 anyio 状态"""
    cmd = srv.get("command") or srv.get("cmd")
    args = srv.get("args") or []
    name_srv = srv.get("name") or cmd
    if not cmd:
        return
    print(f"[MCP] 连接 {name_srv}...", flush=True)

    async def _connect() -> None:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            return  # 由外层根据 sessions_out 判断并打印
        env_overrides = srv.get("env") or {}
        # 空字符串表示从 os.environ 读取（含 .env 加载的变量）
        merged = dict(os.environ)
        for k, v in env_overrides.items():
            val = os.environ.get(k, "") if (v == "" or v is None) else str(v)
            if val:
                merged[k] = val
        params = StdioServerParameters(
            command=str(cmd),
            args=[str(a) for a in args],
            env=merged if env_overrides else None,
        )
        # errlog=_DEVNULL 静默 MCP 子进程的 INFO 等日志，避免终端刷屏
        stdio_ctx = stdio_client(params, errlog=_DEVNULL)
        read, write = await stdio_ctx.__aenter__()
        sess_ctx = ClientSession(read, write)
        sess = await sess_ctx.__aenter__()
        await sess.initialize()
        tools_result = await sess.list_tools()
        tools_list = getattr(tools_result, "tools", None) or []
        with lock:
            for t in tools_list:
                name = getattr(t, "name", None) or (t.get("name") if isinstance(t, dict) else "")
                if name:
                    tools_out.append(_mcp_tool_to_openai(t))
                    tool_to_idx[name] = idx
            sessions_out[idx] = {"sess": sess, "sess_ctx": sess_ctx, "stdio_ctx": stdio_ctx}

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop_ref[idx] = loop
    try:
        loop.run_until_complete(_connect())
        done_events[idx].set()
        if sessions_out[idx] is not None:
            print(f"[MCP]   ✓ {name_srv} 已连接", flush=True)
            loop.run_forever()  # 保持 loop 运行，供后续 call_tool 使用
        else:
            try:
                from mcp import ClientSession
            except ImportError:
                print(f"[MCP]   ✗ {name_srv} 需安装 mcp: pip install mcp", flush=True)
            else:
                print(f"[MCP]   ✗ {name_srv} 启动失败", flush=True)
    except Exception as e:
        print(f"[MCP]   ✗ {name_srv} 失败: {e}", flush=True)
    finally:
        done_events[idx].set()


async def init_global_mcp_session() -> "MCPToolSession | None":
    """启动时连接 MCP 服务器，存入全局会话。每服务器独立线程，避免 anyio 跨任务错误。"""
    global _global_session, _config_hash_at_session
    if _global_session is not None:
        return _global_session
    servers = _get_mcp_config()
    if not servers:
        print("[MCP] 未配置 mcp.servers，跳过连接", flush=True)
        return None
    # 预检查：确保 mcp 包可导入（避免所有服务均报「需安装 mcp」却难以定位）
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError as e:
        import sys
        print(f"[MCP] 无法导入 mcp 包: {e}", flush=True)
        print(f"[MCP] Python: {sys.executable}", flush=True)
        print("[MCP] 请在此环境执行: pip install mcp", flush=True)
        return None

    print("[MCP] 正在连接 MCP 服务器（每服务器独立线程）...", flush=True)
    tools_out: list = []
    tool_to_idx: dict = {}
    sessions_out: list = [None] * len(servers)
    loop_ref: list = [None] * len(servers)
    lock = threading.Lock()
    done_events = [threading.Event() for _ in range(len(servers))]
    threads: list[threading.Thread] = []
    for i, srv in enumerate(servers):
        if not (srv.get("command") or srv.get("cmd")):
            done_events[i].set()
            continue
        t = threading.Thread(
            target=_connect_one_server_in_thread,
            args=(i, srv, tools_out, tool_to_idx, sessions_out, loop_ref, lock, done_events),
            daemon=True,
        )
        t.start()
        threads.append(t)
    for ev in done_events:
        ev.wait(timeout=120)
    session = MCPToolSession()
    session._tools = tools_out
    session._tool_to_session = tool_to_idx
    session._server_holders = [None] * len(servers)
    for i in range(len(servers)):
        if sessions_out[i] is not None and loop_ref[i] is not None:
            h = sessions_out[i]
            session._server_holders[i] = {
                "sess": h["sess"], "sess_ctx": h["sess_ctx"], "stdio_ctx": h["stdio_ctx"],
                "loop": loop_ref[i],
            }
    if not session._tools:
        print("[MCP] 无可用工具，请检查: 1) pip install mcp  2) Node.js 与 npx  3) uv（Office/ModelScope）", flush=True)
        return None
    _global_session = session
    _config_hash_at_session = _mcp_config_hash()
    print(f"[MCP] 连接完成，共 {len(tools_out)} 个工具", flush=True)
    return session


def get_global_mcp_session() -> "MCPToolSession | None":
    """获取已初始化的全局 MCP 会话"""
    return _global_session


@asynccontextmanager
async def mcp_session() -> AsyncIterator["MCPToolSession"]:
    """连接配置的 MCP 服务器，返回工具会话。若配置变更则自动重连（动态更新）。"""
    global _global_session, _config_hash_at_session
    if _global_session is not None and _config_hash_at_session != _mcp_config_hash():
        reload_global_mcp_session()
    if _global_session is not None:
        yield _global_session
        return
    session = await init_global_mcp_session()
    if session is None:
        session = MCPToolSession()
    try:
        yield session
    finally:
        if session is not _global_session:
            session.close_sync()


class MCPToolSession:
    """MCP 工具会话：聚合多个服务器的工具，每个服务器在独立线程的 loop 中"""

    def __init__(self) -> None:
        self._tools: list[dict] = []
        self._tool_to_session: dict[str, int] = {}
        self._server_holders: list[dict] = []

    def close_sync(self) -> None:
        """同步关闭（仅用于非全局的临时会话）"""
        for h in getattr(self, "_server_holders", []) or []:
            if h is None:
                continue
            loop = h.get("loop")
            if loop and loop.is_running():
                loop.call_soon_threadsafe(loop.stop)
        self._server_holders = []
        self._tools = []
        self._tool_to_session = {}

    def get_openai_tools(self) -> list[dict]:
        """返回 OpenAI API 的 tools 格式"""
        return self._tools.copy()

    async def call_tool(self, name: str, arguments: dict) -> str:
        """调用工具，在对应服务器的 loop 中执行"""
        idx = self._tool_to_session.get(name)
        if idx is None:
            return json.dumps({"error": f"工具不存在: {name}"}, ensure_ascii=False)
        if idx >= len(self._server_holders) or self._server_holders[idx] is None:
            return json.dumps({"error": f"服务器 {idx} 不可用"}, ensure_ascii=False)
        holder = self._server_holders[idx]
        loop = holder["loop"]
        sess = holder["sess"]

        def _run():
            coro = sess.call_tool(name, arguments=arguments or {})
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result(timeout=120)

        try:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                result = ex.submit(_run).result(timeout=125)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)
        content = []
        if hasattr(result, "content"):
            for block in (result.content or []):
                text = getattr(block, "text", None) or (block.get("text") if isinstance(block, dict) else "")
                if text:
                    content.append(str(text))
        return "\n".join(content) if content else json.dumps({"result": "ok"}, ensure_ascii=False)
