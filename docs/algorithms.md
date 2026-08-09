# Algorithms

This document explains the search and coordination algorithms behind RoboFleet Lite in the depth an interviewer would expect: the graph model, the search theory, the actual implementation choices, complexity, and the honest limitations. Everything described here is implemented in `app/services/pathfinding/` and `app/services/coordination/collision.py` — nothing here is aspirational.

## Grid as graph

The warehouse is a rectangular grid, `GRID_WIDTH × GRID_HEIGHT` (20×14 in the default scenario). Every walkable cell — inside the grid bounds and not a static or dynamic obstacle — is a **vertex**. Two vertices share an **edge** if they are cardinal (up/down/left/right) neighbors and both are walkable; `Grid.neighbors()` generates exactly these, so a blocked cell never appears as a neighbor at all — it's removed from the graph entirely rather than made expensive to cross. There are no diagonal edges. Every edge has weight (cost) 1, since one tick moves a robot exactly one cell.

A path is a sequence of vertices `[start, ..., goal]`. Because the sequence includes both endpoints, the number of *moves* along a path of length `n` (as returned by `len(path)`) is `n - 1`; `PathResult.path_length` computes exactly that.

## Vertices and edges in this codebase

- **Vertex** = `Position(x, y)` — a frozen, hashable, orderable dataclass (`app/models/common.py`), so positions can be dictionary keys, set members, and heap tie-breakers.
- **Edge** = an adjacency implied by `Grid.neighbors(p)`, not a stored edge list — the graph is generated on demand from grid dimensions and the current obstacle sets, which is why dynamic obstacles can change the graph's shape between calls without any separate graph-rebuild step.
- **Edge weight** = always 1 (unit cost), since it's a uniform-cost grid with no terrain cost variation.

## BFS vs. Dijkstra vs. A*

All three are graph search algorithms that can find a shortest path on this grid — they differ in what they use to decide expansion order, which matters as soon as edge costs stop being uniform:

| Algorithm | Expansion order | Optimal on unit-cost grid? | Needs a heuristic? |
|---|---|---|---|
| **BFS** | FIFO queue (pure arrival order) | Yes, specifically *because* every edge costs the same | No |
| **Dijkstra** | Priority queue by `g(n)` (known cost so far) | Yes, for any nonnegative edge weights | No |
| **A\*** | Priority queue by `f(n) = g(n) + h(n)` | Yes, if `h` is admissible | Yes |

BFS would be sufficient here since every edge costs exactly 1 — it's the special case of Dijkstra where the priority queue degenerates to a plain FIFO queue. I implemented Dijkstra instead of BFS specifically so the algorithm generalizes immediately to weighted terrain (e.g., a "slow zone" cell costing more to cross) without a rewrite, and so it's a fair, like-for-like baseline to compare A* against. A* then adds goal-direction on top of that same priority-queue machinery.

## g(n), h(n), f(n)

- **`g(n)`** — the exact cost of the cheapest path found so far from the start to node `n`. In this implementation it's tracked in a `cost: dict[Position, int]` map and only ever decreases as better routes are discovered.
- **`h(n)`** — an estimate of the remaining cost from `n` to the goal. This is the only place A* and Dijkstra differ: A* uses Manhattan distance; Dijkstra effectively uses `h(n) = 0` everywhere (it's implemented by simply never adding a heuristic term, not by calling A* with a zero function).
- **`f(n) = g(n) + h(n)`** — the priority used to order the frontier heap. The node with the lowest `f` is expanded next. When `h(n) = 0` for all `n`, `f(n) = g(n)` and A* degenerates to exactly Dijkstra's behavior.

## The Manhattan heuristic

```
h(n) = |goal.x - n.x| + |goal.y - n.y|
```

This is the number of cardinal steps needed to close the coordinate gap between `n` and the goal *if nothing were in the way*. It's the natural heuristic for four-directional, unit-cost movement because it's exactly the cost of an unobstructed route — obstacles can only make the real cost equal to or greater than this estimate, never less.

## Admissibility and consistency

A heuristic is **admissible** if it never overestimates the true remaining cost to the goal, for every node. Manhattan distance is admissible here because any obstacle can only add detour steps, never remove required ones — the straight-line grid distance is a hard lower bound. Admissibility is what guarantees A* finds an *optimal* path: it will never let a node whose true best cost is higher than the current best solution jump the queue by looking artificially cheap.

A heuristic is **consistent** (or monotone) if, for every edge `(n, n')` with cost `c(n, n')`, `h(n) <= c(n, n') + h(n')`. Manhattan distance is consistent here because a single cardinal move changes the coordinate gap by exactly 1 in one axis — the heuristic can drop by at most 1 per unit-cost edge, so the inequality always holds (with equality along the direct route, and slack elsewhere). Consistency is the stronger, more useful property in practice: it guarantees `f(n)` is non-decreasing along any path the search explores, which means once a node is popped from the frontier its `g` value is already final — the algorithm never needs to re-expand a node after visiting it, simplifying the implementation to a plain "expand once" loop with no re-opening logic.

## Path reconstruction

Both algorithms use the same `reconstruct()` helper (`app/services/pathfinding/common.py`). While searching, every time a cheaper route to a neighbor is found, `came_from[neighbor] = current` records a single parent pointer — the edge the best-known route to `neighbor` arrived through. Once the goal is popped off the frontier, `reconstruct` walks `came_from` backward from the goal to the start, building the path in reverse, then reverses it once at the end. This is `O(path length)` and requires no extra search — the parent pointers are a byproduct of the search itself, not a second pass.

## Time and space complexity

With `V` vertices and `E` edges, a binary-heap-based Dijkstra/A* runs in **`O((V + E) log V)`** time and **`O(V)`** space for the cost map, parent map, and heap. On a rectangular 4-neighbor grid, every interior vertex has exactly 4 edges, so `E = O(V)`, simplifying the bound to **`O(V log V)`** time. Both implementations here use `heapq`, a binary heap, giving `O(log n)` push and pop.

One implementation detail with a complexity cost: `heapq` has no decrease-key operation. When a cheaper cost to an already-frontier node is found, a new entry is pushed rather than the old one updated in place, so the heap can carry stale duplicate entries. Dijkstra explicitly guards against acting on a stale entry with `if current_cost != cost[current]: continue`; A* achieves the same effect implicitly because a stale entry's `f` value is never better than the fresh one, so it can't win comparisons that matter, but it still costs a wasted pop. This trades a small amount of extra heap traffic for a much simpler implementation than a heap with proper decrease-key support (e.g., an indexed/pairing heap).

## A* vs. Dijkstra, compared directly

Both are implemented independently (not as one algorithm parameterized by the other) but share `reconstruct` and `validate`, so path reconstruction and input handling can't silently diverge between them. On this grid:

- **Optimality:** identical — both are guaranteed optimal for nonnegative unit-cost edges, and `test_algorithms_return_equal_optimal_length` asserts they return equal-length paths on the same scenario.
- **Path chosen:** can differ when multiple optimal-length paths exist — different expansion order can settle on a different (but equally short) route. Neither is "more correct"; the length is what's guaranteed equal, not the exact cell sequence.
- **Nodes expanded:** A* is typically lower because Manhattan distance biases expansion toward the goal instead of radiating outward uniformly. The committed evaluation (`docs/evaluation-results.json`, reproducible via `python -m scripts.evaluate`) shows this directly on the default scenario: A* expanded 149 nodes vs. Dijkstra's 244 for the same 26-length optimal route, and 4 vs. 10 nodes on a short 2-length route. This is a property of these two specific scenarios, not a universal guarantee — an adversarial layout could narrow or erase A*'s advantage.
- **Wall-clock planning time:** measured with `perf_counter` per request and exposed via the API/dashboard, but deliberately excluded from the committed evaluation comparison because it's machine-dependent — expanded-node count is the fair, reproducible comparison metric.

## Collision types in multi-robot coordination

Once multiple agents move on the same graph simultaneously, single-agent shortest-path search alone isn't enough — two independently-optimal paths can still collide:

- **Vertex (same-cell) conflict** — two robots' proposed next positions are the same cell in the same tick.
- **Edge-swap conflict** — robot A's destination is robot B's current cell, and robot B's destination is robot A's current cell, in the same tick: they'd pass through each other. This is invisible to a check that only asks "is the destination cell currently occupied?" since each robot's destination looks vacated from a purely positional snapshot.
- **Stationary occupancy** — a robot proposes moving into a cell whose current occupant isn't moving away this tick (or hasn't yet been resolved to move away), so entering would momentarily overlap them.

## Prioritized coordination

`resolve_moves` (`app/services/coordination/collision.py`) resolves all three conflict types with a single pass, processing robots in a fixed priority order (ascending robot ID) each tick:

1. Each robot proposes one destination (the next cell in its planned path, or its current cell if it has none).
2. Processing in priority order, a proposed destination is rejected — the robot stays put instead — if: it's already reserved by a higher-priority robot this tick (vertex conflict); it would complete a two-robot swap with an already-accepted move (edge-swap conflict); or its current occupant hasn't yet resolved to vacate it this same tick (stationary/unresolved occupancy).
3. A rejected robot's `conflicts` counter increments and it simply retries the same proposed move next tick, by which point the graph state (and the occupant's resolution) has moved forward.

This guarantees **safety** — no two robots are ever assigned the same or a swapped position, checked directly by `test_same_cell_conflict`, `test_edge_swap_prevented`, `test_stationary_occupancy`, `test_three_robot_contention_is_unique`, and continuously by the seeded 250-tick property test. It does **not** guarantee **completeness or fairness**: a lower-priority robot can, in principle, be blocked repeatedly by higher-priority robots reoccupying a contested cell, which is starvation, and in a sufficiently adversarial narrow-corridor layout the fleet can reach a state where no robot can make progress, which is deadlock. Neither is exercised by the current scenario, but neither is structurally impossible — this is a deliberate scope boundary, not a hidden bug.

## Limitations

- One-tick, priority-based, greedy conflict resolution — not a joint, globally optimal multi-agent plan.
- No fairness mechanism (e.g., priority aging), so persistent low-priority starvation is theoretically possible.
- No deadlock detection or recovery.
- No time-expanded reservation table — coordination only reasons about the *current* tick's proposed moves, not several ticks ahead.
- Assumes perfect, instantaneous execution of an accepted move; there's no model of partial-tick motion or collision margin.

## Alternatives worth knowing (not implemented here)

These are the standard next steps a real multi-agent pathfinding system would reach for, useful to name and contrast against but out of scope for this project:

- **MAPF (Multi-Agent Path Finding)** is the general problem name: finding a set of paths for multiple agents on a shared graph such that no two agents conflict, ideally minimizing total cost (sum of path lengths) or makespan (time until the last agent finishes).
- **CBS (Conflict-Based Search)** is a complete, optimal MAPF algorithm: it plans each agent's path independently, detects the first conflict between any pair, and branches into two constrained subproblems (one per agent, forbidding that conflict), rebuilding a constraint tree until no conflicts remain. It's what you'd reach for if you needed a *guaranteed* jointly-valid, optimal solution instead of a greedy, priority-based one.
- **D\*** and **D\* Lite** are incremental replanning algorithms for graphs whose costs change over time (e.g., newly discovered obstacles) — instead of re-running search from scratch after every change, they repair only the part of the search tree affected by the change. This project's obstacle handling instead does a full from-scratch A* replan on the affected robot's current position; D* Lite would be the natural upgrade if replanning cost or frequency became a bottleneck.
