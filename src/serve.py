"""F33L local helper: serves the page on your own machine and, if yt-dlp is installed, fetches the audio of a YouTube link
for personal use so the jukebox can loop it. Runs only on 127.0.0.1. The public website never uses this.

Usage:  python src/serve.py [--port 8765] [--ffmpeg path\\to\\ffmpeg.exe]
Then open http://127.0.0.1:8765/ and paste a link.
Needs yt-dlp for links:  winget install yt-dlp   (or: pip install yt-dlp). Files you drop in need nothing extra.
Please respect the terms of the service and the rights of the artist; this is for your own listening, not redistribution.
"""
import argparse, glob, json, os, shutil, subprocess, sys, tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, quote

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
YT_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
MAX_SECONDS = 15 * 60
FFMPEG = os.environ.get("F33L_FFMPEG") or "ffmpeg"


def validate_url(u):
    """Return a safe https YouTube URL or None. No shell is ever used, but we still refuse anything odd."""
    if not isinstance(u, str) or len(u) > 300 or any(c.isspace() for c in u) or u.startswith("-"):
        return None
    p = urlparse(u)
    if p.scheme != "https" or (p.hostname or "").lower() not in YT_HOSTS or p.username or p.password:
        return None
    return u


def ytdlp_cmd():
    exe = shutil.which("yt-dlp")
    if exe:
        return [exe]
    try:
        import yt_dlp  # noqa: F401
        return [sys.executable, "-m", "yt_dlp"]
    except ImportError:
        return None


def host_ok(host, port):
    return host in (f"127.0.0.1:{port}", f"localhost:{port}")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        if not host_ok(self.headers.get("Host", ""), self.server.server_port):
            return self._json(403, {"error": "bad host"})
        u = urlparse(self.path)
        if u.path == "/api/health":
            return self._json(200, {"ok": True, "youtube": ytdlp_cmd() is not None})
        if u.path == "/api/yt":
            if self.headers.get("X-F33L") != "1":      # blocks other websites from calling this
                return self._json(403, {"error": "missing header"})
            url = validate_url((parse_qs(u.query).get("url") or [""])[0])
            if not url:
                return self._json(400, {"error": "Paste a normal https YouTube link."})
            cmd = ytdlp_cmd()
            if not cmd:
                return self._json(501, {"error": "yt-dlp is not installed. Run: winget install yt-dlp"})
            tmp = tempfile.mkdtemp(prefix="f33l_")
            try:
                run = cmd + ["--no-playlist", "--no-warnings", "-q", "-x", "--audio-format", "mp3", "--audio-quality", "5",
                             "--match-filter", f"duration<={MAX_SECONDS}", "--ffmpeg-location", FFMPEG,
                             "-o", os.path.join(tmp, "a.%(ext)s"), "--print", "title", "--", url]
                r = subprocess.run(run, capture_output=True, text=True, timeout=240)
                files = glob.glob(os.path.join(tmp, "a.mp3"))
                if r.returncode != 0 or not files:
                    return self._json(422, {"error": "Could not get audio (private, too long over 15 min, or blocked)."})
                data = open(files[0], "rb").read()
                self.send_response(200); self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("X-Title", quote((r.stdout.strip().splitlines() or ["video"])[0][:120]))
                self.end_headers(); self.wfile.write(data)
            except subprocess.TimeoutExpired:
                self._json(504, {"error": "That took too long."})
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            return
        return super().do_GET()


def main():
    global FFMPEG
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8765); ap.add_argument("--ffmpeg")
    a = ap.parse_args()
    if a.ffmpeg: FFMPEG = a.ffmpeg
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"F33L on http://127.0.0.1:{a.port}/   (YouTube links: {'ready' if ytdlp_cmd() else 'install yt-dlp to enable'})")
    try: srv.serve_forever()
    except KeyboardInterrupt: pass


if __name__ == "__main__":
    main()
