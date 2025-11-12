import asyncio, sys
import websockets
URL = sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8000/v1/state/live/ws"
async def main():
    async with websockets.connect(URL) as ws:
        print(f"[WS connected] {URL}")
        while True:
            print(await ws.recv())
if __name__ == "__main__":
    asyncio.run(main())
