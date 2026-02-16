"""Mac 专用：小球常驻，点击切换显示/隐藏 Live2D"""

import os
import signal
import sys
import threading
import time
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

ROOT = Path(__file__).resolve().parents[2]
AVATAR_DIR = ROOT / "assets" / "avatar"
APP_HTML = AVATAR_DIR / "app.html"

AVATAR_WIDTH = 400
AVATAR_HEIGHT = 600
# 收起：宽 80 容纳按钮区域，高 96
BALL_WIDTH = 80
BALL_HEIGHT = 96

_port = [0]
_collapsed = [True]


def _start_server():
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(AVATAR_DIR), **k)

        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path == "/api/speak" or self.path.startswith("/api/speak?"):
                self._handle_speak()
                return
            super().do_GET()

        def do_POST(self):
            if self.path == "/api/playback-done" or self.path.startswith("/api/playback-done?"):
                self._handle_playback_done()
                return
            if self.path == "/api/playback-segment-done" or self.path.startswith("/api/playback-segment-done?"):
                self._handle_playback_segment_done()
                return
            self.send_response(404)
            self.end_headers()

        def _handle_playback_done(self):
            try:
                from voice.tts import schedule_clear_on_next_push
                schedule_clear_on_next_push()
            except Exception:
                pass
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

        def _handle_playback_segment_done(self):
            try:
                import json
                n = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(n).decode("utf-8") if n else "{}"
                data = json.loads(body) if body.strip() else {}
                url = (data.get("url") or "").strip()
                if url:
                    try:
                        from voice.tts import _is_debug
                        if _is_debug():
                            print(f"[TTS] 已播放: {url}", flush=True)
                    except Exception:
                        pass
            except Exception:
                pass
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

        def _handle_speak(self):
            url = None
            agent_done = False
            try:
                from voice.tts import pop_queue, is_agent_round_done, _is_debug
                url = pop_queue()
                if url and _is_debug():
                    print(f"[TTS] 取出供播放: {url}", flush=True)
                if not url:
                    agent_done = is_agent_round_done()
            except Exception:
                pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            if url:
                body = ('{"url":"' + url.replace("\\", "\\\\").replace('"', '\\"') + '"}').encode()
            else:
                body = ('{"url":null,"agent_done":' + ("true" if agent_done else "false") + "}").encode()
            self.wfile.write(body)

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    _port[0] = httpd.server_port
    httpd.serve_forever()


def _get_model():
    try:
        import yaml
        cfg = ROOT / "config" / "zhyx.yaml"
        if cfg.exists():
            with open(cfg, encoding="utf-8") as f:
                d = yaml.safe_load(f)
            m = (d.get("avatar") or {}).get("model", "hijiki")
            return str(m).strip().lower() or "hijiki"
    except Exception:
        pass
    return "hijiki"


def _screen_size():
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        w, h = root.winfo_screenwidth(), root.winfo_screenheight()
        root.destroy()
        return w, h
    except Exception:
        return 1920, 1080




def run_avatar():
    if sys.platform != "darwin":
        print("形象窗口仅支持 macOS")
        return
    # pywebview 在 Mac 上阻塞 Cocoa 事件循环，Ctrl+C 无法正常终止，需强制退出
    def _on_sigint(*_):
        os._exit(0)

    signal.signal(signal.SIGINT, _on_sigint)
    signal.signal(signal.SIGTERM, _on_sigint)
    try:
        import webview
    except ImportError:
        print("请安装: pip install pywebview")
        return
    if not APP_HTML.exists():
        print(f"Avatar HTML not found: {APP_HTML}")
        return

    (AVATAR_DIR / "tts").mkdir(exist_ok=True)
    threading.Thread(target=_start_server, daemon=True).start()
    time.sleep(0.3)
    # 启动时预加载 FunASR 模型（若配置为 funasr），避免首次对话才加载
    try:
        from voice.stt import preload_funasr_model
        preload_funasr_model()
    except Exception as e:
        print(f"[STT] 预加载失败: {e}", flush=True)
    # 启动时连接 MCP 服务器（每服务器独立线程，避免 anyio cancel scope 错误）
    try:
        import asyncio
        from mcp_client.client import init_global_mcp_session
        asyncio.run(init_global_mcp_session())
    except Exception as e:
        print(f"[MCP] 启动时连接失败: {e}", flush=True)
    model = _get_model()
    url = f"http://127.0.0.1:{_port[0]}/app.html" + (f"?model={model}" if model else "")

    screen_w, screen_h = _screen_size()
    ball_x = screen_w - BALL_WIDTH - 4
    ball_y = max(0, (screen_h - BALL_HEIGHT) // 2)
    full_x = screen_w - AVATAR_WIDTH - 4
    full_y = max(0, (screen_h - AVATAR_HEIGHT) // 2)

    _win_ref = [None]

    def make_api():
        def do_expand():
            _collapsed[0] = False
            try:
                w = _win_ref[0]
                if w:
                    w.resize(AVATAR_WIDTH, AVATAR_HEIGHT)
                    w.move(int(full_x), full_y)
                    w.evaluate_js("if(typeof showFull==='function')showFull()")
            except Exception:
                pass

        def do_collapse():
            _collapsed[0] = True
            try:
                w = _win_ref[0]
                if w:
                    w.resize(BALL_WIDTH, BALL_HEIGHT)
                    w.move(int(ball_x), ball_y)
                    w.evaluate_js("if(typeof showBall==='function')showBall()")
            except Exception:
                pass

        def do_speak(audio_url):
            import json
            try:
                w = _win_ref[0]
                if w:
                    w.evaluate_js("if(typeof speakToAvatar==='function')speakToAvatar(" + json.dumps(str(audio_url)) + ")")
            except Exception:
                pass

        def do_stop_speak():
            try:
                w = _win_ref[0]
                if w:
                    w.evaluate_js("if(typeof stopAvatarSpeaking==='function')stopAvatarSpeaking()")
            except Exception:
                pass

        def start_listening():
            try:
                from voice.stt import start_recording
                start_recording()
            except Exception:
                pass

        def stop_listening():
            try:
                from voice.stt import stop_recording_and_speak
                stop_recording_and_speak()
            except Exception:
                pass

        def do_switch_model():
            try:
                w = _win_ref[0]
                if w:
                    w.evaluate_js(
                        "if(typeof switchToNextModel==='function')switchToNextModel()"
                    )
            except Exception:
                pass

        def do_quit():
            try:
                w = _win_ref[0]
                if w:
                    w.destroy()
            except Exception:
                pass
            # 先关闭 MCP 会话（停止事件循环）
            try:
                from mcp_client.client import reload_global_mcp_session
                reload_global_mcp_session()
            except Exception:
                pass
            # 终止直接子进程（npx/uvx 等），避免孤儿进程累积
            try:
                import subprocess
                subprocess.run(
                    ["pkill", "-P", str(os.getpid())],
                    capture_output=True,
                    timeout=2,
                )
            except Exception:
                pass
            # 强制退出，避免 Python 等待线程导致挂起
            os._exit(0)

        class Api:
            def expand(self):
                do_expand()

            def collapse(self):
                do_collapse()

            def speak(self, audio_url):
                do_speak(audio_url)

            def stop_speaking(self):
                do_stop_speak()

            def start_listening(self):
                start_listening()

            def stop_listening(self):
                stop_listening()

            def switch_model(self):
                do_switch_model()

            def quit(self):
                do_quit()

        return Api()

    win = webview.create_window(
        "知式",
        url,
        width=BALL_WIDTH,
        height=BALL_HEIGHT,
        x=int(ball_x),
        y=ball_y,
        frameless=True,
        transparent=True,
        resizable=False,
        on_top=True,
        easy_drag=False,
        js_api=make_api(),
    )
    _win_ref[0] = win

    webview.start(debug=False)


if __name__ == "__main__":
    run_avatar()
