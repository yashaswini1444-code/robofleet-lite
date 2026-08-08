import pytest
from app.models import Grid, Position
from app.services.pathfinding import astar, dijkstra

@pytest.mark.parametrize("planner", [astar, dijkstra])
def test_optimal_path(planner):
    grid = Grid(5, 5, {Position(2, y) for y in range(4)})
    result = planner(grid, Position(0, 0), Position(4, 0))
    assert result.reachable and result.path_length == 12
    assert result.path[0] == Position(0, 0) and result.path[-1] == Position(4, 0)

@pytest.mark.parametrize("planner", [astar, dijkstra])
def test_start_goal_and_invalid(planner):
    grid = Grid(3, 3)
    assert planner(grid, Position(1, 1), Position(1, 1)).path_length == 0
    assert not planner(grid, Position(-1, 0), Position(1, 1)).reachable

def test_algorithms_return_equal_optimal_length():
    grid = Grid(10, 10, {Position(4, y) for y in range(9)})
    assert astar(grid, Position(0, 0), Position(9, 0)).path_length == dijkstra(grid, Position(0, 0), Position(9, 0)).path_length

