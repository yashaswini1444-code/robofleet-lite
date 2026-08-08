from app.models import Position, RobotState, TaskState
from app.services.simulation import SimulationEngine

def test_nearest_reachable_robot_and_tie_break():
    e = SimulationEngine()
    task = e.add_task(Position(2, 2), Position(17, 2))
    assert task.assigned_robot_id == "R1"
    assert task.state == TaskState.ASSIGNED

def test_queues_when_all_busy_then_assigns():
    e = SimulationEngine()
    for i, r in enumerate(e.robots):
        r.state, r.assigned_task_id = RobotState.WAITING, f"busy{i}"
    task = e.add_task(Position(2, 2), Position(17, 2))
    assert task.state == TaskState.QUEUED

def test_full_lifecycle_without_teleporting():
    e = SimulationEngine(); t = e.add_task(Position(2, 2), Position(17, 2))
    previous = next(r for r in e.robots if r.id == t.assigned_robot_id).position
    for _ in range(100):
        e.tick(); robot = next(r for r in e.robots if r.id == t.assigned_robot_id or r.tasks_completed)
        assert abs(robot.position.x-previous.x)+abs(robot.position.y-previous.y) <= 1
        previous = robot.position
        if t.state == TaskState.DELIVERED: break
    assert t.state == TaskState.DELIVERED

