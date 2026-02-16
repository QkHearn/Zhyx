"""FastAPI 应用"""

from fastapi import FastAPI
from pydantic import BaseModel

from core.chat import chat, run_skill
from core.routing import get_mcp
from skills import get_registry

app = FastAPI(title="知式 Zhyx", description="Local-first Digital Human")


@app.on_event("startup")
async def startup():
    get_mcp().scan_and_register_skills()
    try:
        from mcp_client.client import init_global_mcp_session
        await init_global_mcp_session()
    except Exception as e:
        print(f"[MCP] 启动时连接失败: {e}", flush=True)


class ChatIn(BaseModel):
    message: str


class SkillIn(BaseModel):
    name: str
    args: dict = {}


@app.post("/chat")
async def api_chat(body: ChatIn):
    return {"reply": await chat(body.message)}


@app.post("/skill")
async def api_skill(body: SkillIn):
    return run_skill(body.name, body.args)


@app.get("/skills")
async def api_skills():
    return [{"name": s.name, "description": s.description} for s in get_registry().list_all()]


@app.post("/mcp/reload")
async def api_mcp_reload():
    """重新加载 MCP 服务器配置，下次对话使用新配置（动态更新）"""
    try:
        from mcp_client.client import reload_global_mcp_session
        reload_global_mcp_session()
        return {"ok": True, "message": "MCP 配置已失效，下次对话将按新配置重连"}
    except ImportError:
        return {"ok": False, "message": "mcp_client 未就绪"}
