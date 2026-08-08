from dataclasses import dataclass
from enum import StrEnum
from .common import Position

class TaskState(StrEnum):
    QUEUED = "QUEUED"
    ASSIGNED = "ASSIGNED"
    PICKED_UP = "PICKED_UP"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"

@dataclass
class DeliveryTask:
    id: str
    pickup: Position
    delivery: Position
    state: TaskState = TaskState.QUEUED
    assigned_robot_id: str | None = None
    sequence: int = 0

