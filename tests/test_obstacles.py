from app.models import Position, RobotState
from app.services.simulation import SimulationEngine

def test_obstacle_on_path_replans_without_moving():
    e=SimulationEngine(); t=e.add_task(Position(2,2),Position(17,2)); r=next(x for x in e.robots if x.id==t.assigned_robot_id)
    before=r.position; blocked=r.path[0]; e.add_obstacle(blocked)
    assert r.position==before and r.replans==1 and blocked not in r.path

def test_obstacle_off_path_does_not_replan_and_removal():
    e=SimulationEngine(); t=e.add_task(Position(2,2),Position(17,2)); r=next(x for x in e.robots if x.id==t.assigned_robot_id)
    p=Position(19,13); e.add_obstacle(p); assert r.replans==0
    e.remove_obstacle(p); assert p not in e.grid.dynamic_obstacles

def test_reject_robot_endpoint_and_static_cells():
    e=SimulationEngine()
    for p in [e.robots[0].position, next(iter(e.grid.pickup_locations)), next(iter(e.grid.static_obstacles))]:
        try: e.add_obstacle(p)
        except ValueError: pass
        else: raise AssertionError("invalid obstacle accepted")

