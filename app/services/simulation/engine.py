from dataclasses import asdict
from time import perf_counter
from app.models import DeliveryTask, Position, Robot, RobotState, TaskState
from app.services.pathfinding import astar, dijkstra
from app.services.coordination.collision import resolve_moves
from .scenarios import default_scenario

class SimulationEngine:
    def __init__(self):
        self.running = False
        self.tick_count = 0
        self._task_sequence = 0
        self.reset()

    def reset(self):
        self.grid, self.robots = default_scenario()
        self.tasks: list[DeliveryTask] = []
        self.running = False
        self.tick_count = 0
        self._task_sequence = 0

    def plan(self, start: Position, goal: Position, algorithm="astar"):
        before = perf_counter()
        result = (astar if algorithm == "astar" else dijkstra)(self.grid, start, goal)
        result.planning_time_ms = (perf_counter() - before) * 1000
        return result

    def add_task(self, pickup: Position, delivery: Position) -> DeliveryTask:
        if pickup == delivery or not self.grid.is_walkable(pickup) or not self.grid.is_walkable(delivery):
            raise ValueError("Pickup and delivery must be distinct walkable cells")
        self._task_sequence += 1
        task = DeliveryTask(f"T{self._task_sequence}", pickup, delivery, sequence=self._task_sequence)
        self.tasks.append(task)
        self.assign_tasks()
        return task

    def assign_tasks(self):
        for task in sorted((t for t in self.tasks if t.state == TaskState.QUEUED), key=lambda t: t.sequence):
            candidates = []
            for robot in self.robots:
                if robot.state == RobotState.IDLE and robot.assigned_task_id is None:
                    route = self.plan(robot.position, task.pickup)
                    if route.reachable:
                        candidates.append((route.path_length, robot.id, robot, route))
            if not candidates:
                continue
            _, _, robot, route = min(candidates, key=lambda c: (c[0], c[1]))
            task.state, task.assigned_robot_id = TaskState.ASSIGNED, robot.id
            robot.assigned_task_id, robot.target = task.id, task.pickup
            robot.state = RobotState.MOVING_TO_PICKUP
            self._set_route(robot, route)
            self._handle_arrival(robot)

    def _set_route(self, robot, result):
        robot.path = result.path[1:] if result.reachable else []
        robot.last_path_length = result.path_length
        robot.last_planning_time_ms = result.planning_time_ms
        robot.blocked_reason = None if result.reachable else "No route to target"

    def _task(self, robot):
        return next(t for t in self.tasks if t.id == robot.assigned_task_id)

    def _handle_arrival(self, robot):
        if robot.target != robot.position:
            return
        task = self._task(robot)
        if robot.state in (RobotState.MOVING_TO_PICKUP, RobotState.REPLANNING) and task.state == TaskState.ASSIGNED:
            task.state = TaskState.PICKED_UP
            robot.state, robot.target = RobotState.MOVING_TO_DELIVERY, task.delivery
            self._set_route(robot, self.plan(robot.position, task.delivery))
        elif task.state == TaskState.PICKED_UP:
            task.state = TaskState.DELIVERED
            robot.tasks_completed += 1
            robot.state, robot.assigned_task_id, robot.target, robot.path = RobotState.IDLE, None, None, []

    def tick(self):
        self.assign_tasks()
        intents = {r.id: (r.path[0] if r.path else r.position) for r in self.robots}
        moves = resolve_moves(self.robots, intents)
        old = {r.id: r.position for r in self.robots}
        for robot in self.robots:
            new = moves[robot.id]
            if new != robot.position:
                robot.position = new
                robot.distance_moved += 1
                if robot.path and robot.path[0] == new:
                    robot.path.pop(0)
                robot.state = RobotState.MOVING_TO_PICKUP if self._task(robot).state == TaskState.ASSIGNED else RobotState.MOVING_TO_DELIVERY
            elif robot.assigned_task_id and robot.target != robot.position:
                robot.state = RobotState.WAITING
            if robot.assigned_task_id:
                self._handle_arrival(robot)
        assert len({r.position for r in self.robots}) == len(self.robots)
        for a in self.robots:
            for b in self.robots:
                assert not (a.id < b.id and old[a.id] == b.position and old[b.id] == a.position and a.position != old[a.id])
        self.tick_count += 1
        self.assign_tasks()
        return self.snapshot()

    def add_obstacle(self, p: Position):
        if not self.grid.is_inside(p) or self.grid.is_blocked(p) or p in self.grid.pickup_locations | self.grid.delivery_locations or p in {r.position for r in self.robots}:
            raise ValueError("Obstacle must be a free, non-endpoint, unoccupied cell")
        self.grid.dynamic_obstacles.add(p)
        for robot in self.robots:
            if p in robot.path:
                robot.state = RobotState.REPLANNING
                robot.replans += 1
                self._set_route(robot, self.plan(robot.position, robot.target))
                if not robot.path and robot.position != robot.target:
                    robot.state = RobotState.WAITING

    def remove_obstacle(self, p: Position):
        if p not in self.grid.dynamic_obstacles:
            raise KeyError("Dynamic obstacle not found")
        self.grid.dynamic_obstacles.remove(p)
        for robot in self.robots:
            if robot.assigned_task_id and (robot.blocked_reason or not robot.path):
                robot.replans += 1
                self._set_route(robot, self.plan(robot.position, robot.target))

    def compare(self, start, goal):
        return [self.plan(start, goal, name) for name in ("astar", "dijkstra")]

    def snapshot(self):
        def pos(p): return {"x": p.x, "y": p.y}
        robots = [{**asdict(r), "position": pos(r.position), "target": pos(r.target) if r.target else None,
                   "path": [pos(p) for p in r.path]} for r in self.robots]
        tasks = [{**asdict(t), "pickup": pos(t.pickup), "delivery": pos(t.delivery)} for t in self.tasks]
        completed = sum(r.tasks_completed for r in self.robots)
        return {"running": self.running, "tick": self.tick_count,
                "grid": {"width": self.grid.width, "height": self.grid.height,
                         "static_obstacles": [pos(p) for p in sorted(self.grid.static_obstacles)],
                         "dynamic_obstacles": [pos(p) for p in sorted(self.grid.dynamic_obstacles)],
                         "pickups": [pos(p) for p in sorted(self.grid.pickup_locations)],
                         "deliveries": [pos(p) for p in sorted(self.grid.delivery_locations)]},
                "robots": robots, "tasks": tasks,
                "metrics": {"ticks": self.tick_count, "tasks_completed": completed,
                            "distance_moved": sum(r.distance_moved for r in self.robots),
                            "replans": sum(r.replans for r in self.robots), "conflicts": sum(r.conflicts for r in self.robots)}}
