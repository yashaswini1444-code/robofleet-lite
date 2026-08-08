from app.models import Grid, Position, Robot

def default_scenario() -> tuple[Grid, list[Robot]]:
    pickups = {Position(2, 2), Position(2, 11), Position(10, 2)}
    deliveries = {Position(17, 2), Position(17, 11), Position(10, 11)}
    walls = {Position(6, y) for y in range(14) if y not in (3, 10)}
    walls |= {Position(13, y) for y in range(14) if y not in (3, 10)}
    grid = Grid(20, 14, walls, set(), pickups, deliveries)
    robots = [Robot("R1", Position(1, 1)), Robot("R2", Position(1, 12)), Robot("R3", Position(10, 7))]
    return grid, robots

