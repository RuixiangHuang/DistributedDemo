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


async def _is_registered() -> bool:
    async with httpx.AsyncClient(timeout=3.0) as client:
        response = await client.get(f"{CENTER_URL}/nodes")
        response.raise_for_status()
        payload = response.json()
    nodes = payload.get("nodes", {})
    return NODE_ID in nodes


async def _heartbeat_loop():
    while True:
        try:
            if await _is_registered():
                await _send_heartbeat()
        except httpx.HTTPError:
            # Keep node process alive even when center is temporarily unreachable.
            pass
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global heartbeat_task
    heartbeat_task = asyncio.create_task(_heartbeat_loop())
    try:
        yield
    finally:
        if heartbeat_task is not None:
            heartbeat_task.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat_task


app = FastAPI(title="Node Service", lifespan=lifespan)


@app.get("/")
def health():
    return {
        "service": "node",
        "node_id": NODE_ID,
        "node_port": NODE_PORT,
        "status": "ok",
    }


@app.get("/ping")
def ping(request: Request):
    return {
        "message": "pong",
        "node_id": NODE_ID,
        "responded_from": str(request.base_url).rstrip("/"),
        "responded_from_port": NODE_PORT,
    }
