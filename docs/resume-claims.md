# Resume claim verification

Every RoboFleet Lite bullet on the resume, broken into its individual claims, each mapped to the implementation that makes it true, the automated test(s) that verify it, and concrete evidence (file/test names, not invented numbers).

### Claim: "Built a browser-based 2D warehouse grid simulator with obstacles, pickup points, and delivery points"

| | |
|---|---|
| Implementation | `app/models/grid.py` (`Grid`, `is_walkable`, `is_blocked`), `app/services/simulation/scenarios.py` (`default_scenario`: 20×14 grid, static wall layout, 3 pickup + 3 delivery cells), `app/web/index.html` / `app.js` (canvas rendering) |
| Automated test | `test_smoke_and_assets` (grid served and reachable via HTTP), `test_obstacles.py::test_reject_robot_endpoint_and_static_cells` (endpoints/static cells are distinct, protected cell types) |
| Evidence | Grid dimensions and obstacle/endpoint sets are defined in code, not generated at random; `docs/screenshot.png` is a live capture of the rendered grid with obstacles and endpoints visible |
| Status | VERIFIED |

### Claim: "coordinating three simulated robots in real time over WebSockets"

| | |
|---|---|
| Implementation | `default_scenario` instantiates exactly `Robot("R1", ...)`, `Robot("R2", ...)`, `Robot("R3", ...)`; `app/api/websocket.py` (`ConnectionManager`), `/ws/simulation` in `app/main.py`, background `simulation_loop` broadcasting every tick |
| Automated test | `test_websocket_initial_snapshot` (in-process), `test_real_uvicorn_websocket_upgrade_and_initial_snapshot` (real Uvicorn subprocess + real `websockets` client) — both assert `len(snapshot["robots"]) == 3` |
| Evidence | Robot count is a hardcoded scenario invariant, not a UI illusion; the subprocess test proves the real WebSocket upgrade handshake works, not just the in-process test client |
| Status | VERIFIED |

### Claim: "Implemented A* path planning with a Dijkstra-based comparison"

| | |
|---|---|
| Implementation | `app/services/pathfinding/astar.py`, `app/services/pathfinding/dijkstra.py` — both implemented directly with `heapq`, no pathfinding library; `POST /api/pathfinding/compare` (`SimulationEngine.compare`) runs both on identical input |
| Automated test | `test_pathfinding.py::test_optimal_path[astar]` / `[dijkstra]` (parametrized), `test_algorithms_return_equal_optimal_length`, `test_start_goal_and_invalid[astar]` / `[dijkstra]`, `test_api.py::test_task_tick_compare_and_validation` (exercises the `/compare` endpoint) |
| Evidence | `docs/evaluation-results.json` (reproducible via `python -m scripts.evaluate`): on the default cross-map scenario A* expands 149 nodes vs. Dijkstra's 244 for the same 26-length optimal path; on a short route, 4 vs. 10 nodes for the same 2-length path — a real, reproducible expansion-count comparison, not a timing claim |
| Status | VERIFIED |

### Claim: "assigning each incoming task to the nearest available robot"

| | |
|---|---|
| Implementation | `SimulationEngine.assign_tasks` (`app/services/simulation/engine.py`): A* from every idle, unassigned robot to the pickup; filters unreachable robots; selects `min((path_length, robot_id))` |
| Automated test | `test_assignment.py::test_nearest_reachable_robot_and_tie_break`, `test_queues_when_all_busy_then_assigns`, `test_full_lifecycle_without_teleporting` |
| Evidence | Tie-breaking by robot ID is deterministic and directly asserted; the full-lifecycle test checks incremental position movement, ruling out a "snap to destination" shortcut |
| Status | VERIFIED |

### Claim: "while preventing grid-cell collisions between robots"

| | |
|---|---|
| Implementation | `app/services/coordination/collision.py::resolve_moves` — priority-ordered per-tick arbitration preventing same-cell and edge-swap conflicts; `SimulationEngine.tick()` additionally runtime-asserts the invariant every tick |
| Automated test | `test_collision.py::test_same_cell_conflict`, `test_edge_swap_prevented`, `test_stationary_occupancy`, `test_three_robot_contention_is_unique`; `test_safety_property.py::test_seeded_multi_tick_collision_invariant` (250 seeded ticks, 12 dispatched tasks) |
| Evidence | The safety-property test checks the invariant after every one of 250 ticks, not a single crafted scenario — this is the strongest evidence in the suite for this specific claim |
| Status | VERIFIED |

### Claim: "Added dynamic obstacle insertion with automatic route recalculation"

| | |
|---|---|
| Implementation | `SimulationEngine.add_obstacle` / `remove_obstacle`; `POST /api/obstacles`, `DELETE /api/obstacles/{x}/{y}`; click-to-add wired in `app/web/app.js` |
| Automated test | `test_obstacles.py::test_obstacle_on_path_replans_without_moving`, `test_obstacle_off_path_does_not_replan_and_removal`, `test_reject_robot_endpoint_and_static_cells` |
| Evidence | Replanning is proven to originate from the robot's current cell (not the original start), and to leave unaffected robots untouched, at the test level — not just visually plausible on the dashboard |
| Status | VERIFIED |

### Claim: "a live dashboard displaying robot movement, path length, planning time, and completed tasks"

| | |
|---|---|
| Implementation | `SimulationEngine.snapshot()` includes per-robot `path`, `last_path_length`, `last_planning_time_ms`, `tasks_completed`, and fleet-wide `metrics` (ticks, tasks_completed, distance_moved, replans, conflicts); `app/web/app.js` renders all of it live over the WebSocket feed |
| Automated test | `test_websocket_initial_snapshot`, `test_smoke_and_assets` (`/api/metrics` reachable) |
| Evidence | `docs/screenshot.png` shows the live metrics panel (ticks, tasks completed, distance moved, replans, conflicts) and per-robot path rendering during an active simulation |
| Status | VERIFIED |

### Claim: "Wrote automated tests for the path-planning algorithm and collision-prevention logic"

| | |
|---|---|
| Implementation | N/A (this claim is about the test suite itself) |
| Automated test | `tests/test_pathfinding.py` (algorithm correctness/optimality), `tests/test_collision.py` (direct arbitration unit tests), `tests/test_safety_property.py` (continuous invariant across 250 ticks) — 20 tests total across the full suite including these |
| Evidence | `pytest -v` run locally: 20 passed; `.github/workflows/tests.yml` runs the identical suite in CI on Python 3.12 on every push to `main` |
| Status | VERIFIED |

## Notes on methodology

- No metric in this document or in `docs/evaluation-results.json` is estimated, rounded for effect, or extrapolated — every number is either a fixed scenario invariant (robot count, tick count, test count) or a value produced by actually running `scripts/evaluate.py` / `pytest`.
- Wall-clock planning-time (`planning_time_ms`) is real and measured with `perf_counter`, but is intentionally excluded from this document and from the committed evaluation comparison because it is machine-dependent; expanded-node count is used instead as the reproducible A*-vs-Dijkstra comparison metric.
- All verification here is scoped to a discrete software simulator. These statements make no claim about physical-robot deployment, hardware integration, or production autonomous-fleet performance.
