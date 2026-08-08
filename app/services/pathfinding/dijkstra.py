import heapq
from itertools import count
from app.models import Grid, PathResult, Position
from .common import reconstruct, validate

def dijkstra(grid: Grid, start: Position, goal: Position) -> PathResult:
    if not validate(grid, start, goal):
        return PathResult(algorithm="dijkstra")
    serial = count()
    frontier = [(0, next(serial), start)]
    came_from: dict[Position, Position] = {}
    cost = {start: 0}
    expanded = 0
    while frontier:
        current_cost, _, current = heapq.heappop(frontier)
        if current_cost != cost[current]:
            continue
        expanded += 1
        if current == goal:
            return PathResult(reconstruct(came_from, current), expanded, "dijkstra")
        for neighbor in grid.neighbors(current):
            new_cost = current_cost + 1
            if new_cost < cost.get(neighbor, 10**18):
                cost[neighbor] = new_cost
                came_from[neighbor] = current
                heapq.heappush(frontier, (new_cost, next(serial), neighbor))
    return PathResult(expanded_nodes=expanded, algorithm="dijkstra")
