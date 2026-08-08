# Evaluation

Run `python -m scripts.evaluate` from the repository root. It executes A* and Dijkstra on two deterministic default-warehouse routes, recording reachability, optimal path length, and expanded nodes. It then dispatches three jobs, advances exactly 100 ticks, and records backend simulation metrics. The generated `docs/evaluation-results.json` is the source of reported values.

The evaluation deliberately excludes wall-clock planning times from the committed comparison because they are machine-dependent; the API and dashboard still measure actual per-plan time. It is a reproducible functional comparison, not a claim about production robot throughput.
