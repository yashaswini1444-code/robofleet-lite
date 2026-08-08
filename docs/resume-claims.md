# Resume claim verification

| Claim | Implementation | Tests | Status |
|---|---|---|---|
| Browser 2D grid, obstacles/endpoints, three robots, real-time WebSockets | `app/web/*`, `default_scenario`, `SimulationEngine.snapshot`, `/ws/simulation` | `test_smoke_and_assets`, `test_websocket_initial_snapshot` | VERIFIED |
| A* plus Dijkstra, nearest available robot, collision prevention | `astar`, `dijkstra`, `SimulationEngine.assign_tasks`, `resolve_moves` | `test_pathfinding.py`, `test_assignment.py`, `test_collision.py`, seeded safety property | VERIFIED |
| Dynamic obstacle replanning and live path/planning/task metrics | `SimulationEngine.add_obstacle`, `_set_route`, dashboard renderer | `test_obstacles.py`, API smoke tests | VERIFIED |
| Automated pathfinding and collision-prevention tests | `tests/test_pathfinding.py`, `tests/test_collision.py`, `tests/test_safety_property.py` | Full pytest suite | VERIFIED |

Verification is limited to this discrete software simulator; these statements make no physical-robot deployment claim.

