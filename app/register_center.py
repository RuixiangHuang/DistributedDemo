import os
import random
import time
from typing import Any, Dict
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl


app = FastAPI(title="Register Center")


class NodeRegistration(BaseModel):
    node_id: str
    node_url: HttpUrl


class NodeUnregistration(BaseModel):
    node_id: str


class NodeHeartbeat(BaseModel):
    node_id: str


registered_nodes: Dict[str, Dict[str, Any]] = {}
HEARTBEAT_TIMEOUT_SECONDS = int(os.getenv("HEARTBEAT_TIMEOUT_SECONDS", "10"))


def _extract_port(url: str):
    parsed = urlparse(url)
    return parsed.port


def _is_alive(node_info: Dict[str, Any]) -> bool:
    return (time.time() - node_info["last_heartbeat"]) <= HEARTBEAT_TIMEOUT_SECONDS


def _alive_nodes() -> Dict[str, Dict[str, Any]]:
    return {
        node_id: info
        for node_id, info in registered_nodes.items()
        if _is_alive(info)
    }


@app.get("/")
def health():
    return {"service": "register-center", "status": "ok"}


@app.post("/nodes/register")
def register_node(payload: NodeRegistration):
    node_url = str(payload.node_url).rstrip("/")
    registered_nodes[payload.node_id] = {
        "node_url": node_url,
        "node_port": _extract_port(node_url),
        "last_heartbeat": time.time(),
    }
    return {
        "message": "node registered",
        "node_id": payload.node_id,
        "total_nodes": len(registered_nodes),
    }


@app.post("/nodes/unregister")
def unregister_node(payload: NodeUnregistration):
    if payload.node_id not in registered_nodes:
        raise HTTPException(status_code=404, detail="node not found")

    removed_node = registered_nodes.pop(payload.node_id)
    return {
        "message": "node unregistered",
        "node_id": payload.node_id,
        "node_url": removed_node["node_url"],
        "node_port": removed_node["node_port"],
        "total_nodes": len(registered_nodes),
    }


@app.post("/nodes/heartbeat")
def heartbeat(payload: NodeHeartbeat):
    node_info = registered_nodes.get(payload.node_id)
    if node_info is None:
        raise HTTPException(status_code=404, detail="node not found")

    node_info["last_heartbeat"] = time.time()
    return {
        "message": "heartbeat received",
        "node_id": payload.node_id,
        "node_port": node_info["node_port"],
    }


@app.get("/nodes")
def list_nodes():
    nodes = {
        node_id: {
            "node_url": info["node_url"],
            "node_port": info["node_port"],
            "alive": _is_alive(info),
            "last_heartbeat": info["last_heartbeat"],
        }
        for node_id, info in registered_nodes.items()
    }
    alive_count = sum(1 for node in nodes.values() if node["alive"])
    return {
        "total_nodes": len(registered_nodes),
        "alive_nodes": alive_count,
        "heartbeat_timeout_seconds": HEARTBEAT_TIMEOUT_SECONDS,
        "nodes": nodes,
    }


@app.get("/ping")
async def ping():
    if not registered_nodes:
        raise HTTPException(status_code=503, detail="no registered nodes")

    alive_nodes = _alive_nodes()
    if not alive_nodes:
        raise HTTPException(status_code=503, detail="no alive nodes (heartbeat timeout)")

    chosen_node_id = random.choice(list(alive_nodes.keys()))
    chosen_node = alive_nodes[chosen_node_id]
    chosen_node_url = chosen_node["node_url"]
    target = f"{chosen_node_url}/ping"

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            node_response = await client.get(target)
            node_response.raise_for_status()
            payload = node_response.json()
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"node unreachable: {exc}") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"node returned bad status: {exc.response.status_code}",
        ) from exc

    return {
        "message": "pong from random node",
        "selected_node_id": chosen_node_id,
        "selected_node_url": chosen_node_url,
        "selected_node_port": chosen_node["node_port"],
        "responded_from": payload.get("responded_from", chosen_node_url),
        "responded_from_port": payload.get("responded_from_port", chosen_node["node_port"]),
        "node_response": payload,
    }
