import asyncio
import json
import websockets

async def test_websocket():
    uri = "ws://localhost:8000/ws"
    
    async with websockets.connect(uri) as ws:
        # Reset
        print("1. Reset...")
        await ws.send(json.dumps({"type": "reset", "data": {}}))
        response = await ws.recv()
        data = json.loads(response)
        print(f"   Response: {data}")
        
        obs = data.get("data", {}).get("observation", {})
        services = obs.get("available_services", ["api-gateway"])