# Microservice Homework Demo: Register Center + Node

This project provides a minimal runnable microservice architecture example:

- `register center`: handles node registration/unregistration, receives heartbeat, and performs random `ping` dispatch.
- `node`: auto-registers on startup, sends heartbeat periodically, and auto-unregisters on shutdown.

## 1. Create and activate a virtual environment

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Start services

### Start register center (port 8000)

```bash
uvicorn app.register_center:app --host 0.0.0.0 --port 8000 --reload
```

### Start two nodes (example)

Terminal 1:

```bash
NODE_ID=node-1 NODE_PORT=9001 CENTER_URL=http://127.0.0.1:8000 NODE_PUBLIC_URL=http://127.0.0.1:9001 uvicorn app.node:app --host 0.0.0.0 --port 9001 --reload
```

Terminal 2:

```bash
NODE_ID=node-2 NODE_PORT=9002 CENTER_URL=http://127.0.0.1:8000 NODE_PUBLIC_URL=http://127.0.0.1:9002 uvicorn app.node:app --host 0.0.0.0 --port 9002 --reload
```

## 4. Heartbeat and random ping dispatch

Nodes send heartbeat to center through:

- `POST /nodes/heartbeat`

Center marks a node as alive if heartbeat is received within the timeout window.

Call the endpoint below multiple times. It will randomly route to one **alive** node:

```bash
curl http://127.0.0.1:8000/ping
```

The response includes:

- `selected_node_port`: selected node port in center routing result
- `responded_from_port`: the actual node port that returned `pong`

## 5. Query and unregister

List registered nodes:

```bash
curl http://127.0.0.1:8000/nodes
```

Unregister a node:

```bash
curl -X POST http://127.0.0.1:8000/nodes/unregister \
  -H "Content-Type: application/json" \
  -d '{"node_id":"node-1"}'
```
