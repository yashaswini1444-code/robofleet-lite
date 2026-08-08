from app.models import Position, Robot

def resolve_moves(robots: list[Robot], intents: dict[str, Position]) -> dict[str, Position]:
    """Resolve one tick by robot-id priority; prevent vertices and edge swaps."""
    starts = {r.id: r.position for r in robots}
    accepted: dict[str, Position] = {}
    reserved: set[Position] = set()
    for robot in sorted(robots, key=lambda r: r.id):
        destination = intents.get(robot.id, robot.position)
        conflict = destination in reserved
        for other_id, other_dest in accepted.items():
            if destination == starts[other_id] and other_dest == robot.position and destination != robot.position:
                conflict = True
        # A robot may not enter a cell whose current occupant is not moving away safely.
        occupant = next((oid for oid, pos in starts.items() if pos == destination and oid != robot.id), None)
        if occupant and occupant not in accepted:
            conflict = True
        if occupant and accepted.get(occupant) == destination:
            conflict = True
        if conflict:
            destination = robot.position
            robot.conflicts += 1
        # If waiting now conflicts with an earlier move, revoke that lower-safety move.
        if destination in reserved:
            mover = next(i for i, p in accepted.items() if p == destination)
            accepted[mover] = starts[mover]
            reserved.discard(destination)
        accepted[robot.id] = destination
        reserved.add(destination)
    return accepted

