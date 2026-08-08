from dataclasses import dataclass, field
from .common import Position

@dataclass
class Grid:
    width: int
    height: int
    static_obstacles: set[Position] = field(default_factory=set)
    dynamic_obstacles: set[Position] = field(default_factory=set)
    pickup_locations: set[Position] = field(default_factory=set)
    delivery_locations: set[Position] = field(default_factory=set)

    def is_inside(self, p: Position) -> bool:
        return 0 <= p.x < self.width and 0 <= p.y < self.height

    def is_blocked(self, p: Position) -> bool:
        return p in self.static_obstacles or p in self.dynamic_obstacles

    def is_walkable(self, p: Position) -> bool:
        return self.is_inside(p) and not self.is_blocked(p)

    def neighbors(self, p: Position) -> list[Position]:
        candidates = (Position(p.x, p.y-1), Position(p.x-1, p.y), Position(p.x+1, p.y), Position(p.x, p.y+1))
        return [n for n in candidates if self.is_walkable(n)]

