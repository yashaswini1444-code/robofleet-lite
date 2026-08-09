# Portfolio Summary

Ready-to-paste descriptions of RoboFleet Lite for a resume, LinkedIn, a GitHub profile, or answering "tell me about a project" cold. Every figure here (test count, tick count, algorithm names) is verifiable directly in the repository — nothing is estimated or rounded up for effect.

## One-line description

A FastAPI + WebSocket multi-robot warehouse simulator with from-scratch A*/Dijkstra path planning, nearest-robot task assignment, and collision-safe real-time coordination for three robots.

## 50-word version

RoboFleet Lite is a browser-based warehouse simulator where a FastAPI backend runs from-scratch A* and Dijkstra to assign delivery jobs to the nearest available robot, arbitrates every robot's moves each tick to prevent same-cell and edge-swap collisions, and streams live state to a canvas dashboard over WebSockets.

## 100-word version

RoboFleet Lite is a backend-authoritative multi-robot warehouse path-planning simulator. Three robots pick up and deliver jobs on a 2D grid; a FastAPI backend runs A* (compared against a from-scratch Dijkstra baseline) to assign each new job to the nearest reachable idle robot, then arbitrates all robots' proposed moves every simulation tick to make same-cell and edge-swap collisions structurally impossible rather than merely unlikely. Obstacles can be inserted mid-run and force affected robots to replan live from their current position. All state streams to a vanilla-JS canvas dashboard over WebSockets, so the browser only ever renders server truth. It's covered by 20 automated tests, including a seeded 250-tick multi-agent safety property test, run in CI on every push.

## Technologies

Python, FastAPI, WebSockets (native ASGI, plus the `websockets` client library in tests), Pydantic, Uvicorn, `asyncio` (locks, background tasks, lifespan management), `heapq`-based A*/Dijkstra implemented from scratch, HTML5 Canvas, vanilla JavaScript, CSS, pytest, GitHub Actions CI.

## Engineering challenges (and how they were solved)

- **Preventing collisions between simultaneously-moving agents, not just detecting them after the fact.** Solved with a per-tick conflict-arbitration pass (`resolve_moves`) that reserves destinations by priority order and explicitly checks for the edge-swap case (two robots passing through each other), which a naive "is this cell occupied" check misses entirely.
- **Keeping the simulation deterministic while serving concurrent async HTTP/WebSocket traffic.** Solved by keeping `SimulationEngine.tick()` fully synchronous and side-effect-free with respect to time (no `sleep`, no clock read), and pushing all real concurrency handling — a single `asyncio.Lock` around every mutation — into the thin FastAPI layer above it.
- **Replanning without ever letting a robot "teleport."** Obstacle-triggered replans always route from the robot's actual current cell to its existing target, never from the original task start, verified by a lifecycle test that checks incremental position advancement rather than a single before/after snapshot.
- **Proving the real network path works, not just the in-process test client.** FastAPI's `TestClient` handles WebSockets in-process and bypasses the real HTTP Upgrade handshake; a dedicated test boots actual Uvicorn as a subprocess and connects with the `websockets` client library, which caught a genuine Uvicorn WebSocket dependency gap during development (fixed in commit `a11c9a0`).
- **Making a safety property testable at scale, not just spot-checkable.** A seeded, semi-randomized 250-tick run with 12 dispatched tasks asserts the "no two robots ever share a cell, no edge swaps ever occur" invariant after every single tick, rather than relying on a handful of hand-built scenarios to catch coordination bugs.

## Three strongest resume bullets

1. Built RoboFleet Lite, a FastAPI + WebSocket multi-robot warehouse simulator that assigns delivery tasks to the nearest available robot via from-scratch A* (with a Dijkstra comparison) and arbitrates every simultaneous robot move to structurally prevent same-cell and edge-swap collisions.
2. Designed a backend-authoritative simulation engine with deterministic, lock-protected ticks, live dynamic-obstacle insertion with automatic route replanning, and a real-time browser dashboard streaming robot paths, planning time, and task metrics over WebSockets.
3. Verified correctness with 20 automated pytest tests spanning pathfinding optimality, task assignment, collision arbitration, obstacle replanning, REST/WebSocket contracts, and a seeded 250-tick multi-agent safety property, all running in CI on every push.

## LinkedIn project description

**RoboFleet Lite — Multi-Robot Warehouse Path-Planning Simulator**

Built a browser-based warehouse simulator to explore multi-agent coordination end to end: from-scratch A* and Dijkstra path planning, nearest-available-robot task assignment, and a per-tick collision-arbitration system that makes same-cell and edge-swap collisions between robots structurally impossible rather than just unlikely. The FastAPI backend is the single source of truth — it streams every state change to a live canvas dashboard over WebSockets, so the UI never computes or predicts anything itself. Obstacles can be added mid-simulation and force affected robots to replan their route live, without ever teleporting. Backed by 20 automated tests (including a seeded 250-tick safety-property test) running in CI on every push. Stack: Python, FastAPI, WebSockets, asyncio, vanilla JS/HTML5 Canvas, pytest, GitHub Actions.

## GitHub short description

Browser-based multi-robot warehouse path-planning simulator: A*/Dijkstra, nearest-robot task assignment, real-time collision-safe coordination, and a live WebSocket dashboard (FastAPI + vanilla JS).

*(This is already applied to the repository via `gh repo edit`.)*

## Skills demonstrated

- Graph search algorithm design and implementation from first principles (A*, Dijkstra, heuristic admissibility/consistency reasoning)
- Concurrency-safe backend design (`asyncio.Lock`, background task lifecycle, deterministic core logic separated from real-time orchestration)
- Real-time systems design (WebSocket push architecture vs. polling, broadcast fault-tolerance)
- API design (REST command/query separation, Pydantic request validation, meaningful HTTP status codes for domain errors)
- Multi-agent systems reasoning (conflict types, safety vs. completeness tradeoffs, priority-based coordination)
- Layered architecture and dependency inversion (framework-independent domain/algorithm code, testable in isolation)
- Test engineering across multiple levels: pure-function unit tests, integration tests via `TestClient`, a real-subprocess network test, and a seeded property-based invariant test
- Technical writing: documenting architecture, algorithm tradeoffs, and honest limitations for a technical audience

## Interview talking points (quick-reference)

- Lead with the collision-arbitration design — it's the most interesting engineering decision, not just "I used A*."
- Have the edge-swap explanation ready verbatim; it's the detail that signals you understand multi-agent coordination beyond a single-agent pathfinding demo.
- Name the limitation (safe but not complete, no MAPF guarantee) unprompted — it reads as engineering maturity, not a weakness.
- If asked "why no ROS / no real robots," answer directly: this is a software/algorithms simulator by design, and be ready to describe what would change with real hardware (localization uncertainty, continuous control, latency, safety envelopes).
- If asked to extend it live, the fastest, most legible change is adding diagonal movement (`Grid.neighbors` + heuristic swap) — it touches exactly the algorithm layer being discussed and takes minutes, not a rewrite.

See [docs/interview-guide.md](interview-guide.md) for the full 60-second/2-minute pitches, 50 Q&A, follow-ups, and live-coding prompts.
