from app.models import Position

def reconstruct(came_from: dict[Position, Position], current: Position) -> list[Position]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    return list(reversed(path))

def validate(grid, start: Position, goal: Position) -> bool:
    return grid.is_walkable(start) and grid.is_walkable(goal)

