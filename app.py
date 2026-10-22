"""Serveur HTTP local pour L’Atelier Roulant."""

from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from os import environ
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = int(environ.get("PORT", "8000"))


class SiteHandler(SimpleHTTPRequestHandler):
    """Sert les fichiers statiques du site depuis le dépôt."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), SiteHandler)
    print(f"L’Atelier Roulant est disponible sur http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")
    finally:
        server.server_close()
