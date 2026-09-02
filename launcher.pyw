"""桌面 app 启动器 — PyWebView 套壳 Streamlit。

双击桌面快捷方式（pythonw.exe + 这个文件）：
1. 单例锁（防双开）
2. 找空闲端口（默认 8501，被占就 8502/8503...）
3. 立刻显示 splash 窗口（青蓝→靛紫渐变 + Ψ logo + 加载动画）
4. 后台启 Streamlit（不弹 cmd 黑窗）
5. Python 工作线程探测 /_stcore/host-config 就绪 → 用 window.load_url 切换到主界面
6. 关闭窗口 → 优雅终止 Streamlit 进程（同步执行确保日志落盘）

开发时仍可用：streamlit run app.py（浏览器，热重载）。
"""
from __future__ import annotations

import logging
import os
import socket
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path

import webview


HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
ICON = str(ASSETS / "app.ico")
LOG_FILE = HERE / "logs" / "launcher.log"
SINGLETON_LOCK_PORT = 49283  # 与 learning-system (49281) 错开

# v5.8: 重型依赖（pingouin/statsmodels/semopy 等）已改为页面渲染后
# 后台懒加载，启动只等 Streamlit 服务器就绪（通常 3~8s）。
# 超时设宽一点兜底（冷盘/杀毒扫描等极端情况）。
READY_TIMEOUT_SEC = 90
READY_POLL_INTERVAL = 0.4


# ---------- 日志 ----------
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)
logger = logging.getLogger("psy-launcher")


# ---------- 单例 ----------
_lock_socket = None  # 全局保活，进程退出才释放


def acquire_singleton_lock() -> bool:
    """监听一个固定端口实现单例锁。已运行返回 False。"""
    global _lock_socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    try:
        s.bind(("127.0.0.1", SINGLETON_LOCK_PORT))
        s.listen(1)
        _lock_socket = s
        return True
    except OSError:
        s.close()
        return False


# ---------- 端口探测 ----------
def find_free_port(preferred: int = 8501, max_tries: int = 20) -> int:
    for offset in range(max_tries):
        p = preferred + offset
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise RuntimeError(f"找不到空闲端口（{preferred}-{preferred + max_tries}）")


# ---------- 启动 Streamlit ----------
def start_streamlit_backend(port: int) -> subprocess.Popen:
    cmd = [
        sys.executable, "-m", "streamlit", "run", str(HERE / "app.py"),
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--server.fileWatcherType", "none",
    ]
    logger.info("Starting streamlit: %s", " ".join(cmd))
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW
    return subprocess.Popen(
        cmd,
        cwd=str(HERE),
        stdout=open(str(LOG_FILE.parent / "streamlit.log"), "ab"),
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )


# ---------- splash ----------
SPLASH_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>心理分析系统</title>
<style>
  * { box-sizing: border-box; }
  html, body {
    margin: 0; padding: 0; height: 100%;
    font-family: -apple-system, "Segoe UI", "PingFang SC",
                 "Microsoft YaHei", sans-serif;
    background: linear-gradient(135deg, #0EA5E9 0%, #6366F1 100%);
    color: white; overflow: hidden;
    user-select: none;
  }
  .center {
    height: 100%; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 24px;
  }
  .logo {
    font-size: 96px; font-weight: 700; line-height: 1;
    background: rgba(255,255,255,0.18); border-radius: 28px;
    width: 144px; height: 144px;
    display: flex; align-items: center; justify-content: center;
    backdrop-filter: blur(8px);
    box-shadow: 0 20px 50px rgba(0,0,0,0.25);
  }
  h1 { margin: 0; font-size: 32px; font-weight: 600; }
  p#status {
    margin: 0; font-size: 15px; opacity: 0.85; min-height: 22px;
  }
  .spinner {
    width: 40px; height: 40px; border: 3px solid rgba(255,255,255,0.25);
    border-top-color: white; border-radius: 50%;
    animation: spin 0.9s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .hint {
    position: absolute; bottom: 24px; font-size: 12px; opacity: 0.65;
    text-align: center; width: 100%;
  }
  .progress-bar {
    width: 280px; height: 4px; background: rgba(255,255,255,0.18);
    border-radius: 2px; overflow: hidden;
  }
  .progress-fill {
    height: 100%; background: white; width: 0%;
    transition: width 0.4s ease-out;
  }
</style>
</head>
<body>
<div class="center">
  <div class="logo">&Psi;</div>
  <h1>心理分析系统</h1>
  <div class="spinner"></div>
  <p id="status">正在启动后端…</p>
  <div class="progress-bar"><div id="progress" class="progress-fill"></div></div>
</div>
<div class="hint">&copy; 2026 &middot; 选题 &middot; 设计 &middot; 数据 &middot; 写作 &middot; 文献雷达</div>
</body>
</html>
"""


def update_splash(window: "webview.Window", text: str, percent: int) -> None:
    """通过 evaluate_js 实时更新 splash 文案 + 进度条。"""
    safe = text.replace("\\", "\\\\").replace("`", "\\`").replace("'", "\\'")
    js = (
        f"document.getElementById('status').textContent = '{safe}';"
        f"document.getElementById('progress').style.width = '{percent}%';"
    )
    try:
        window.evaluate_js(js)
    except Exception:
        pass  # 窗口可能已关闭


# ---------- 后端就绪探测 ----------
def is_streamlit_ready(target_url: str) -> bool:
    """/_stcore/host-config 200 才算真就绪（比 /_stcore/health 更深）。"""
    try:
        req = urllib.request.Request(f"{target_url}/_stcore/host-config")
        with urllib.request.urlopen(req, timeout=1.5) as r:
            return 200 <= r.status < 500
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
        return False


def wait_for_streamlit_and_load(window: "webview.Window", target_url: str,
                                 proc: subprocess.Popen) -> None:
    """pywebview 工作线程：探测 streamlit 就绪，再 load_url 切换到主界面。"""
    logger.info("Worker: probing %s", target_url)
    start = time.monotonic()
    while True:
        elapsed = time.monotonic() - start
        if elapsed > READY_TIMEOUT_SEC:
            logger.error("Streamlit not ready after %.1fs", elapsed)
            update_splash(window,
                          f"启动超时（{int(elapsed)}s）。请关闭窗口后重试，或查看日志。",
                          0)
            return

        # streamlit 子进程意外退出
        if proc.poll() is not None:
            logger.error("Streamlit subprocess exited with code %s", proc.returncode)
            update_splash(window,
                          f"后端进程退出（code={proc.returncode}）。请查看日志。",
                          0)
            return

        if is_streamlit_ready(target_url):
            logger.info("Streamlit ready in %.2fs", elapsed)
            update_splash(window, "就绪，正在加载界面…", 100)
            time.sleep(0.25)
            try:
                window.load_url(target_url)
            except Exception:
                logger.exception("load_url failed")
            return

        # 进度文案：随时间推移给出"为啥还没好"的合理解释
        # （v5.8 后正常启动 3~8s，这些阶段仅兜底）
        if elapsed < 2:
            msg, pct = "正在启动后端…", 20
        elif elapsed < 5:
            msg, pct = "Streamlit 服务器初始化中…", 45
        elif elapsed < 10:
            msg, pct = "正在渲染主界面…", 70
        elif elapsed < 20:
            msg, pct = "首次启动稍慢，正在初始化…", 85
        else:
            msg, pct = f"还在启动（已 {int(elapsed)}s），请稍候或查看 logs/launcher.log…", 92
        update_splash(window, msg, pct)

        time.sleep(READY_POLL_INTERVAL)


# ---------- 错误对话框 ----------
def show_error_box(title: str, message: str) -> None:
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
            return
        except Exception:
            pass
    print(f"[{title}] {message}", file=sys.stderr)


# ---------- 主流程 ----------
def main() -> int:
    logger.info("=" * 60)
    logger.info("Launcher start, sys.executable=%s", sys.executable)

    if not acquire_singleton_lock():
        logger.info("Another instance is running; exit.")
        show_error_box("已在运行", "心理分析系统已在运行，请检查任务栏窗口。")
        return 0

    try:
        port = find_free_port(preferred=8501)
    except Exception as e:
        logger.exception("Port scan failed")
        show_error_box("启动失败", f"找不到空闲端口：{e}\n\n详细日志：{LOG_FILE}")
        return 1

    try:
        proc = start_streamlit_backend(port)
    except Exception as e:
        logger.exception("Streamlit start failed")
        show_error_box("启动失败",
                       f"无法启动 Streamlit：{e}\n\n请确保依赖完整安装：\n"
                       f"  pip install -r requirements.txt\n\n日志：{LOG_FILE}")
        return 1

    target_url = f"http://127.0.0.1:{port}"
    logger.info("Streamlit backend at %s (pid=%s)", target_url, proc.pid)

    window = webview.create_window(
        "心理分析系统",
        html=SPLASH_HTML,
        width=1440,
        height=920,
        min_size=(1000, 680),
        background_color="#0EA5E9",
        easy_drag=False,
        confirm_close=False,
    )

    closed_flag = {"done": False}

    def on_closed():
        if closed_flag["done"]:
            return
        closed_flag["done"] = True
        logger.info("Window closed; terminating streamlit pid=%s.", proc.pid)
        try:
            proc.terminate()
            try:
                proc.wait(timeout=4)
                logger.info("Streamlit exited cleanly.")
            except subprocess.TimeoutExpired:
                logger.warning("Streamlit did not exit in 4s, killing.")
                proc.kill()
        except Exception:
            logger.exception("Failed to terminate streamlit cleanly")

    # should_lock=True：closed 事件同步执行（默认是后台线程，主进程可能在
    # 回调跑完前就退出，导致 streamlit 残留 + 日志没刷盘）
    window.events.closed._should_lock = True
    window.events.closed += on_closed

    try:
        webview.start(
            wait_for_streamlit_and_load,
            args=(window, target_url, proc),
            icon=ICON if os.path.exists(ICON) else None,
            private_mode=False,
        )
    except Exception:
        logger.exception("webview.start failed")
        show_error_box("启动失败",
                       f"GUI 初始化失败。请确保已装 WebView2（Win10/11 一般预装）。\n"
                       f"日志：{LOG_FILE}")
        on_closed()
        return 1

    # webview.start 返回后窗口已关闭。万一 closed 事件没触发，这里兜底。
    on_closed()
    logger.info("Launcher exit normally.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        logger.exception("Unhandled exception in launcher")
        show_error_box("严重错误",
                       f"未预料的错误：{e}\n\n详细堆栈：\n{traceback.format_exc()}\n\n"
                       f"日志：{LOG_FILE}")
        sys.exit(1)
