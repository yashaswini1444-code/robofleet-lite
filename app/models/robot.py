from dataclasses import dataclass, field
from enum import StrEnum
from .common import Position

class RobotState(StrEnum):
    IDLE = "IDLE"
    MOVING_TO_PICKUP = "MOVING_TO_PICKUP"
    MOVING_TO_DELIVERY = "MOVING_TO_DELIVERY"
    WAITING = "WAITING"
    REPLANNING = "REPLANNING"

@dataclass
class Robot:
    id: str
    position: Position
    state: RobotState = RobotState.IDLE
    assigned_task_id: str | None = None
    path: list[Position] = field(default_factory=list)
    target: Position | None = None
    distance_moved: int = 0
    tasks_completed: int = 0
    replans: int = 0
    conflicts: int = 0
    last_planning_time_ms: float = 0.0
    last_path_length: int | None = None
    algorithm: str = "astar"
    blocked_reason: str | None = None

