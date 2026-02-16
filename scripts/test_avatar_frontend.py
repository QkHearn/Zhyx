#!/usr/bin/env python3
"""前端测试：仅启动 HTTP 服务 + pywebview，不加载 FunASR/MCP/主应用。"""

import os
import signal
import sys
import threading
import time
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

ROOT = Path(__file__).resolve().parents[1]
AVATAR_DIR = ROOT / "assets" / "avatar"
APP_HTML = AVATAR_DIR / "app.html"

AVATAR_WIDTH = 400
AVATAR_HEIGHT = 600
BALL_WIDTH = 80
BALL_HEIGHT = 96

_port = [0]


def _start_server():
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(AVATAR_DIR), **k)

        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path == "/api/speak" or self.path.startswith("/api/speak?"):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b'{"url":null,"agent_done":false}')
                return
            super().do_GET()

        def do_POST(self):
            if self.path in ("/api/playback-done", "/api/playback-segment-done"):
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                return
            self.send_response(404)
            self.end_headers()

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    _port[0] = httpd.server_port
    httpd.serve_forever()


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


def main():
    if sys.platform != "darwin":
        print("形象窗口仅支持 macOS")
        return 1

    def _on_sigint(*_):
        os._exit(0)

    signal.signal(signal.SIGINT, _on_sigint)
    signal.signal(signal.SIGTERM, _on_sigint)

    try:
        import webview
    except ImportError:
        print("请安装: pip install pywebview")
        return 1

    if not APP_HTML.exists():
        print(f"Avatar HTML not found: {APP_HTML}")
        return 1

    threading.Thread(target=_start_server, daemon=True).start()
    time.sleep(0.3)

    screen_w, screen_h = _screen_size()
    ball_x = screen_w - BALL_WIDTH - 4
    ball_y = max(0, (screen_h - BALL_HEIGHT) // 2)
    full_x = screen_w - AVATAR_WIDTH - 4
    full_y = max(0, (screen_h - AVATAR_HEIGHT) // 2)

    _win_ref = [None]

    def make_api():
        def do_expand():
            w = _win_ref[0]
            if w:
                w.resize(AVATAR_WIDTH, AVATAR_HEIGHT)
                w.move(int(full_x), full_y)
                w.evaluate_js("if(typeof showFull==='function')showFull()")

        def do_collapse():
            w = _win_ref[0]
            if w:
                w.resize(BALL_WIDTH, BALL_HEIGHT)
                w.move(int(ball_x), ball_y)
                w.evaluate_js("if(typeof showBall==='function')showBall()")

        class Api:
            def expand(self):
                do_expand()

            def collapse(self):
                do_collapse()

            def start_listening(self):
                pass

            def stop_listening(self):
                pass

            def switch_model(self):
                w = _win_ref[0]
                if w:
                    w.evaluate_js("if(typeof switchToNextModel==='function')switchToNextModel()")

            def quit(self):
                w = _win_ref[0]
                if w:
                    w.destroy()
                os._exit(0)

        return Api()

    url = f"http://127.0.0.1:{_port[0]}/app.html?model=hijiki"
    win = webview.create_window(
        "知式 - 前端测试",
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

    print("前端测试：点击小球展开/折叠，换角色、退出可用。无语音/TTS。")
    webview.start(debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
