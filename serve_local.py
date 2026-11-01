"""Run the website locally the way Vercel serves it: static files from web/, /api/evaluate from api/evaluate.py.

Usage:  python3 serve_local.py [port]      then open http://localhost:8000
"""
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "api"))
import evaluate as api  # noqa: E402


class Handler(SimpleHTTPRequestHandler):
    _send = api.handler._send

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "web"), **kwargs)

    def do_GET(self):
        path = self.path.split("?")[0].split("#")[0]
        if path == "/api/evaluate":
            return api.handler.do_GET(self)
        if "." not in path.rsplit("/", 1)[-1] and (ROOT / "web" / f"{path.strip('/')}.html").exists():
            self.path = f"{path}.html"  # same as Vercel's cleanUrls
        return super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] == "/api/evaluate":
            return api.handler.do_POST(self)
        self.send_error(404)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Serving on http://localhost:{port}")
    ThreadingHTTPServer(("", port), Handler).serve_forever()
