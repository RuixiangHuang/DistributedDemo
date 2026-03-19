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
NODE_PUBLIC_URL = os.getenv("NODE_PUBLIC_URL", f"http://127.0.0.1:{NODE_PORT}").rstrip("/")
HEARTBEAT_INTERVAL_SECONDS = float(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "2"))

heartbeat_task: Optional[asyncio.Task] = None


async def _register():
    payload = {"node_id": NODE_ID, "node_url": NODE_PUBLIC_URL}
    async with httpx.AsyncClient(timeout=3.0) as client:
        response = await client.post(f"{CENTER_URL}/nodes/register", json=payload)
        response.raise_for_status()


async def _unregister():
    payload = {"node_id": NODE_ID}
    async with httpx.AsyncClient(timeout=3.0) as client:
        response = await client.post(f"{CENTER_URL}/nodes/unregister", json=payload)
        response.raise_for_status()


async def _send_heartbeat():
    payload = {"node_id": NODE_ID}
    async with httpx.AsyncClient(timeout=3.0) as client:
        response = await client.post(f"{CENTER_URL}/nodes/heartbeat", json=payload)
        response.raise_for_status()


async def _register_with_retry(retries: int = 10, delay_seconds: float = 0.5):
    last_error: Optional[Exception] = None
    for _ in range(retries):
        try:
            await _register()
            return
        except httpx.HTTPError as exc:
            last_error = exc
            await asyncio.sleep(delay_seconds)
    if last_error is not None:
        raise last_error


async def _heartbeat_loop():
    while True:
        try:
            await _send_heartbeat()
        except httpx.HTTPError:
            # Keep node process alive even when center is temporarily unreachable.
            pass
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global heartbeat_task
    await _register_with_retry()
    heartbeat_task = asyncio.create_task(_heartbeat_loop())
    try:
        yield
    finally:
        if heartbeat_task is not None:
            heartbeat_task.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat_task
        try:
            await _unregister()
        except httpx.HTTPError:
            pass


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
