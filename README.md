# Microservice Homework Demo: Register Center + Node

This project provides a minimal runnable microservice architecture example:

- `register center`: handles node registration/unregistration and random `ping` dispatch.
- `node`: a registered service instance exposing its own `/ping` endpoint.

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
NODE_ID=node-1 uvicorn app.node:app --host 0.0.0.0 --port 9001 --reload
```

Terminal 2:

```bash
NODE_ID=node-2 uvicorn app.node:app --host 0.0.0.0 --port 9002 --reload
```

## 4. Register nodes to register center

```bash
curl -X POST http://127.0.0.1:8000/nodes/register \
  -H "Content-Type: application/json" \
  -d '{"node_id":"node-1","node_url":"http://127.0.0.1:9001"}'
```

```bash
curl -X POST http://127.0.0.1:8000/nodes/register \
  -H "Content-Type: application/json" \
  -d '{"node_id":"node-2","node_url":"http://127.0.0.1:9002"}'
```

## 5. Random ping dispatch

Call the endpoint below multiple times. It will randomly route to one of the registered nodes:

```bash
curl http://127.0.0.1:8000/ping
```

## 6. Query and unregister

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
