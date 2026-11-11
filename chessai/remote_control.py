"""Optional, separately managed local-network controller for chessai.service."""
import hmac
import json
import os
from pathlib import Path
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


UNIT = "chessai.service"


def systemctl(action):
    command = ["systemctl", "--user", action, UNIT]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"Could not run systemctl: {exc}") from exc
    if action == "is-active":
        if result.returncode == 0 and result.stdout.strip() == "active":
            return True
        if result.returncode == 3 and result.stdout.strip() == "inactive":
            return False
    elif result.returncode == 0:
        return None
    raise RuntimeError(f"systemctl {action} failed: {result.stderr.strip() or result.stdout.strip()}")


def create_handler(token, run=systemctl):
    operation_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # Do not log request headers or credentials.
            super().log_message(fmt, *args)

        def reply(self, status, data):
            content = json.dumps(data).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def authorized(self):
            provided = self.headers.get("Authorization", "")
            return hmac.compare_digest(provided.encode("utf-8"), f"Bearer {token}".encode("utf-8"))

        def do_GET(self):
            if not self.authorized():
                self.reply(401, {"detail": "Invalid controller token."})
                return
            if self.path != "/status":
                self.reply(404, {"detail": "Unknown endpoint."})
                return
            try:
                with operation_lock:
                    running = run("is-active")
            except RuntimeError as exc:
                self.reply(503, {"detail": str(exc)})
                return
            self.reply(200, {"running": running})

        def do_POST(self):
            if not self.authorized():
                self.reply(401, {"detail": "Invalid controller token."})
                return
            if self.path not in {"/start", "/stop"}:
                self.reply(404, {"detail": "Unknown endpoint."})
                return
            try:
                with operation_lock:
                    run(self.path[1:])
                    running = run("is-active")
            except RuntimeError as exc:
                self.reply(503, {"detail": str(exc)})
                return
            self.reply(200, {"running": running})

    return Handler


def main():
    token_file = os.environ.get("CHESSAI_CONTROL_TOKEN_FILE")
    if not token_file:
        raise SystemExit("Set CHESSAI_CONTROL_TOKEN_FILE to a private token file.")
    path = Path(token_file)
    try:
        if path.stat().st_mode & 0o077:
            raise SystemExit("Controller token file must not be accessible to group or others.")
        token = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise SystemExit(f"Cannot read controller token: {exc}") from exc
    if len(token) < 32 or not token.isascii() or any(char.isspace() for char in token):
        raise SystemExit("Controller token must contain at least 32 non-whitespace ASCII characters.")
    address = os.environ.get("CHESSAI_CONTROL_HOST", "0.0.0.0")
    port = int(os.environ.get("CHESSAI_CONTROL_PORT", "5679"))
    server = ThreadingHTTPServer((address, port), create_handler(token))
    print(f"ChessAI controller listening on {address}:{port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
