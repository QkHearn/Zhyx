"""Core - LLM 对话 + 工具调度"""

import httpx
import json
from pathlib import Path
from typing import AsyncIterator, Callable

ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_LLM_URL = "http://localhost:11434"
_DEFAULT_LLM_MODEL = "qwen2.5:latest"
_tools: dict[str, Callable[[dict], dict]] = {}


def _is_debug() -> bool:
    try:
        import yaml
        cfg = ROOT / "config" / "zhyx.yaml"
        if cfg.exists():
            with open(cfg, encoding="utf-8") as f:
                d = yaml.safe_load(f) or {}
            return bool(d.get("debug", False))
    except Exception:
        pass
    return False


def _read_reasoning_enabled() -> bool:
    try:
        import yaml
        cfg = ROOT / "config" / "zhyx.yaml"
        if cfg.exists():
            with open(cfg, encoding="utf-8") as f:
                d = yaml.safe_load(f) or {}
            return bool((d.get("tts") or {}).get("read_reasoning", False))
    except Exception:
        pass
    return False


def _get_llm_config() -> dict:
    import os
    d = {}
    try:
        import yaml
        cfg = ROOT / "config" / "zhyx.yaml"
        if cfg.exists():
            with open(cfg, encoding="utf-8") as f:
                d = (yaml.safe_load(f) or {}).get("llm") or {}
    except Exception:
        pass
    api_key = os.getenv("ZHYX_LLM_API_KEY") or d.get("api_key") or ""
    url = os.getenv("ZHYX_LLM_URL") or d.get("url") or _DEFAULT_LLM_URL
    fmt = d.get("api_format") or ""
    if not fmt and (api_key or "open.bigmodel.cn" in url or "openai" in url.lower()):
        fmt = "openai"
    if not fmt:
        fmt = "ollama"
    return {
        "url": url.strip().rstrip("/"),
        "model": os.getenv("ZHYX_LLM_MODEL") or d.get("model") or _DEFAULT_LLM_MODEL,
        "api_key": api_key.strip() if api_key else "",
        "stream": d.get("stream", True),
        "api_format": fmt,
        "system": d.get("system") or "",
    }


def _build_messages(
    history: list[dict] | None,
    user_message: dict,
    extra_system: str | None = None,
) -> list[dict]:
    cfg = _get_llm_config()
    sys_raw = (cfg.get("system") or "").strip()
    system_content = ""
    if sys_raw:
        p = ROOT / sys_raw
        if p.exists() and p.is_file():
            try:
                system_content = p.read_text(encoding="utf-8").strip()
            except Exception:
                system_content = sys_raw
        else:
            system_content = sys_raw
    if extra_system and extra_system.strip():
        system_content = (system_content + "\n\n" + extra_system.strip()).strip()
    msgs = list(history or [])
    if system_content:
        msgs = [{"role": "system", "content": system_content}] + msgs
    return msgs + [user_message]


def _read_file(args: dict) -> dict:
    path = args.get("path", "")
    try:
        return {"content": Path(path).read_text(encoding="utf-8", errors="replace")}
    except Exception as e:
        return {"error": str(e)}


def register_tool(name: str, fn: Callable[[dict], dict]) -> None:
    _tools[name] = fn


register_tool("read_file", _read_file)


def call_tool(name: str, args: dict) -> dict:
    if name not in _tools:
        return {"error": f"tool not found: {name}"}
    return _tools[name](args)


def tools_runner() -> Callable[[str, dict], dict]:
    return lambda name, args: call_tool(name, args)


def _llm_headers(cfg: dict) -> dict:
    h = {"Content-Type": "application/json"}
    if cfg.get("api_key"):
        h["Authorization"] = f"Bearer {cfg['api_key']}"
    return h


def _chat_url(cfg: dict) -> str:
    if cfg.get("api_format") == "openai":
        base = cfg["url"]
        return f"{base}/chat/completions" if not base.endswith("completions") else base
    return f"{cfg['url']}/api/chat"


def _parse_ollama_chunk(data: dict) -> str:
    chunk = data.get("response", "")
    if data.get("done") and data.get("message"):
        return data["message"].get("content", "") or chunk
    return chunk


def _parse_openai_chunk(data: dict) -> str:
    try:
        choices = data.get("choices") or []
        if choices:
            delta = choices[0].get("delta") or {}
            return delta.get("content") or ""
    except (IndexError, KeyError, TypeError):
        pass
    return ""


async def chat(message: str, history: list[dict] | None = None, stream: bool | None = None) -> str:
    cfg = _get_llm_config()
    url = _chat_url(cfg)
    use_stream = stream if stream is not None else cfg.get("stream", True)
    payload = {
        "model": cfg["model"],
        "messages": _build_messages(history, {"role": "user", "content": message}),
        "stream": use_stream,
    }
    headers = _llm_headers(cfg)
    is_openai = cfg.get("api_format") == "openai"

    async with httpx.AsyncClient() as c:
        try:
            if use_stream:
                full = []
                async with c.stream("POST", url, json=payload, headers=headers, timeout=60) as r:
                    if r.status_code >= 400:
                        body = await r.aread()
                        print(f"[LLM 错误] HTTP {r.status_code} {url}", flush=True)
                        print(body.decode("utf-8", errors="replace"), flush=True)
                    r.raise_for_status()
                    async for line in r.aiter_lines():
                        line = (line or "").strip()
                        if not line or (is_openai and line == "data: [DONE]"):
                            continue
                        if is_openai and line.startswith("data: "):
                            line = line[6:]
                        try:
                            data = json.loads(line)
                            chunk = _parse_openai_chunk(data) if is_openai else _parse_ollama_chunk(data)
                            if chunk:
                                full.append(chunk)
                            elif not is_openai and data.get("done") and data.get("message"):
                                content = data["message"].get("content", "")
                                if content:
                                    result = content
                                    if _is_debug():
                                        print("[LLM]", result, flush=True)
                                    return result
                        except json.JSONDecodeError:
                            pass
                result = "".join(full) if full else ""
                if _is_debug() and result:
                    print("[LLM]", result, flush=True)
                return result
            r = await c.post(url, json=payload, headers=headers, timeout=60)
            if r.status_code >= 400:
                print(f"[LLM 错误] HTTP {r.status_code} {url}", flush=True)
                print(r.text, flush=True)
            r.raise_for_status()
            data = r.json()
            if is_openai:
                choices = data.get("choices") or []
                result = (choices[0].get("message") or {}).get("content", "") if choices else ""
            else:
                result = data.get("message", {}).get("content", "")
            if _is_debug() and result:
                print("[LLM]", result, flush=True)
            return result
        except httpx.HTTPStatusError as e:
            print(f"[LLM 错误] HTTP {e.response.status_code} {url}", flush=True)
            print(e.response.text, flush=True)
            raise
        except Exception as e:
            import traceback
            print(f"[LLM 错误] {e}", flush=True)
            traceback.print_exc()
            raise


async def chat_stream(message: str, history: list[dict] | None = None) -> AsyncIterator[str]:
    cfg = _get_llm_config()
    url = _chat_url(cfg)
    payload = {
        "model": cfg["model"],
        "messages": _build_messages(history, {"role": "user", "content": message}),
        "stream": True,
    }
    headers = _llm_headers(cfg)
    full_reply = []
    is_openai = cfg.get("api_format") == "openai"
    try:
        async with httpx.AsyncClient() as c:
            async with c.stream("POST", url, json=payload, headers=headers, timeout=60) as r:
                if r.status_code >= 400:
                    body = await r.aread()
                    print(f"[LLM 错误] HTTP {r.status_code} {url}", flush=True)
                    print(body.decode("utf-8", errors="replace"), flush=True)
                r.raise_for_status()
                async for line in r.aiter_lines():
                    line = (line or "").strip()
                    if not line or (is_openai and line == "data: [DONE]"):
                        continue
                    if is_openai and line.startswith("data: "):
                        line = line[6:]
                    try:
                        data = json.loads(line)
                        chunk = _parse_openai_chunk(data) if is_openai else data.get("response", "")
                        if chunk:
                            full_reply.append(chunk)
                            if _is_debug():
                                print(chunk, end="", flush=True)
                            yield chunk
                    except json.JSONDecodeError:
                        pass
        if _is_debug() and full_reply:
            print(flush=True)
    except httpx.HTTPStatusError as e:
        print(f"[LLM 错误] HTTP {e.response.status_code} {url}", flush=True)
        print(e.response.text, flush=True)
        raise
    except Exception as e:
        import traceback
        print(f"[LLM 错误] {e}", flush=True)
        traceback.print_exc()
        raise


async def chat_with_mcp_tools(
    message: str,
    history: list[dict] | None = None,
    on_speak=None,
) -> str:
    async def _speak(t: str) -> None:
        if on_speak and t and t.strip():
            text = t.strip()
            if _is_debug():
                print(f"[TTS] 请求朗读: {text[:80]}{'...' if len(text) > 80 else ''}", flush=True)
            import asyncio
            r = on_speak(text)
            if asyncio.iscoroutine(r):
                await r
            else:
                await asyncio.get_event_loop().run_in_executor(None, lambda: on_speak(text))

    try:
        from mcp_client.client import mcp_session as _mcp_ctx
        from voice.tts import mark_agent_round_done
    except ImportError:
        reply = await chat(message, history)
        if reply:
            await _speak(reply)
        try:
            from voice.tts import mark_agent_round_done
            mark_agent_round_done()
        except ImportError:
            pass
        return reply or ""

    async with _mcp_ctx() as sess:
        mcp_tools = sess.get_openai_tools()
        if not mcp_tools:
            reply = await chat(message, history)
            if reply:
                await _speak(reply)
            try:
                from voice.tts import mark_agent_round_done
                mark_agent_round_done()
            except ImportError:
                pass
            return reply or ""

        cfg = _get_llm_config()
        url = _chat_url(cfg)
        headers = _llm_headers(cfg)
        extra_system = None
        try:
            from agent_skills.loader import get_agent_skill_context
            extra_system = get_agent_skill_context()
        except ImportError:
            pass
        messages: list[dict] = _build_messages(
            history, {"role": "user", "content": message}, extra_system=extra_system
        )
        max_rounds = 10

        async with httpx.AsyncClient() as c:
            for _ in range(max_rounds):
                payload = {
                    "model": cfg["model"],
                    "messages": messages,
                    "stream": False,
                    "tools": mcp_tools,
                    "tool_choice": "auto",
                }
                r = await c.post(url, json=payload, headers=headers, timeout=120)
                if r.status_code >= 400:
                    print(f"[LLM 错误] HTTP {r.status_code}", flush=True)
                    print(r.text[:500], flush=True)
                    r.raise_for_status()
                data = r.json()
                choice = (data.get("choices") or [{}])[0]
                msg = choice.get("message") or {}
                content = (msg.get("content") or "").strip()
                reasoning = (msg.get("reasoning_content") or "").strip()
                tool_calls = msg.get("tool_calls") or []

                if _read_reasoning_enabled() and reasoning:
                    await _speak(reasoning)
                if content and not tool_calls:
                    await _speak(content)
                    if _is_debug():
                        print("[LLM]", content, flush=True)
                    try:
                        from voice.tts import mark_agent_round_done
                        mark_agent_round_done()
                    except ImportError:
                        pass
                    return content

                if not tool_calls:
                    try:
                        from voice.tts import mark_agent_round_done
                        mark_agent_round_done()
                    except ImportError:
                        pass
                    return content or ""

                messages.append(msg)
                for tc in tool_calls:
                    fn = (tc.get("function") or {})
                    name = fn.get("name") or ""
                    args_str = fn.get("arguments") or "{}"
                    try:
                        args = json.loads(args_str)
                    except json.JSONDecodeError:
                        args = {}
                    if _is_debug():
                        print(f"[工具] {name}({json.dumps(args, ensure_ascii=False)[:80]}...)", flush=True)
                    result = await sess.call_tool(name, args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id") or "",
                        "content": result,
                    })

    try:
        from voice.tts import mark_agent_round_done
        mark_agent_round_done()
    except ImportError:
        pass
    return ""


def run_skill(name: str, args: dict, tools=None) -> dict:
    from skills import get_registry
    reg = get_registry()
    skill = reg.get(name)
    if not skill:
        return {"error": f"skill not found: {name}"}
    _tools = tools or tools_runner()
    return skill.run(args, tools=_tools)
