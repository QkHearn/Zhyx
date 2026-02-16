"""TTS 模块 - 文本转语音，供形象口型同步"""

import asyncio
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TTS_DIR = ROOT / "assets" / "avatar" / "tts"
AUDIO_FILE = TTS_DIR / "latest.mp3"

_speak_queue: deque[str] = deque()
_agent_round_done: bool = False
_pending_clear: bool = False


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


def _get_voice() -> str:
    try:
        import yaml
        cfg = ROOT / "config" / "zhyx.yaml"
        if cfg.exists():
            with open(cfg, encoding="utf-8") as f:
                d = yaml.safe_load(f)
            v = (d.get("tts") or {}).get("voice", "zh-CN-XiaoxiaoNeural")
            return str(v).strip() or "zh-CN-XiaoxiaoNeural"
    except Exception:
        pass
    return "zh-CN-XiaoxiaoNeural"


def _get_rate() -> str:
    try:
        import yaml
        cfg = ROOT / "config" / "zhyx.yaml"
        if cfg.exists():
            with open(cfg, encoding="utf-8") as f:
                d = yaml.safe_load(f)
            r = (d.get("tts") or {}).get("rate")
            if r is None:
                return "+0%"
            s = str(r).strip()
            if not s or s == "0%":
                return "+0%"
            if not s.endswith("%"):
                s = s + "%"
            if s[0] not in ("+", "-"):
                s = "+" + s
            return s
    except Exception:
        pass
    return "+0%"


def _ensure_dir():
    TTS_DIR.mkdir(parents=True, exist_ok=True)


_MAX_CHARS_PER_CHUNK = 400


def _split_for_tts(text: str) -> list[str]:
    import re
    s = text.strip()
    if not s or len(s) < 2:
        return []
    if len(s) <= _MAX_CHARS_PER_CHUNK:
        return [s]
    chunks = []
    parts = re.split(r'(?<=[。！？?!.\n])', s)
    buf = ""
    for p in parts:
        if len(buf) + len(p) <= _MAX_CHARS_PER_CHUNK:
            buf += p
        else:
            if buf.strip():
                chunks.append(buf.strip())
            buf = p
            while len(buf) > _MAX_CHARS_PER_CHUNK:
                chunks.append(buf[:_MAX_CHARS_PER_CHUNK].strip())
                buf = buf[_MAX_CHARS_PER_CHUNK:]
    if buf.strip():
        chunks.append(buf.strip())
    return [c for c in chunks if len(c) >= 2]


def _clean_tts_text(text: str) -> str:
    import re
    s = str(text).strip()
    s = re.sub(r"[\u2600-\u26FF\u2700-\u27BF\U0001F300-\U0001F9FF]+", "", s)
    s = re.sub(r"\*+", "", s)
    s = re.sub(r"`+", "", s)
    s = re.sub(r"#+", "", s)
    s = re.sub(r"_+", "", s)
    s = re.sub(r"~+", "", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"([A-Za-z])\.([A-Za-z])", r"\1点\2", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def push_queue(url: str) -> None:
    _speak_queue.append(url.strip())


def pop_queue() -> str | None:
    if not _speak_queue:
        return None
    try:
        return _speak_queue.popleft()
    except IndexError:
        return None


def mark_agent_round_done() -> None:
    global _agent_round_done
    _agent_round_done = True


def is_agent_round_done() -> bool:
    return _agent_round_done


def clear_tts_dir() -> None:
    global _agent_round_done
    if not TTS_DIR.exists():
        _agent_round_done = False
        return
    try:
        for f in TTS_DIR.glob("*.mp3"):
            f.unlink(missing_ok=True)
    except Exception:
        pass
    _agent_round_done = False


def schedule_clear_on_next_push() -> None:
    global _pending_clear
    _pending_clear = True


async def _speak_one_chunk(text: str, voice: str, rate: str, out_path: Path) -> bool:
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(str(out_path))
        return True
    except Exception as e:
        if "NoAudioReceived" in type(e).__name__ or "no audio" in str(e).lower():
            print(f"[TTS] NoAudioReceived: {text[:50]}...", flush=True)
            fallback = text.replace("Z.ai", "Z点ai").replace("GLM", "G L M")
            if fallback != text:
                try:
                    import edge_tts
                    communicate = edge_tts.Communicate(fallback, voice, rate=rate)
                    await communicate.save(str(out_path))
                    return True
                except Exception:
                    return False
            return False
        raise


async def speak_async(text: str, voice: str | None = None) -> str | None:
    global _pending_clear
    if _pending_clear:
        _pending_clear = False
        clear_tts_dir()
    try:
        import edge_tts
    except ImportError as e:
        print(f"[TTS] 未安装 edge-tts: {e}", flush=True)
        return None
    raw = _clean_tts_text(text)
    if not raw or len(raw) < 2:
        if _is_debug():
            print(f"[TTS] 跳过: 文本过短或为空 (清洗后 {len(raw)} 字)", flush=True)
        return None
    voice = voice or _get_voice()
    rate = _get_rate()
    _ensure_dir()
    import time
    chunks = _split_for_tts(raw)
    last_rel = None
    success_count = 0
    for i, chunk in enumerate(chunks):
        out_path = TTS_DIR / f"seg_{int(time.time()*1000)}_{i:02x}_{id(chunk) & 0xFFFF:04x}.mp3"
        ok = await _speak_one_chunk(chunk, voice, rate, out_path)
        if ok:
            rel = "tts/" + out_path.name
            push_queue(rel)
            last_rel = rel
            success_count += 1
            if _is_debug():
                print(f"[TTS] 入队: {rel} ({len(chunk)} 字)", flush=True)
        else:
            if _is_debug():
                print(f"[TTS] 失败跳过: {chunk[:40]}...", flush=True)
    if success_count == 0 and _is_debug():
        print(f"[TTS] 全部 {len(chunks)} 段均失败，未入队", flush=True)
    return last_rel if success_count > 0 else None


def speak(text: str, voice: str | None = None) -> str | None:
    return asyncio.run(speak_async(text, voice))


def has_pending() -> bool:
    return len(_speak_queue) > 0
