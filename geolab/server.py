"""Read-only, loopback-only laboratory HTTP service. Run with python -m geolab.server."""

import argparse
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .solver import solve

ROOT = Path(__file__).resolve().parents[1]


class LocalServer(HTTPServer):
    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(3)  # Browser preconnects cannot hold the single worker indefinitely.
        return connection, address


def make_server(port=8764):
    scenes = {p.stem: json.loads(p.read_text()) for p in sorted((ROOT / "data/inputs").glob("*.json"))}
    if not scenes:
        raise RuntimeError("No fixtures. Run python3 -m geolab.generate first.")

    @lru_cache(maxsize=8)
    def cached_solve(scene_id, resolution, selection):
        return solve(scenes[scene_id], resolution, list(selection))

    class Handler(BaseHTTPRequestHandler):
        def send_data(self, data, content_type="application/json; charset=utf-8", code=200):
            if isinstance(data, (dict, list)):
                data = json.dumps(data, allow_nan=False).encode()
            elif isinstance(data, str):
                data = data.encode()
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            url = urlsplit(self.path)
            query = parse_qs(url.query, keep_blank_values=True)
            static = {"/": ("web/index.html", "text/html; charset=utf-8"),
                      "/index.html": ("web/index.html", "text/html; charset=utf-8"),
                      "/app.js": ("web/app.js", "text/javascript; charset=utf-8"),
                      "/style.css": ("web/style.css", "text/css; charset=utf-8"),
                      "/report": ("reports/coverage.md", "text/plain; charset=utf-8"),
                      "/teaching.svg": ("reports/teaching.svg", "image/svg+xml")}
            try:
                if url.path in static:
                    file, content_type = static[url.path]
                    path = ROOT / file
                    if not path.is_file():
                        self.send_data({"error": "Artifact not generated yet"}, code=404)
                    else:
                        self.send_data(path.read_bytes(), content_type)
                    return
                if url.path == "/api/scenes":
                    self.send_data({"scenes": list(scenes.values())})
                    return
                if url.path not in ("/api/scene", "/api/truth", "/api/solve"):
                    self.send_data({"error": "Not found"}, code=404)
                    return
                scene_id = query.get("id", [""])[0]
                if scene_id not in scenes:
                    raise ValueError("Select a scene ID listed by /api/scenes")
                if url.path == "/api/scene":
                    self.send_data(scenes[scene_id])
                elif url.path == "/api/truth":
                    # Teaching-only answer-key endpoint. Never passed to solve().
                    self.send_data(json.loads((ROOT / "data/truth" / (scene_id + ".json")).read_text()))
                else:
                    resolution = int(query.get("n", ["128"])[0])
                    if "obs" in query:
                        selection = tuple(filter(None, query["obs"][0].split(",")))
                    else:
                        selection = tuple(scenes[scene_id].get("default_observations", [o["id"] for o in scenes[scene_id]["observations"]]))
                    self.send_data(cached_solve(scene_id, resolution, selection))
            except (ValueError, TypeError, KeyError) as exc:
                self.send_data({"error": str(exc)}, code=400)

    # Single worker bounds CPU concurrency. No binding to external interfaces.
    return LocalServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8764)
    args = parser.parse_args()
    server = make_server(args.port)
    print(f"Synthetic geolocation laboratory: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
