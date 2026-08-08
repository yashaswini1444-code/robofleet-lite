from fastapi import WebSocket

class ConnectionManager:
    def __init__(self): self.clients: set[WebSocket] = set()
    async def connect(self, ws: WebSocket):
        await ws.accept(); self.clients.add(ws)
    def disconnect(self, ws: WebSocket): self.clients.discard(ws)
    async def broadcast(self, state):
        dead = []
        for ws in list(self.clients):
            try: await ws.send_json(state)
            except Exception: dead.append(ws)
        for ws in dead: self.disconnect(ws)

