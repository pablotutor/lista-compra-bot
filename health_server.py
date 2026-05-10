import os
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from zoneinfo import ZoneInfo

HORA_INICIO = 10
HORA_FIN    = 21
TZ_SPAIN    = ZoneInfo("Europe/Madrid")


def _en_horario_activo() -> bool:
    return HORA_INICIO <= datetime.now(TZ_SPAIN).hour < HORA_FIN


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return
        if _en_horario_activo():
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(503)
            self.end_headers()
            self.wfile.write(b'{"status":"sleeping"}')

    def log_message(self, *args):
        pass  # silenciar logs de cada ping de UptimeRobot


def start_health_server() -> None:
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
