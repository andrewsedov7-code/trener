import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import bot as fitbot

# Простой HTTP сервер чтобы Render не останавливал процесс
class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"FitBot is running!")
    def log_message(self, *args):
        pass  # не спамим в логи

def run_web():
    port = int(__import__("os").environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), PingHandler)
    server.serve_forever()

if __name__ == "__main__":
    # Запускаем веб-сервер в отдельном потоке
    t = threading.Thread(target=run_web, daemon=True)
    t.start()
    # Запускаем бота
    asyncio.run(fitbot.main())
