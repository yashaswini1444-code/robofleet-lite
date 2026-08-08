from dataclasses import dataclass, field

@dataclass(frozen=True, order=True)
class Position:
    """Grid coordinate: x is column, y is row, origin is top-left."""
    x: int
    y: int

@dataclass
class PathResult:
    path: list[Position] = field(default_factory=list)
    expanded_nodes: int = 0
    algorithm: str = ""
    planning_time_ms: float = 0.0

    @property
    def reachable(self) -> bool:
        return bool(self.path)

    @property
    def path_length(self) -> int | None:
        return len(self.path) - 1 if self.path else None

