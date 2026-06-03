from __future__ import annotations

import argparse
import contextlib
import functools
import http.server
import json
import socket
import socketserver
import webbrowser
from http import HTTPStatus
from pathlib import Path
from urllib.parse import urlparse

from api.jobs import JobManager


PROJECT_ROOT = Path(__file__).resolve().parent
STUDIO_ROOT = PROJECT_ROOT / "studio"


class ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class StudioRequestHandler(http.server.SimpleHTTPRequestHandler):
    job_manager: JobManager

    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if not path.startswith("/api/"):
            return super().do_GET()

        try:
            if path == "/api/health":
                self._send_json({"ok": True})
                return

            parts = [part for part in path.strip("/").split("/") if part]
            if len(parts) == 3 and parts[:2] == ["api", "jobs"]:
                self._send_json(self.job_manager.get_status(parts[2]))
                return
            if len(parts) == 4 and parts[:2] == ["api", "jobs"] and parts[3] == "results":
                self._send_json(self.job_manager.get_result(parts[2]))
                return
            if len(parts) == 4 and parts[:2] == ["api", "jobs"] and parts[3] == "export.csv":
                csv_text = self.job_manager.export_csv(parts[2])
                data = csv_text.encode("utf-8-sig")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", f'attachment; filename="studio_job_{parts[2]}.csv"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
        except KeyError:
            self._send_json({"error": "Job not found."}, HTTPStatus.NOT_FOUND)
            return
        except Exception as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self._send_json({"error": "Unknown API endpoint."}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if not path.startswith("/api/"):
            return super().do_POST()

        try:
            if path == "/api/jobs":
                payload = self._read_json_body()
                self._send_json(self.job_manager.create_job(payload), HTTPStatus.CREATED)
                return

            parts = [part for part in path.strip("/").split("/") if part]
            if len(parts) == 4 and parts[:2] == ["api", "jobs"] and parts[3] == "stop":
                self._send_json(self.job_manager.stop_job(parts[2]))
                return
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON request body."}, HTTPStatus.BAD_REQUEST)
            return
        except KeyError:
            self._send_json({"error": "Job not found."}, HTTPStatus.NOT_FOUND)
            return
        except Exception as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self._send_json({"error": "Unknown API endpoint."}, HTTPStatus.NOT_FOUND)


def find_port(preferred: int) -> int:
    for port in range(preferred, preferred + 50):
        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No available port found from {preferred} to {preferred + 49}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch the Battery Sim Studio static UI.")
    parser.add_argument("--port", type=int, default=8601, help="Preferred local server port.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser automatically.")
    args = parser.parse_args()

    if not STUDIO_ROOT.exists():
        raise FileNotFoundError(f"Studio directory does not exist: {STUDIO_ROOT}")

    port = find_port(args.port) if args.host in {"127.0.0.1", "localhost"} else args.port
    StudioRequestHandler.job_manager = JobManager()
    handler = functools.partial(StudioRequestHandler, directory=str(STUDIO_ROOT))

    with ReusableTCPServer((args.host, port), handler) as server:
        url = f"http://{args.host}:{port}/"
        print(f"Battery Sim Studio running at {url}")
        if not args.no_browser:
            webbrowser.open(url)
        server.serve_forever()


if __name__ == "__main__":
    main()
