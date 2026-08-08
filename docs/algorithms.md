# Algorithms

## Grid as graph

Each walkable cell is a vertex. Up, down, left, and right neighbors form unit-cost edges; diagonals are absent. Paths include start and goal, making movement count `len(path) - 1`.

## A*

A* stores best-known `g(n)`, uses Manhattan `h(n)=|x_goal-x|+|y_goal-y|`, and prioritizes `f(n)=g(n)+h(n)` in a heap. Manhattan never overestimates a four-direction unit-cost route, so it is admissible; adjacent estimates differ by at most edge cost, so it is consistent. With these assumptions, the first popped goal is optimal. Parent links reconstruct the path backward.

## Dijkstra and comparison

Dijkstra is the same shortest-path principle with priority equal to `g(n)`—equivalent to A* with `h=0`. Both are implemented directly with `heapq`, not an algorithm library. For nonnegative unit edges each returns the same optimal path length, although tie-breaking may select different equal-length paths. A* commonly expands fewer nodes but that is not guaranteed for every topology/tie order.

With `V` cells and `E` neighbor edges, heap implementations take `O((V+E) log V)` time and `O(V)` space in the worst case. On a rectangular four-neighbor grid, `E=O(V)`. Measured planning milliseconds wrap the deterministic core with `perf_counter`; correctness never depends on timing.

Invalid/blocked endpoints and unreachable goals return a structured unreachable result. Start-equals-goal returns a one-position, zero-length route.

## Multi-robot coordination

Assignment compares A* route lengths for all idle robots, ignores unreachable candidates, and breaks equal distances by ID. Per tick, deterministic priority reserves proposed destination cells, rejects duplicate destinations and A↔B edge swaps, and respects stationary occupancy. Conflicting robots wait. This safely handles local conflicts but is prioritized planning rather than complete MAPF: it can starve or deadlock in opposing narrow corridors and does not guarantee a solution when one exists.

