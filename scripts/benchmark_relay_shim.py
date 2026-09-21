#!/usr/bin/env python3
"""k62a：本地中转 shim（127.0.0.1:8791）——把苏格拉底基准的 OpenAI 兼容调用
转发到 ai.711ev.com 中转站，补齐三件中转要求：
  ① Origin/Referer/浏览器 UA 头（口径同 D:\\code\\scripts\\llm_call.py:_relay_headers）；
  ② temperature 强制 1.0（中转对 gpt 系拒绝其它值）；
  ③ 鉴权重写：上游 key 从 D:/code/.env.local 的 GPT_API_KEY 读取，绝不落日志。
逐次调用追加 data/benchmark_history/_relay_calls.jsonl（ts/model/status/usage）。
纯 stdlib，无第三方依赖。
"""
import json
import re
import urllib.error
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(r"D:/code")
ENV_PATH = ROOT / ".env.local"
LOG_PATH = Path(__file__).resolve().parents[1] / "data" / "benchmark_history" / "_relay_calls.jsonl"  # s922-09/A5: 落仓根 data/，原 .parent 指向 scripts/data/（不存在）
UPSTREAM = "https://ai.711ev.com/v1/chat/completions"
RELAY_HEADERS = {
    "Origin": "http://127.0.0.1:55758",
    "Referer": "http://127.0.0.1:55758/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 Chrome/120 Safari/537.36",
}

API_KEY = ""


def load_env_key() -> str:
    """只取 GPT_API_KEY 的值；绝不打印/写日志。"""
    text = ENV_PATH.read_text(encoding="utf-8")
    match = re.search(r"^GPT_API_KEY\s*=\s*(.+)$", text, re.M)
    if not match:
        raise SystemExit("GPT_API_KEY missing in D:/code/.env.local")
    return match.group(1).strip().strip('"').strip("'")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802（http.server 约定）
        if not self.path.endswith("/chat/completions"):
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length))
        except Exception:
            payload = {}
        model = payload.get("model", "")
        payload["temperature"] = 1.0  # 中转强制值
        data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(UPSTREAM, data=data, method="POST")
        request.add_header("Content-Type", "application/json")
        request.add_header("Authorization", f"Bearer {API_KEY}")
        for key, value in RELAY_HEADERS.items():
            request.add_header(key, value)

        status = 502
        resp_body = b""
        try:
            with urllib.request.urlopen(request, timeout=300) as resp:
                status = resp.status
                resp_body = resp.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            resp_body = exc.read()
        except Exception as exc:  # 连接层错误
            resp_body = json.dumps({"error": str(exc)}).encode("utf-8")

        usage = None
        try:
            usage = json.loads(resp_body).get("usage")
        except Exception:
            usage = None
        self._log(status, model, usage)

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_body)))
        self.end_headers()
        self.wfile.write(resp_body)

    def _log(self, status: int, model: str, usage) -> None:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {"ts": datetime.now().isoformat(), "model": model, "status": status, "usage": usage}
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def log_message(self, *args):  # 静默访问日志
        pass


if __name__ == "__main__":
    API_KEY = load_env_key()
    server = ThreadingHTTPServer(("127.0.0.1", 8791), Handler)
    print("relay shim listening on 127.0.0.1:8791")
    server.serve_forever()
