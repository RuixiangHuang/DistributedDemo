import random
from typing import Dict

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl


app = FastAPI(title="Register Center")


class NodeRegistration(BaseModel):
    node_id: str
    node_url: HttpUrl


class NodeUnregistration(BaseModel):
    node_id: str


registered_nodes: Dict[str, str] = {}


@app.get("/")
def health():
    return {"service": "register-center", "status": "ok"}


@app.post("/nodes/register")
def register_node(payload: NodeRegistration):
    registered_nodes[payload.node_id] = str(payload.node_url).rstrip("/")
    return {
        "message": "node registered",
        "node_id": payload.node_id,
        "total_nodes": len(registered_nodes),
    }


@app.post("/nodes/unregister")
def unregister_node(payload: NodeUnregistration):
    if payload.node_id not in registered_nodes:
        raise HTTPException(status_code=404, detail="node not found")

    removed_url = registered_nodes.pop(payload.node_id)
    return {
        "message": "node unregistered",
        "node_id": payload.node_id,
        "node_url": removed_url,
        "total_nodes": len(registered_nodes),
    }


@app.get("/nodes")
def list_nodes():
    return {"total_nodes": len(registered_nodes), "nodes": registered_nodes}


@app.get("/ping")
async def ping():
    if not registered_nodes:
        raise HTTPException(status_code=503, detail="no registered nodes")

    chosen_node_id = random.choice(list(registered_nodes.keys()))
    chosen_node_url = registered_nodes[chosen_node_id]
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
        "responded_from": payload.get("responded_from", chosen_node_url),
        "node_response": payload,
    }
