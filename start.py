import asyncio
import os
import threading
from aiohttp import web
import bot as fitbot

async def handle(request):
    return web.Response(text="OK")

async def run_web():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await run_web()
    await fitbot.main()

if __name__ == "__main__":
    asyncio.run(main())
