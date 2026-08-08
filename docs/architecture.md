# Architecture

The browser communicates with FastAPI by REST for commands and WebSocket for pushed snapshots. FastAPI serializes access to one authoritative `SimulationEngine` with an `asyncio.Lock`. The engine owns grid, robot, task, and metric state; assignment, pathfinding, and collision code remain framework-independent and directly testable.

The application loop sleeps asynchronously for 500 ms between opportunities to tick. `engine.tick()` itself never sleeps, so tests can advance exact deterministic timesteps. Start, pause, reset, task, obstacle, and manual-tick mutations broadcast updated state.

In-memory state makes this portfolio simulator simple and reproducible. Restarting loses all state. A multi-process deployment cannot safely use this design unchanged: it would require one designated simulation actor or shared durable state, ordered commands, distributed client fan-out, and concurrency control across workers.

See the README architecture and lifecycle diagrams. `models` defines domain truth, `services/pathfinding` treats the grid as a graph, `services/coordination` arbitrates simultaneous intentions, `services/simulation` orchestrates ticks, and `app/main.py` adapts those capabilities to HTTP.

