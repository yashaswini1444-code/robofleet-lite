# Architecture

## Layer overview

```
Browser (canvas + vanilla JS)
      │  REST (commands)         ▲  WebSocket (pushed snapshots)
      ▼                          │
FastAPI (app/main.py)  ──────────┘
      │  asyncio.Lock-guarded calls
      ▼
SimulationEngine (app/services/simulation/engine.py)
      │
      ├── assign_tasks()  ───────────────► nearest-idle-robot assignment
      ├── resolve_moves() ───────────────► app/services/coordination/collision.py
      ├── plan() / compare() ────────────► app/services/pathfinding/ (A*, Dijkstra)
      └── owns state ─────────────────────► app/models/ (Grid, Robot, DeliveryTask, Position)
```

This is a strict four-layer dependency chain — browser → FastAPI → engine → domain/algorithms — and dependencies only point downward. Nothing below `app/main.py` imports FastAPI; `SimulationEngine` imports the assignment logic it defines itself plus the pathfinding and coordination modules, and none of `app/models/`, `app/services/pathfinding/`, or `app/services/coordination/` import `SimulationEngine` or FastAPI. That inversion is what makes A*, Dijkstra, assignment, and collision arbitration directly unit-testable with plain Python objects and no HTTP server or event loop involved.

## Browser

`app/web/index.html`, `styles.css`, `app.js` — a static page with no build step and no framework. It renders whatever JSON snapshot it's given onto a `<canvas>`: grid cells, static/dynamic obstacles, pickup/delivery endpoints, three robots, and their remaining paths, plus a metrics panel and per-robot fleet status. It sends commands to FastAPI over REST (dispatch a task, add an obstacle by click, start/pause/step/reset) and receives all simulation state over one WebSocket connection. It holds **no independent simulation state** — it never computes a path, assigns a task, or moves a robot itself; it is a pure renderer of server-authoritative state. This means the browser can never visually drift from what the backend actually decided, which is also why the WebSocket snapshot, not browser-side interpolation, is the single source of truth for what's "really" happening.

## FastAPI (`app/main.py`)

FastAPI is the only layer that knows about HTTP and WebSockets. It exposes:

- **REST commands**: create a task (`POST /api/tasks`), add/remove a dynamic obstacle (`POST`/`DELETE /api/obstacles...`), and control the simulation (`start`/`pause`/`reset`/`tick`).
- **REST queries**: `/health`, `/api/state`, `/grid`, `/robots`, `/tasks`, `/metrics` — all read-only views over `SimulationEngine.snapshot()`.
- **One WebSocket**, `/ws/simulation` — sends the current snapshot immediately on connect, then receives pushed updates via `ConnectionManager.broadcast` whenever state changes.

A FastAPI `lifespan` context manager starts a single background `asyncio.Task` (`simulation_loop`) when the app boots and cancels it cleanly on shutdown. That loop is the only place real time enters the system: it `await`s `asyncio.sleep(TICK_SECONDS)` (500ms) between opportunities to advance the simulation, and only calls `engine.tick()` while `engine.running` is true.

## Backend-authoritative state and asyncio locking

There is exactly one `SimulationEngine` instance, held as a module-level object in `app/main.py`, and exactly one `asyncio.Lock` (`state_lock`) guarding it. Every code path that mutates engine state — every REST command handler, and the background tick loop — acquires that same lock before calling into the engine and only releases it after the mutation completes. This matters because FastAPI can be handling several concurrent requests on the same event loop: without the lock, a REST-triggered `add_task` and an automatic `tick()` firing at the same moment could interleave and corrupt in-progress state (e.g., a robot's `path` being read mid-mutation). The lock serializes all of that into one consistent order, so the "authoritative" state at any instant is well-defined and every connected client is broadcast the same sequence of snapshots — there is no per-client divergent view.

"Backend-authoritative" also describes the trust boundary: the browser never computes anything that affects simulation truth. Every number and position a user sees came from a `snapshot()` call on the one server-side engine instance, never from client-side prediction or interpolation.

## SimulationEngine and its collaborators

`SimulationEngine` (`app/services/simulation/engine.py`) owns the mutable state — a `Grid`, three `Robot`s, and the current `DeliveryTask` list — and orchestrates three collaborators that are otherwise independent of each other and of FastAPI:

- **Assignment** (`assign_tasks`, implemented directly on the engine): for each queued task, runs A* from every idle robot to the pickup and assigns the nearest reachable one.
- **Pathfinding** (`app/services/pathfinding/`): `astar` and `dijkstra`, both operating purely on `Grid`/`Position` with no knowledge of robots, tasks, or the engine.
- **Collision coordination** (`app/services/coordination/collision.py`): `resolve_moves`, which takes robots and their proposed next cells and returns conflict-free accepted moves — it has no knowledge of tasks, pathfinding, or how the intents were produced.

`engine.tick()` is the core simulation step: re-run assignment, collect each robot's proposed next cell, resolve conflicts, apply accepted moves, handle any pickup/delivery arrivals, assert the collision-free invariant, and re-run assignment once more (so a robot that just freed up can grab a queued task in the same tick). It's a plain synchronous method with no `sleep`, no clock read, and no `async` — determinism is a first-class design goal, not an accident, and it's what makes the seeded 250-tick property test reproducible on every run.

## Domain models (`app/models/`)

`Position`, `Grid`, `Robot`, `DeliveryTask`, and `PathResult` are plain `@dataclass` types with no framework dependency. They are the shared vocabulary every other layer speaks: pathfinding consumes `Grid`/`Position` and returns `PathResult`; the engine consumes and mutates `Robot`/`DeliveryTask`; the API layer serializes all of it via `asdict()` plus small position-formatting helpers in `snapshot()`. Keeping these framework-free is what lets `tests/test_pathfinding.py`, `test_assignment.py`, and `test_collision.py` construct scenarios directly out of dataclasses with no FastAPI app, database, or event loop in the loop at all.

## In-memory state and its consequence

There is no database and no persistence layer. `SimulationEngine.reset()` rebuilds the grid and robots from `default_scenario()` and empties the task list — this is also exactly what happens implicitly on process start. The upside is simplicity and perfect reproducibility for a portfolio/interview demo: a fresh process is always a known, deterministic starting state. The direct consequence is that **restarting the backend discards all simulation history** — there is no "resume where you left off," and this design intentionally does not attempt to hide that tradeoff.

## Single-process limitation

Because `SimulationEngine` is one Python object behind one `asyncio.Lock` in one process, this architecture cannot be scaled horizontally (multiple Uvicorn/Gunicorn worker processes, or multiple machines behind a load balancer) without a redesign. Two workers would each hold their own independent copy of the simulation and silently diverge — the lock only serializes access *within* a single process's memory space. Making this multi-process-safe would require either designating exactly one process as the sole simulation owner (with all others acting as pure request-forwarding relays) or moving state into a shared, durable store (e.g., Redis or a database) with proper cross-process concurrency control and an ordered command log. Neither is implemented here — it's called out explicitly rather than glossed over, because "how would you scale this" is a predictable interview follow-up.

## Determinism as a design property, not a side effect

Every random choice in the system is either absent or explicitly seeded (`random.seed(2026)` in the safety-property test). Tie-breaking in assignment (`robot_id`) and in collision arbitration (ascending ID priority order) is fixed and deterministic rather than relying on set/dict iteration order or timing. This is what allows the automated test suite — especially the 250-tick property test — to assert exact, repeatable outcomes instead of merely "usually correct" behavior, and it's a property worth naming explicitly in an interview: determinism was a design constraint applied from the domain layer outward, not bolted on for testing afterward.
