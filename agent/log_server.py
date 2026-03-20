"""
AnsysAgent 日志查看 HTTP 服务

启动后台 HTTP server，提供简洁的 Web 界面查看运行日志。

端口：默认 7788，可通过环境变量 ANSYS_LOG_PORT 覆盖。
访问：http://localhost:7788
"""

from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


def _get_log_file() -> Path:
    from agent.paths import ANSYS_DATA_DIR
    return ANSYS_DATA_DIR / "logs" / "ansys_agent.log"


def _read_recent_lines(n: int = 300) -> list[str]:
    log_file = _get_log_file()
    if not log_file.exists():
        return []
    try:
        with open(log_file, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return [line.rstrip() for line in lines[-n:]]
    except Exception:
        return []


_HTML = """\
<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>AnsysAgent Logs</title>
<style>
  body { font-family: monospace; background: #1e1e1e; color: #d4d4d4; margin: 0; }
  #header { background: #252526; padding: 10px 16px; display: flex; align-items: center; gap: 12px; border-bottom: 1px solid #3c3c3c; }
  #header h1 { font-size: 15px; margin: 0; color: #9cdcfe; }
  #ctrl { margin-left: auto; display: flex; gap: 8px; align-items: center; font-size: 12px; }
  #ctrl label { color: #888; }
  #ctrl input[type=checkbox] { cursor: pointer; }
  #ctrl button { background: #0e639c; border: none; color: #fff; padding: 4px 10px; border-radius: 3px; cursor: pointer; font-size: 12px; }
  #ctrl button:hover { background: #1177bb; }
  #log { padding: 10px 16px; font-size: 12px; line-height: 1.6; white-space: pre-wrap; word-break: break-all; }
  .ERROR   { color: #f48771; }
  .WARNING { color: #cca700; }
  .DEBUG   { color: #888; }
  .INFO    { color: #d4d4d4; }
  #status { font-size: 11px; color: #888; margin-left: 8px; }
</style>
</head>
<body>
<div id="header">
  <h1>AnsysAgent Logs</h1>
  <span id="status">loading...</span>
  <div id="ctrl">
    <label><input type="checkbox" id="autoScroll" checked> Auto-scroll</label>
    <label><input type="checkbox" id="autoRefresh" checked> Auto-refresh</label>
    <button onclick="fetchLogs()">Refresh</button>
    <button onclick="clearDisplay()">Clear</button>
  </div>
</div>
<div id="log"></div>
<script>
const LEVEL_RE = /\\[(ERROR|WARNING|DEBUG|INFO)\\]/;
function colorLine(line) {
  const m = LEVEL_RE.exec(line);
  const cls = m ? m[1] : 'INFO';
  const escaped = line.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  return '<span class="' + cls + '">' + escaped + '</span>';
}
let lines = [];
async function fetchLogs() {
  try {
    const res = await fetch('/api/logs?lines=500');
    const data = await res.json();
    lines = data.lines || [];
    render();
    document.getElementById('status').textContent = 'updated ' + new Date().toLocaleTimeString();
  } catch(e) {
    document.getElementById('status').textContent = 'error: ' + e.message;
  }
}
function render() {
  const el = document.getElementById('log');
  el.innerHTML = lines.map(colorLine).join('\\n');
  if (document.getElementById('autoScroll').checked) {
    el.scrollTop = el.scrollHeight;
    window.scrollTo(0, document.body.scrollHeight);
  }
}
function clearDisplay() { lines = []; render(); }
fetchLogs();
setInterval(() => { if (document.getElementById('autoRefresh').checked) fetchLogs(); }, 2000);
</script>
</body>
</html>
"""


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # silence access logs
        pass

    def do_GET(self):  # noqa: N802
        if self.path == "/" or self.path == "":
            body = _HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path.startswith("/api/logs"):
            qs = self.path.split("?", 1)[1] if "?" in self.path else ""
            n = 300
            for part in qs.split("&"):
                if part.startswith("lines="):
                    try:
                        n = int(part[6:])
                    except ValueError:
                        pass
            data = json.dumps({"lines": _read_recent_lines(n)}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404)
            self.end_headers()


def start_log_server() -> int:
    """
    在后台守护线程中启动日志查看 HTTP server。
    返回实际绑定的端口号。
    """
    port = int(os.environ.get("ANSYS_LOG_PORT", "7788"))
    server = HTTPServer(("127.0.0.1", port), _Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True, name="AnsysLogServer")
    t.start()
    return port
