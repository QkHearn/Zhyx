"""STT 语音识别 - FunASR（阿里 Paraformer 中文专用）"""

import os
import tempfile
import threading
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

_stream = None
_buffer = []
_voice_history: list[dict] = []
_MAX_HISTORY = 10
_funasr_model = None


def _get_stt_config():
    try:
        import yaml
        cfg = ROOT / "config" / "zhyx.yaml"
        if cfg.exists():
            with open(cfg, encoding="utf-8") as f:
                d = yaml.safe_load(f)
            return d.get("stt") or {}
    except Exception:
        pass
    return {}


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


def _maybe_debug_stt(text: str | None):
    if not _is_debug():
        return
    if text and text.strip():
        print("[STT]", text.strip(), flush=True)
    else:
        print("[STT] (无识别结果)", flush=True)


def _recognize(data: bytes, sample_rate: int = 16000) -> str | None:
    cfg = _get_stt_config()
    return _recognize_funasr(data, sample_rate)


def preload_funasr_model() -> bool:
    """启动时预加载 FunASR 模型。"""
    cfg = _get_stt_config()
    try:
        from funasr import AutoModel
    except ImportError:
        return False
    global _funasr_model
    if _funasr_model is not None:
        return True
    model_id = cfg.get("funasr_model") or "paraformer-zh"
    try:
        print("[STT] 正在预加载 FunASR 模型...", flush=True)
        _funasr_model = AutoModel(
            model=model_id,
            vad_model="fsmn-vad",
            punc_model="ct-punc",
            device="cpu",
            disable_update=True,
        )
        print("[STT] FunASR 模型加载完成", flush=True)
        return True
    except Exception as e:
        print(f"[STT] FunASR 预加载失败: {e}", flush=True)
        return False


def _recognize_funasr(data: bytes, sample_rate: int) -> str | None:
    global _funasr_model
    try:
        from funasr import AutoModel
    except ImportError as e:
        if _is_debug():
            if "torchaudio" in str(e) or "torch" in str(e):
                print("[STT] FunASR 依赖缺失，请执行: pip install torchaudio", flush=True)
            else:
                print("[STT] FunASR 未安装，请执行: pip install funasr modelscope", flush=True)
        return None

    cfg = _get_stt_config()
    model_id = cfg.get("funasr_model") or "paraformer-zh"
    try:
        if _funasr_model is None:
            if _is_debug():
                print("[STT] 正在加载 FunASR 模型（首次较慢）...", flush=True)
            _funasr_model = AutoModel(
                model=model_id,
                vad_model="fsmn-vad",
                punc_model="ct-punc",
                device="cpu",
                disable_update=True,
            )
        model = _funasr_model
    except Exception as e:
        if _is_debug():
            print("[STT] FunASR 模型加载失败:", str(e), flush=True)
        return None

    dur_sec = len(data) / (sample_rate * 2)
    if dur_sec < 0.5 and _is_debug():
        print(f"[STT] 录音过短 ({dur_sec:.1f}s)，请说话至少 1 秒", flush=True)

    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            with wave.open(path, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(sample_rate)
                w.writeframes(data)
            res = model.generate(input=path, batch_size_s=0)
            if res and len(res) > 0:
                text = (res[0].get("text") or "").strip()
                return text or None
            if _is_debug():
                print("[STT] FunASR 识别结果为空（可能是静音或无明显语音）", flush=True)
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass
    except Exception as e:
        if _is_debug():
            print("[STT] FunASR 识别异常:", str(e), flush=True)
    return None


def start_recording() -> bool:
    global _stream, _buffer
    try:
        import sounddevice as sd
    except ImportError:
        return False
    if _stream is not None:
        return True

    _buffer = []

    def _audio_callback(indata, frames, time_info, status):
        _buffer.append(indata.copy())

    try:
        _stream = sd.InputStream(
            samplerate=16000, channels=1, dtype="int16", callback=_audio_callback
        )
        _stream.start()
        return True
    except Exception:
        _stream = None
        return False


def stop_recording_and_speak(callback=None) -> bool:
    global _stream, _buffer
    try:
        import sounddevice as sd
        import numpy as np
    except ImportError:
        if callback:
            callback(None)
        return False
    if _stream is None:
        if callback:
            callback(None)
        return False
    try:
        _stream.stop()
        _stream.close()
    except Exception:
        pass
    _stream = None
    if not _buffer:
        if callback:
            callback(None)
        return True
    try:
        rec = np.concatenate(_buffer, axis=0)
        data = rec.tobytes()
    except Exception:
        if callback:
            callback(None)
        _buffer = []
        return True
    _buffer = []

    text = _recognize(data, 16000)
    _maybe_debug_stt(text)
    if not text or not text.strip():
        if callback:
            callback(None)
        return True
    user_text = text.strip()
    if callback:
        callback(user_text)
    else:
        def _query_and_speak():
            import asyncio
            from core.chat import chat_with_mcp_tools
            from voice.tts import speak_async
            global _voice_history
            try:
                reply = asyncio.run(chat_with_mcp_tools(
                    user_text, history=_voice_history.copy(), on_speak=speak_async
                ))
                if reply and reply.strip():
                    _voice_history.append({"role": "user", "content": user_text})
                    _voice_history.append({"role": "assistant", "content": reply.strip()})
                    if len(_voice_history) > _MAX_HISTORY:
                        _voice_history = _voice_history[-_MAX_HISTORY:]
                elif not reply or not reply.strip():
                    asyncio.run(speak_async("抱歉，我没有理解你的问题。"))
            except Exception as e:
                import traceback
                print("[错误]", str(e), flush=True)
                traceback.print_exc()
                asyncio.run(speak_async(f"出错了：{e}" if str(e) else "请求大模型失败，请检查服务是否开启。"))

        threading.Thread(target=_query_and_speak, daemon=True).start()
    return True


def is_recording() -> bool:
    return _stream is not None


def listen_and_speak(callback=None):
    user_text = [""]

    def _query_and_speak():
        import asyncio
        from core.chat import chat_with_mcp_tools
        from voice.tts import speak_async
        global _voice_history
        try:
            reply = asyncio.run(chat_with_mcp_tools(
                user_text[0], history=_voice_history.copy(), on_speak=speak_async
            ))
            if reply and reply.strip():
                _voice_history.append({"role": "user", "content": user_text[0]})
                _voice_history.append({"role": "assistant", "content": reply.strip()})
                if len(_voice_history) > _MAX_HISTORY:
                    _voice_history = _voice_history[-_MAX_HISTORY:]
            elif not reply or not reply.strip():
                asyncio.run(speak_async("抱歉，我没有理解你的问题。"))
        except Exception as e:
            import traceback
            print("[错误]", str(e), flush=True)
            traceback.print_exc()
            asyncio.run(speak_async(f"出错了：{e}" if str(e) else "请求大模型失败，请检查服务是否开启。"))

    def _run():
        text = _listen_impl()
        _maybe_debug_stt(text)
        if not text or not text.strip():
            if callback:
                callback(None)
            return
        user_text[0] = text.strip()
        if callback:
            callback(user_text[0])
        else:
            threading.Thread(target=_query_and_speak, daemon=True).start()

    user_text = ""
    threading.Thread(target=_run, daemon=True).start()


def _listen_impl() -> str | None:
    try:
        import sounddevice as sd
        import numpy as np
    except ImportError:
        return None
    fs = 16000
    duration = 5
    try:
        rec = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype="int16")
        sd.wait()
    except Exception:
        return None
    data = rec.tobytes()
    return _recognize(data, fs)


def listen_sync() -> str | None:
    """同步录音识别，返回文字，失败返回 None。会阻塞约 5 秒。"""
    return _listen_impl()
