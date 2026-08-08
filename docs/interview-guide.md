# Interview guide

## The system from zero

The warehouse is a rectangular graph: walkable cells are vertices and four-direction moves are unit edges. BFS is sufficient for unweighted grids; Dijkstra generalizes to nonnegative weighted edges; A* adds a goal-directed heuristic. Here Dijkstra prioritizes `g`, while A* prioritizes `f=g+h`. Manhattan distance is admissible and consistent because one cardinal move changes it by at most one. Parent pointers reconstruct the optimal route.

A robot records position, route, target, task, operational state, distance, completion, replan, conflict, and planning metrics. A task is queued, assigned, picked up, then delivered. Assignment measures an A* route from every idle robot to the pickup, ignores unreachable robots, and selects `(distance, robot_id)` minimum.

Multi-agent movement introduces vertex collisions (same destination) and edge swaps (two robots exchange cells simultaneously). The backend gathers intentions, applies deterministic priority/reservations, and makes conflicts wait. Dynamic obstacles invalidate affected remaining routes; planning restarts from current position. This is safe local coordination, not complete MAPF, and adversarial corridors may deadlock.

FastAPI exposes command/query REST endpoints. WebSockets push authoritative snapshots so motion needs no polling. Canvas renders state but owns no physics. Tests exercise algorithms, lifecycle, REST, WebSocket, replanning, explicit conflicts, and 250 seeded ticks. Metrics describe simulation work, not physical performance.

## Common interview questions

- **Why A* instead of Dijkstra?** Its admissible heuristic directs exploration toward the goal while retaining optimality.
- **When does A* become Dijkstra?** When `h(n)=0` everywhere.
- **Why Manhattan distance?** It is the obstacle-agnostic lower bound for cardinal unit moves.
- **Can A* return a non-optimal route?** Not here with nonnegative costs and the consistent heuristic; an overestimating heuristic or incorrect termination can.
- **How are same-cell and edge-swap collisions prevented?** Backend intention arbitration reserves destinations and checks reverse edges before simultaneous application.
- **What happens in the same corridor?** Conflicts wait; the Lite policy can deadlock and has no completeness guarantee.
- **Could priority starve a robot?** Yes. Aging priorities or stronger MAPF planning would improve fairness.
- **Why no ROS?** This is a browser algorithms simulator with no hardware, sensors, or ROS graph to integrate.
- **What changes with real robots?** Continuous trajectories, control, localization uncertainty, safety envelopes, latency, fail-safe stops, and hardware integration.
- **What if localization is inaccurate?** This model cannot represent it; real systems need probabilistic state estimation and larger collision margins.
- **What happens when an obstacle appears?** It is validated, intersecting remaining routes replan from current positions, and unreachable robots safely wait.
- **Why WebSockets?** Server ticks produce unsolicited updates; a persistent duplex channel avoids repetitive polling overhead and lag.
- **How would 100 robots change the design?** Spatial partitioning, longer reservation horizons, fairness, efficient MAPF, a simulation actor, durable events, and load-tested fan-out.
- **Would prioritized planning always find a solution?** No, even when a joint solution exists.
- **What are CBS, D*, D* Lite, and MAPF?** MAPF is joint multi-agent path finding; CBS resolves inter-agent constraints at a high level; D*/D* Lite incrementally repair paths as costs change.
- **Main limitations?** Discrete perfect motion, in-memory single process, local priority coordination, and no physical uncertainty.

## Live-coding map

- Change the heuristic in `astar.py`; preserve admissibility if optimality matters.
- Add diagonals in `Grid.neighbors`, assign diagonal cost, and replace Manhattan with octile distance.
- Add a fourth start in `default_scenario` (the required default intentionally remains three).
- Change assignment ranking in `SimulationEngine.assign_tasks`.
- Change dimensions and walls in `default_scenario`.
- Add fixed obstacles there or call the obstacle REST API.
- Add a field to robot/engine aggregation, snapshot metrics, dashboard, and tests.
- Change movement priority in `resolve_moves`; preserve deterministic safety checks.

