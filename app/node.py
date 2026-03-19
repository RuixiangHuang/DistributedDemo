import os

from fastapi import FastAPI, Request


app = FastAPI(title="Node Service")

NODE_ID = os.getenv("NODE_ID", "node-unknown")


@app.get("/")
def health():
    return {"service": "node", "node_id": NODE_ID, "status": "ok"}


@app.get("/ping")
def ping(request: Request):
    return {
        "message": "pong",
        "node_id": NODE_ID,
        "responded_from": str(request.base_url).rstrip("/"),
    }
