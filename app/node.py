import os
import asyncio
from contextlib import suppress
from typing import Optional

import httpx
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager


NODE_ID = os.getenv("NODE_ID", "node-unknown")
NODE_PORT = int(os.getenv("NODE_PORT", "9000"))
CENTER_URL = os.getenv("CENTER_URL", "http://127.0.0.1:8000").rstrip("/")
HEARTBEAT_INTERVAL_SECONDS = float(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "2"))

heartbeat_task: Optional[asyncio.Task] = None


async def _send_heartbeat():
    payload = {"node_id": NODE_ID}
    async with httpx.AsyncClient(timeout=3.0) as client:
        response = await client.post(f"{CENTER_URL}/nodes/heartbeat", json=payload)
        response.raise_for_status()


async def _heartbeat_loop():
    global heartbeat_task
    while True:
        try:
            await _send_heartbeat()
        except httpx.HTTPStatusError as exc:
            # If this node is not registered anymore, stop heartbeat loop.
            if exc.response.status_code == 404:
                break
        except httpx.HTTPError:
            # Keep node process alive even when center is temporarily unreachable.
            pass
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
    heartbeat_task = None


def _heartbeat_running() -> bool:
    return heartbeat_task is not None and not heartbeat_task.done()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        yield
    finally:
        global heartbeat_task
        if _heartbeat_running():
            heartbeat_task.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat_task
        heartbeat_task = None


app = FastAPI(title="Node Service", lifespan=lifespan)


@app.get("/")
def health():
    return {
        "service": "node",
        "node_id": NODE_ID,
        "node_port": NODE_PORT,
        "heartbeat_running": _heartbeat_running(),
        "status": "ok",
    }


@app.post("/heartbeat/start")
async def start_heartbeat():
    global heartbeat_task
    if _heartbeat_running():
        return {"message": "heartbeat already running", "node_id": NODE_ID}
    heartbeat_task = asyncio.get_running_loop().create_task(_heartbeat_loop())
    return {"message": "heartbeat started", "node_id": NODE_ID}


@app.post("/heartbeat/stop")
async def stop_heartbeat():
    global heartbeat_task
    if not _heartbeat_running():
        return {"message": "heartbeat already stopped", "node_id": NODE_ID}
    heartbeat_task.cancel()
    with suppress(asyncio.CancelledError):
        await heartbeat_task
    heartbeat_task = None
    return {"message": "heartbeat stopped", "node_id": NODE_ID}


@app.get("/ping")
def ping(request: Request):
    return {
        "message": "pong",
        "node_id": NODE_ID,
        "responded_from": str(request.base_url).rstrip("/"),
        "responded_from_port": NODE_PORT,
    }
