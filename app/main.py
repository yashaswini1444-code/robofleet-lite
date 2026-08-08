import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.models import Position
from app.schemas.api import TaskCreate, ObstacleCreate, CompareRequest
from app.services.simulation import SimulationEngine
from app.api.websocket import ConnectionManager
from app.core.config import TICK_SECONDS

engine = SimulationEngine()
manager = ConnectionManager()
state_lock = asyncio.Lock()
loop_task: asyncio.Task | None = None

async def simulation_loop():
    while True:
        if engine.running:
            async with state_lock: state = engine.tick()
            await manager.broadcast(state)
        await asyncio.sleep(TICK_SECONDS)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global loop_task
    loop_task = asyncio.create_task(simulation_loop())
    yield
    loop_task.cancel()
    try: await loop_task
    except asyncio.CancelledError: pass

app = FastAPI(title="RoboFleet Lite", version="1.0.0", lifespan=lifespan)
web = Path(__file__).parent / "web"
app.mount("/static", StaticFiles(directory=web), name="static")

@app.get("/")
def index(): return FileResponse(web / "index.html")
@app.get("/health")
def health(): return {"status": "ok"}
@app.get("/api/state")
def state(): return engine.snapshot()
@app.get("/api/grid")
def grid(): return engine.snapshot()["grid"]
@app.get("/api/robots")
def robots(): return engine.snapshot()["robots"]
@app.get("/api/tasks")
def tasks(): return engine.snapshot()["tasks"]
@app.get("/api/metrics")
def metrics(): return engine.snapshot()["metrics"]

async def changed(state=None):
    result = state or engine.snapshot(); await manager.broadcast(result); return result

@app.post("/api/tasks", status_code=201)
async def create_task(body: TaskCreate):
    try:
        async with state_lock: task = engine.add_task(Position(**body.pickup.model_dump()), Position(**body.delivery.model_dump()))
    except ValueError as exc: raise HTTPException(400, str(exc)) from exc
    return await changed()

@app.post("/api/obstacles", status_code=201)
async def add_obstacle(body: ObstacleCreate):
    try:
        async with state_lock: engine.add_obstacle(Position(**body.position.model_dump()))
    except ValueError as exc: raise HTTPException(409, str(exc)) from exc
    return await changed()

@app.delete("/api/obstacles/{x}/{y}")
async def remove_obstacle(x: int, y: int):
    try:
        async with state_lock: engine.remove_obstacle(Position(x, y))
    except KeyError as exc: raise HTTPException(404, str(exc)) from exc
    return await changed()

@app.post("/api/simulation/start")
async def start(): engine.running = True; return await changed()
@app.post("/api/simulation/pause")
async def pause(): engine.running = False; return await changed()
@app.post("/api/simulation/reset")
async def reset():
    async with state_lock: engine.reset()
    return await changed()
@app.post("/api/simulation/tick")
async def tick():
    async with state_lock: result = engine.tick()
    return await changed(result)

@app.post("/api/pathfinding/compare")
def compare(body: CompareRequest):
    results = engine.compare(Position(**body.start.model_dump()), Position(**body.goal.model_dump()))
    return [{"algorithm": r.algorithm, "reachable": r.reachable, "path_length": r.path_length,
             "expanded_nodes": r.expanded_nodes, "planning_time_ms": r.planning_time_ms,
             "path": [{"x": p.x, "y": p.y} for p in r.path]} for r in results]

@app.websocket("/ws/simulation")
async def socket(ws: WebSocket):
    await manager.connect(ws)
    try:
        await ws.send_json(engine.snapshot())
        while True: await ws.receive_text()
    except WebSocketDisconnect: manager.disconnect(ws)
