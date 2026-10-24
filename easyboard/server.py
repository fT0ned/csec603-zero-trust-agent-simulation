"""Tiny read-only web server (stdlib only). GET only; nothing here ever writes to results/."""
import json
import socket
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from . import data

PAGE = Path(__file__).parent / 'static' / 'index.html'


def make_handler(results=None):
    class Handler(BaseHTTPRequestHandler):
        server_version = 'easyboard'

        def log_message(self, *args): pass

        def _send(self, status, body, kind):
            payload = body if isinstance(body, bytes) else body.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', kind); self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store'); self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers(); self.wfile.write(payload)

        def _json(self, value, status=200): self._send(status, json.dumps(value), 'application/json; charset=utf-8')

        def do_GET(self):
            path = urlparse(self.path).path.rstrip('/') or '/'
            if path == '/': return self._send(200, PAGE.read_bytes(), 'text/html; charset=utf-8')
            if path == '/healthz': return self._json({'ok': True})
            if path == '/api/overview': return self._json(data.overview(results))
            if path == '/api/glossary': return self._json([{'term': t, 'meaning': m} for t, m in data.GLOSSARY])
            if path.startswith('/api/study/'):
                study = data.get_study(path[len('/api/study/'):], results)
                return self._json(study) if study else self._json({'error': 'unknown study'}, 404)
            self._json({'error': 'not found'}, 404)

        def _refuse(self): self._json({'error': 'This dashboard is read-only.'}, 405)
        do_POST = do_PUT = do_DELETE = do_PATCH = _refuse

    return Handler


def free_port(start=8770, tries=50):
    for port in range(start, start + tries):
        with socket.socket() as probe:
            try: probe.bind(('127.0.0.1', port))
            except OSError: continue
            return port
    raise RuntimeError('No free port found')


def serve(port=None, results=None, open_browser=True):
    port = port or free_port()
    httpd = ThreadingHTTPServer(('127.0.0.1', port), make_handler(results))
    url = 'http://127.0.0.1:%d/' % port
    print('Dashboard running at ' + url + '  (close this window to stop)', flush=True)
    if open_browser: threading.Timer(0.8, webbrowser.open, args=(url,)).start()
    try: httpd.serve_forever()
    except KeyboardInterrupt: pass
    finally: httpd.server_close()
