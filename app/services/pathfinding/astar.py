import heapq
from itertools import count
from app.models import Grid, PathResult, Position
from .common import reconstruct, validate

def astar(grid: Grid, start: Position, goal: Position) -> PathResult:
    """Optimal A*; returned path includes both start and goal."""
    if not validate(grid, start, goal):
        return PathResult(algorithm="astar")
    serial = count()
    frontier = [(0, next(serial), start)]
    came_from: dict[Position, Position] = {}
    cost = {start: 0}
    expanded = 0
    while frontier:
        _, _, current = heapq.heappop(frontier)
        expanded += 1
        if current == goal:
            return PathResult(reconstruct(came_from, current), expanded, "astar")
        for neighbor in grid.neighbors(current):
            new_cost = cost[current] + 1
            if new_cost < cost.get(neighbor, 10**18):
                cost[neighbor] = new_cost
                came_from[neighbor] = current
                h = abs(goal.x-neighbor.x) + abs(goal.y-neighbor.y)
                heapq.heappush(frontier, (new_cost+h, next(serial), neighbor))
    return PathResult(expanded_nodes=expanded, algorithm="astar")

