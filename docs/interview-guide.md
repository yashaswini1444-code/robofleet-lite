# Interview Guide

This is a talk-track for defending RoboFleet Lite in a technical interview: what to say when asked to explain it, the mechanics behind each design decision, and how to react to likely follow-ups or a live-coding twist. Every claim here is backed by code in this repository — file references are given so you can jump straight to the source.

---

## 1. The 60-second explanation

> "RoboFleet Lite is a backend-authoritative multi-robot warehouse simulator I built with FastAPI and WebSockets. Three simulated robots pick up and deliver jobs on a 2D grid. When a job comes in, the backend runs A* from every idle robot to the pickup point and assigns it to whichever robot has the shortest reachable route — I also implemented Dijkstra from scratch so I could compare the two on the same grid. Every simulation tick, the server resolves all three robots' proposed moves through a conflict-arbitration step that prevents them from landing on the same cell or swapping cells through each other, so collisions are structurally impossible rather than just visually avoided. You can also click the grid to drop an obstacle mid-simulation, which forces any robot whose path is blocked to replan live from its current position. State streams to a vanilla-JS canvas dashboard over a WebSocket, so what you see in the browser is exactly the server's authoritative state, not a client-side simulation. It's backed by 20 automated tests, including a seeded 250-tick multi-agent safety test, and CI runs the full suite on every push."

## 2. The 2-minute explanation

> "RoboFleet Lite models a warehouse as a grid graph. Walkable cells are vertices, and each robot can move one cardinal step — up, down, left, right — per tick, which is a unit-cost edge. On top of that grid I implemented A* and Dijkstra from scratch using `heapq`, not a library, because I wanted to be able to reason about and test every part of the search: the priority queue, the cost bookkeeping, and path reconstruction through parent pointers.
>
> Task assignment works by running A* from every currently idle robot to a new job's pickup cell, filtering out robots that can't reach it, and picking the one with the shortest route, breaking ties by robot ID for determinism. That's the 'nearest available robot' behavior.
>
> The harder engineering problem was coordinating three robots moving simultaneously without letting them collide. Each tick, every robot proposes its next cell based on its current path. A collision-arbitration step — `resolve_moves` — processes robots in priority order and rejects any proposed move that would land two robots on the same cell, or that would have two robots swap cells past each other in one tick (an edge swap, which is invisible to a naive 'is the cell occupied' check but very real physically). A rejected robot just waits one tick instead of moving; that's recorded as a conflict metric.
>
> On top of the static warehouse layout, I added dynamic obstacles: clicking a cell in the browser inserts a temporary obstacle, and any robot whose remaining path crosses it immediately replans from its current position — it never teleports or clips through the new obstacle.
>
> The backend is FastAPI. REST endpoints handle commands like creating a task, adding an obstacle, or starting/pausing the simulation, and a WebSocket pushes the full authoritative snapshot to every connected browser after each tick, so the dashboard never has to poll. All mutating access goes through a single `asyncio.Lock` around one in-memory `SimulationEngine`, which keeps the simulation deterministic and race-free within a single process.
>
> I tested this in layers: pure algorithm tests for A* and Dijkstra optimality, assignment tests for nearest-robot logic and tie-breaking, direct unit tests for the collision arbitrator covering same-cell, edge-swap, and stationary-occupancy conflicts, obstacle/replanning tests, FastAPI `TestClient` tests for the REST and WebSocket contracts, a real subprocess test that boots actual Uvicorn to exercise the real WebSocket upgrade path — because the FastAPI test client doesn't hit the network stack — and a seeded 250-tick property test asserting the 'no two robots ever share a cell' invariant holds continuously, not just in a single crafted scenario. All 20 tests run in GitHub Actions on every push."

## 3. Architecture explanation

> "It's a strict three-layer design: browser, FastAPI, and a plain-Python simulation core.
>
> The browser is a static HTML/CSS page with vanilla JavaScript (`app/web/`) that draws a canvas from whatever state it's given — it never computes movement, pathfinding, or collision logic itself, it's a renderer.
>
> `app/main.py` is the FastAPI layer. It exposes REST endpoints for commands (create a task, add/remove an obstacle, start/pause/reset/tick the simulation, compare A* vs Dijkstra) and one WebSocket endpoint, `/ws/simulation`, that a background asyncio loop broadcasts to every 500ms while the simulation is running. Every mutating call — REST or the tick loop — acquires the same `asyncio.Lock` before touching state and broadcasts the resulting snapshot afterward, so concurrent requests can't interleave and corrupt engine state, and every client sees the same sequence of snapshots.
>
> Underneath FastAPI is `SimulationEngine` (`app/services/simulation/engine.py`), which owns all mutable state — the grid, the three robots, and the task queue — and orchestrates three collaborator modules that know nothing about FastAPI or each other's internals: assignment (`assign_tasks`, inside the engine itself), pathfinding (`app/services/pathfinding/`, A* and Dijkstra), and collision coordination (`app/services/coordination/collision.py`, `resolve_moves`). `app/models/` defines the plain dataclasses — `Grid`, `Robot`, `DeliveryTask`, `Position`, `PathResult` — that all of those layers share.
>
> The key architectural property I'd highlight: nothing below `app/main.py` imports FastAPI. The domain and algorithms are framework-independent, which is why they're unit-testable in isolation and why `SimulationEngine.tick()` can be deterministic — it never sleeps or reads a clock; only the HTTP-layer loop supplies real time via `asyncio.sleep`."

## 4. A* explanation

> "A* is best-first search over the grid-as-graph, ordered by `f(n) = g(n) + h(n)`: `g(n)` is the exact cost of the cheapest known path from the start to `n` — here, just the number of steps, since every edge costs 1 — and `h(n)` is an estimate of the remaining cost from `n` to the goal. I use Manhattan distance, `|goal.x - n.x| + |goal.y - n.y|`, as `h`. It's implemented with `heapq` as a min-heap keyed on `(f, tie-breaker, position)` — the tie-breaker is a monotonically increasing counter so the heap never has to compare `Position` objects when `f` ties. `came_from` records parent pointers so the winning path can be reconstructed backward from the goal once it's popped. The function returns a `PathResult` with the reconstructed path (including both start and goal), the number of nodes expanded, and which algorithm produced it; if start or goal is blocked or off-grid, or the goal is unreachable, it returns an empty, unreachable result instead of raising."

## 5. Dijkstra explanation

> "Dijkstra is the same priority-queue shortest-path search with `h(n) = 0` — the priority is pure `g(n)`, the known cost so far, so it expands in order of distance from the start with no sense of direction toward the goal. I implemented it separately from A* (not as A* with a zero heuristic passed in) so both algorithms are independently readable and testable, but they share the same `reconstruct`/`validate` helpers so path reconstruction and input validation can't silently diverge between them. One detail worth knowing: my Dijkstra has a `if current_cost != cost[current]: continue` staleness check, because `heapq` doesn't support decrease-key — when a cheaper cost to a node is found, I push a new heap entry instead of updating the old one, so a stale, more expensive entry can still be sitting in the heap and needs to be skipped when it's eventually popped."

## 6. Nearest-robot assignment explanation

> "When a task is created, `assign_tasks` looks at every queued task in FIFO order (by a `sequence` counter) and, for each one, runs A* from every currently idle, unassigned robot to the task's pickup cell. Robots that can't reach the pickup are filtered out entirely rather than treated as infinitely far. Among the reachable candidates, it picks the minimum by `(path_length, robot_id)` — so the shortest route wins, and if two robots are exactly tied, the lower robot ID wins deterministically, which matters for reproducible tests and demos. If no robot is currently free, the task just stays `QUEUED` and gets picked up automatically the next time `assign_tasks` runs — which happens on task creation and on both ends of every `tick()`, so a robot that frees up mid-tick can immediately grab a waiting job in that same tick rather than waiting a full cycle."

## 7. Same-cell collision explanation

> "Every tick, each robot proposes its next cell — the head of its remaining path, or its current cell if it has no path. `resolve_moves` processes robots in a fixed priority order (ascending robot ID) and keeps a `reserved` set of cells already claimed by a higher-priority robot this tick. If a lower-priority robot proposes a destination that's already reserved, its move is rejected: it stays in place instead, and its `conflicts` counter increments. So two robots can never both be granted the same destination cell in the same tick — the arbitration makes it a `set`, and a same-cell collision is checked directly in `test_same_cell_conflict` and asserted globally every tick by `assert len({r.position for r in self.robots}) == len(self.robots)` in `SimulationEngine.tick()`."

## 8. Edge-swap collision explanation

> "An edge swap is when robot A moves into robot B's current cell in the same tick that B moves into A's current cell — they pass through each other. A naive 'is the destination occupied or reserved' check misses this entirely, because at the moment each move is proposed, the *destination* cell looks free (its occupant is also leaving). `resolve_moves` detects this explicitly: for a candidate move, it checks whether any already-accepted robot's destination equals *this* robot's current position while that robot's own current position equals *this* robot's destination — i.e., a genuine two-robot swap — and rejects it, forcing one side to wait. It's covered directly by `test_edge_swap_prevented` and by the seeded 250-tick property test, which checks the swap invariant across every consecutive pair of ticks, not just a single hand-built scenario."

## 9. Dynamic replanning explanation

> "Obstacles can be inserted at runtime — by clicking a cell in the dashboard or calling `POST /api/obstacles` — and `SimulationEngine.add_obstacle` first validates that the cell is empty, not a static wall, not a pickup/delivery endpoint, and not currently occupied by a robot. Once added, every robot is checked: if the new obstacle cell appears anywhere in a robot's *remaining* path, that robot is marked `REPLANNING`, its `replans` counter increments, and it gets a brand-new route planned with A* from its current position — not from where it started the original task — to its existing target. That's the 'no teleporting' guarantee: the robot only ever continues from where it physically is. If the new route comes back unreachable, the robot is set to `WAITING` with a human-readable `blocked_reason` instead of crashing or freezing silently. Removing an obstacle retries planning for any robot that's currently blocked or pathless, so it can resume automatically without user intervention."

## 10. FastAPI explanation

> "FastAPI is the HTTP/WebSocket layer, chosen because it gives async request handling, automatic request validation via Pydantic (`app/schemas/api.py`), and native WebSocket support in one framework, without needing a separate ASGI routing layer. I used its `lifespan` context manager to start a background `asyncio.Task` that runs the simulation tick loop for the life of the app and cancel it cleanly on shutdown, rather than relying on a startup/shutdown event pair. Every route that mutates state — creating a task, adding an obstacle, starting/pausing/resetting, manual tick — acquires the shared `asyncio.Lock` before calling into `SimulationEngine` and then broadcasts the resulting snapshot to WebSocket clients, so REST-triggered changes and the automatic tick loop can never interleave unsafely even though FastAPI can be handling multiple requests concurrently."

## 11. WebSocket explanation

> "The dashboard needs to reflect robot motion that happens on the server's own clock, not just in response to something the browser did — so REST alone would mean the browser polling on an interval, guessing at how often to ask. A WebSocket lets the server push a snapshot the instant it changes: `/ws/simulation` sends the full state immediately on connect, and a `ConnectionManager` (`app/api/websocket.py`) tracks every connected socket and broadcasts to all of them whenever the engine's state changes — after a manual tick, after an obstacle is added, and every automatic tick from the background loop. It broadcasts defensively: if `send_json` fails on a socket (client disconnected without a clean close), that socket is dropped from the client set instead of taking down the broadcast for everyone else. I test both the FastAPI `TestClient`'s in-process WebSocket handling and, separately, a real Uvicorn subprocess with the `websockets` client library, because `TestClient` doesn't actually exercise the real HTTP Upgrade handshake and I wanted proof the real network path works too."

## 12. Testing explanation

> "Tests are split by what they're proving, from pure logic outward to the network boundary:
>
> - `test_pathfinding.py` — A* and Dijkstra return equal-length optimal paths on shared scenarios, handle unreachable/invalid start-goal pairs, and are parametrized so both algorithms run through the same assertions.
> - `test_assignment.py` — nearest-reachable-robot selection, ID tie-breaking, queuing when every robot is busy, and a full pickup-to-delivery lifecycle test that checks the robot's position transitions incrementally rather than jumping straight to the destination (guards against teleporting bugs).
> - `test_collision.py` — same-cell conflicts, edge swaps, stationary occupancy, and three-robot contention over a single cell, asserting all resolved destinations are still unique.
> - `test_obstacles.py` — an obstacle placed on a robot's path forces a replan; one placed off-path doesn't; static cells, robot positions, and pickup/delivery endpoints are rejected as obstacle locations.
> - `test_safety_property.py` — a `random.seed(2026)`-seeded run that dispatches 12 tasks and ticks 250 times, asserting after *every single tick* that no two robots share a position and that no edge swap occurred between consecutive ticks. This is the strongest test in the suite because it's a property held over a long, semi-randomized run rather than one hand-picked scenario.
> - `test_api.py` — FastAPI `TestClient` smoke tests: health check, static assets, full REST flow (create task → tick → compare algorithms → reject an invalid same-cell task with 400), and the WebSocket's initial snapshot.
> - `test_uvicorn_websocket.py` — boots real Uvicorn as a subprocess on a free port and connects with the `websockets` client library, because `TestClient`'s WebSocket support is in-process and bypasses the actual ASGI WebSocket upgrade handshake; this test exists specifically to catch a real regression class (I hit and fixed a genuine Uvicorn WebSocket dependency gap, which is what commit `a11c9a0` addresses).
>
> All 20 tests pass in under 4 seconds locally and run in GitHub Actions (`.github/workflows/tests.yml`) on Python 3.12 on every push to `main`."

## 13. Limitations (say these before an interviewer finds them)

- **Not a complete MAPF solver.** Collision arbitration is one-tick, priority-based, and *safe* (no collisions, ever) but not *complete* — it can make a robot wait indefinitely, or in principle deadlock, in an adversarial narrow-corridor layout, even when a joint solution exists. Real multi-agent pathfinding (MAPF) completeness needs something like Conflict-Based Search (CBS) or reservation tables over a time-expanded graph.
- **Single-process, in-memory state.** `SimulationEngine` is a plain Python object behind one `asyncio.Lock`. Restarting the process loses all state, and this design cannot be horizontally scaled across multiple worker processes without a redesign (shared/durable state, or a single designated simulation owner process).
- **Discrete, idealized motion.** Cells are discrete, moves are instantaneous per tick, localization is perfect, and there's no acceleration, momentum, battery, or sensor-noise model — this is a software/algorithms simulator, not a physical robot control stack.
- **No persistence, auth, or ROS integration.** No database, no user accounts, no hardware or ROS graph — state and history live only as long as the process runs.
- **Timing metrics are machine-dependent.** `planning_time_ms` is wall-clock via `perf_counter`; it's useful to *compare* A* vs Dijkstra on the same machine in the same run, but it's not a portable performance claim.

---

## 50 realistic interviewer questions with concise model answers

### Algorithms

1. **Why A* instead of plain Dijkstra?** A* uses Manhattan distance to bias the search toward the goal, so it typically expands fewer nodes than Dijkstra on the same grid, while still guaranteeing the optimal path because the heuristic is admissible.
2. **When does A* behave exactly like Dijkstra?** When `h(n) = 0` for every node — then `f(n) = g(n)` and the search order is identical.
3. **Why is Manhattan distance the right heuristic here?** Movement is four-directional with unit cost, so Manhattan distance is exactly the cost of an obstacle-free route — it can never overestimate the true remaining cost, which is what admissibility requires.
4. **What does admissible mean, precisely?** `h(n)` never overestimates the true cheapest cost from `n` to the goal, for every node `n`.
5. **What does consistent (monotone) mean, and does Manhattan distance satisfy it?** `h(n) <= cost(n, n') + h(n')` for every neighbor `n'` — moving one grid step changes Manhattan distance by exactly 1, which always satisfies that inequality with equality or slack, so yes.
6. **Why does admissibility matter for correctness?** With an admissible heuristic, A* is guaranteed to find an optimal path; with consistency, it also never needs to re-expand a node after it's been popped, which is why `expanded += 1` on pop is correct without re-processing.
7. **Could A* return the wrong path here?** Not with this heuristic and nonnegative unit costs. A non-admissible (overestimating) heuristic could cause A* to miss the optimal path.
8. **What data structure powers the frontier, and why?** A binary heap via `heapq`, keyed by `(f, tie-breaker, position)` — `O(log n)` push/pop, and the tie-breaker counter avoids ever comparing `Position` objects when two entries have equal `f`.
9. **How is the path reconstructed?** A `came_from` dict records, for each visited node, the node it was reached from; once the goal is popped, `reconstruct` walks parents back to the start and reverses the list.
10. **What's the time and space complexity?** With `V` vertices and `E` edges, `O((V + E) log V)` time and `O(V)` space for the heap and cost/parent maps — on a rectangular 4-neighbor grid, `E = O(V)`, so it's effectively `O(V log V)`.

### Assignment

11. **How does task assignment pick a robot?** It runs A* from every idle robot to the pickup, discards robots that can't reach it, and picks the minimum by `(path_length, robot_id)`.
12. **Why break ties by robot ID?** For determinism — repeated runs and tests get the same outcome instead of depending on dict/list ordering or randomness.
13. **What happens if no robot is free?** The task stays `QUEUED`; `assign_tasks` is called again at both ends of every tick, so it's picked up as soon as any robot becomes idle.
14. **Why call `assign_tasks` at both the start and end of `tick()`?** So a robot that becomes idle *during* this same tick (finishes a delivery) can be handed a queued task without waiting a full extra tick.
15. **Does assignment account for robots that are busy but about to become idle?** No — only `IDLE` robots with no `assigned_task_id` are candidates; a robot that's mid-route isn't considered even if it's closer, which is a simplifying design choice, not an oversight.
16. **What if the pickup and delivery cells are the same?** `add_task` rejects it up front with a `ValueError`, surfaced as HTTP 400.

### Collision & coordination

17. **How are same-cell collisions prevented?** `resolve_moves` reserves each accepted destination in a set; a later robot proposing an already-reserved cell has its move rejected and stays in place.
18. **How are edge swaps prevented?** Explicitly checked: if an already-accepted robot's destination is this robot's current cell, and that robot's current cell is this robot's destination, it's a swap and is rejected.
19. **What determines priority when two robots want the same cell?** Ascending robot ID — R1 beats R2 beats R3 — processed in that fixed order every tick.
20. **What happens to a robot whose move is rejected?** It stays at its current position for that tick and its `conflicts` counter increments; its path is unchanged so it retries next tick.
21. **Can a robot move into a cell another robot currently occupies?** Only if that occupant has already been resolved this same tick (lower ID, processed earlier) *and* actually moved elsewhere — otherwise it's treated as blocked, which is a conservative, safety-first rule.
22. **Is this coordination approach complete?** No — it's a safe, one-tick, priority-based scheme, not a full MAPF solver; it can leave a robot waiting indefinitely (starvation) in adversarial layouts.
23. **How would you make it fair, so a low-priority robot doesn't starve?** Add priority aging — a robot's effective priority increases the longer it's been forced to wait, so it eventually wins contested cells.
24. **How would you detect a deadlock?** Track consecutive ticks with zero net displacement across all active robots; past a threshold, flag it and either replan or force a priority override.
25. **Is there a global invariant you assert on every tick?** Yes — `SimulationEngine.tick()` asserts all robot positions are pairwise distinct and that no two robots swapped cells, as a runtime safety net in addition to the dedicated tests.

### Dynamic obstacles

26. **What happens when an obstacle is added on a robot's path?** That robot is marked `REPLANNING`, its `replans` counter increments, and A* replans from its *current* cell to its existing target.
27. **What if the obstacle isn't on any robot's path?** Nothing changes for any robot — only paths that actually intersect the new obstacle are affected.
28. **What if the robot becomes unreachable after replanning?** It's set to `WAITING` with a `blocked_reason`; it doesn't error, crash, or vanish.
29. **What happens when an obstacle is removed?** Any robot that's currently blocked or pathless retries planning automatically.
30. **Can you place an obstacle on a robot or an endpoint?** No — `add_obstacle` rejects cells that are static walls, pickup/delivery endpoints, or currently occupied by a robot, raising a `ValueError` (HTTP 409 via the API).
31. **Does a robot ever teleport when replanning?** No — it always replans from `robot.position`, its actual current cell, never from the original task's start.

### Backend / architecture

32. **Why FastAPI over Flask/Django?** Native async and WebSocket support in one framework, plus automatic request validation via Pydantic models, which matches a simulator that needs both request/response REST and a persistent push channel.
33. **Why WebSockets instead of polling?** The server produces state changes on its own clock (the tick loop); a WebSocket lets it push updates the instant they happen instead of the client guessing a poll interval.
34. **How do you prevent race conditions between REST calls and the tick loop?** A single `asyncio.Lock` wraps every state-mutating operation — REST handlers and the background tick loop both acquire it before touching `SimulationEngine`.
35. **Why is `SimulationEngine.tick()` synchronous and lock-free internally?** So its logic is deterministic and directly unit-testable without an event loop; the lock and timing live only in the FastAPI layer that calls it.
36. **What happens if the server restarts?** All state is lost — it's in-memory by design, which keeps the simulator simple and reproducible but isn't durable.
37. **Could this scale to multiple backend processes?** Not unchanged — you'd need either one process to own the simulation exclusively (with others as pure relays) or to move state into a shared, durable store with proper concurrency control.
38. **How does a broken WebSocket client get handled?** `ConnectionManager.broadcast` catches send failures per-socket and drops that client from the set without interrupting delivery to the others.
39. **Why do domain and algorithm modules avoid importing FastAPI?** So they're testable and reusable in complete isolation from the web framework — the tests for A*, Dijkstra, assignment, and collision arbitration never spin up an HTTP server.
40. **What's in the request/response contract?** Pydantic models in `app/schemas/api.py` validate task/obstacle/compare request bodies; invalid input (e.g. malformed coordinates) is rejected by FastAPI before it reaches the engine.

### Testing

41. **What's the strongest test in the suite and why?** The seeded 250-tick safety property test — it's not one hand-crafted scenario, it's an invariant (no shared cells, no edge swaps) checked continuously across a long, semi-randomized run with 12 concurrent tasks.
42. **Why do you have a test that boots real Uvicorn as a subprocess?** Because FastAPI's `TestClient` handles WebSockets in-process and never exercises the actual HTTP Upgrade handshake — I hit a real dependency gap in Uvicorn's WebSocket support that only showed up over a real socket, so I added a regression test that starts a real server and connects with the `websockets` client library.
43. **How do you test that A* and Dijkstra are both correct?** A parametrized test runs both algorithms against the same scenarios and asserts they return equal-length optimal paths, plus separate tests for unreachable and invalid start/goal cases.
44. **How do you test the assignment tie-break?** A scenario places two robots at equal A* distance from a pickup and asserts the lower-ID robot is chosen.
45. **How is "no teleporting" tested?** The full-lifecycle assignment test checks the robot's position advances one cell at a time across ticks rather than jumping straight from start to destination.
46. **What CI runs on every push?** `.github/workflows/tests.yml` runs the full pytest suite on Python 3.12.
47. **Do you have coverage numbers?** No formal coverage report is published — the suite is designed around behavior and invariants (optimality, safety, contracts) rather than a line-coverage target.

### Design tradeoffs / limitations

48. **Why exactly three robots, hardcoded?** It's the resume-scoped, interview-focused version — three keeps demos legible and coordination interesting without needing a scalability story; `default_scenario` is a natural place to parametrize robot count if that changed.
49. **What's the single biggest limitation you'd tell an interviewer up front?** Coordination is safe but not complete — it's not a real MAPF solver, so it can stall a robot indefinitely in an adversarial layout even though a solution exists.
50. **If you had another week, what's the first thing you'd add?** Priority aging for fairness, or a reservation-table/time-expanded approach so coordination gets closer to complete instead of just safe.

---

## 10 likely follow-up questions

1. **You said the heuristic is admissible — can you prove it in one line?** One cardinal move changes `|Δx| + |Δy|` by exactly 1, matching the true edge cost of 1, so Manhattan distance never overestimates the remaining cost.
2. **Your Dijkstra has a staleness check (`if current_cost != cost[current]: continue`) — why is that needed?** `heapq` has no decrease-key operation; when a cheaper cost to a node is found, a new heap entry is pushed rather than updating the old one in place, so a stale, more expensive duplicate can still surface later and must be skipped.
3. **Walk me through exactly what happens if two robots and a third robot all want the same cell in one tick.** They're processed in ID order; the first (lowest ID) reserves it, and the other two are each rejected in turn and stay in place — `test_three_robot_contention_is_unique` asserts the three resolved destinations are still pairwise distinct.
4. **Could your priority-by-ID scheme ever starve a robot forever?** In principle yes, in a specifically adversarial narrow-corridor layout where a higher-priority robot repeatedly re-contests the same cell; it's a known limitation I'd address with priority aging.
5. **Why is validation (`grid.is_walkable`) checked before search even starts, instead of just letting search fail naturally?** It's a fast, explicit rejection for a clearly invalid query (blocked or off-grid start/goal) rather than paying for a wasted search that would return nothing anyway.
6. **What guarantees that the dashboard is never out of sync with the backend?** The browser holds no independent simulation state — it only ever renders the most recent WebSocket snapshot, which is the same object `SimulationEngine.snapshot()` produces for every consumer.
7. **Why use `perf_counter` instead of `time.time()` for planning time?** `perf_counter` is monotonic and designed for measuring short durations; `time.time()` can jump due to system clock adjustments.
8. **What happens if a client sends a task with a pickup or delivery outside the grid?** `Grid.is_walkable` returns `False` for out-of-bounds cells, so `add_task` raises `ValueError`, which the API layer turns into a 400.
9. **How would you extend this to diagonal movement?** Add the four diagonal neighbors in `Grid.neighbors`, decide their cost (commonly `sqrt(2)` or a flat 1 if you want uniform cost), and switch the heuristic to octile or Chebyshev distance so it stays admissible for the new move set.
10. **If you had to support 50 robots instead of 3, what's the first thing that breaks?** The `O(idle robots × A*)` assignment cost per task grows linearly with fleet size, and one-tick priority arbitration gets far more contention-prone and starvation-prone at scale — that's where you'd want spatial partitioning and a proper reservation-based coordinator.

---

## 10 live-coding modifications you may be asked to make

1. **Add diagonal movement.** Extend `Grid.neighbors` (`app/models/grid.py`) with the four diagonal offsets, filtered through `is_walkable` like the existing four; decide and apply a cost for diagonal edges in both `astar.py` and `dijkstra.py`.
2. **Swap the heuristic.** Replace Manhattan distance in `astar.py` with Chebyshev or Euclidean distance; be ready to explain whether it's still admissible for the current (4-direction, unit-cost) move set.
3. **Change the tie-break in assignment.** In `SimulationEngine.assign_tasks`, change the `min(candidates, key=...)` to break ties by, say, fewest `tasks_completed` (load balancing) instead of robot ID.
4. **Add a fourth robot.** Add another `Robot(...)` entry to `default_scenario` (`app/services/simulation/scenarios.py`) and a fresh start cell; note the resume explicitly says "three," so mention that's a deliberate default, not a hard limit.
5. **Reshape the warehouse.** Edit the `walls` set and grid dimensions in `default_scenario` to add a new aisle or bottleneck, and predict how it changes contention at the choke point.
6. **Expose a new metric.** Add a field (e.g., average planning time) to `Robot` or the engine's aggregate, thread it through `snapshot()`, and render it on the dashboard (`app/web/app.js`) — this exercises the full stack from model to browser.
7. **Change movement priority.** In `resolve_moves` (`app/services/coordination/collision.py`), swap ascending-ID priority for something else (e.g., robots closer to their target win) while preserving the same-cell and edge-swap safety checks — a good prompt to test whether you understand *why* the existing checks can't be dropped.
8. **Add a REST endpoint.** Add `GET /api/robots/{robot_id}` returning a single robot's snapshot, including the FastAPI route, a 404 for an unknown ID, and a matching test in `test_api.py`.
9. **Make an obstacle removable by right-click / a second click.** Wire up the existing `DELETE /api/obstacles/{x}/{y}` endpoint to a new dashboard interaction in `app/web/app.js`.
10. **Add a test for a new invariant.** For example, assert that `distance_moved` never decreases and never exceeds `tick_count * 1` for a given robot — a good exercise in writing an invariant test in the same style as `test_safety_property.py`.
