from app.models import Position, Robot
from app.services.coordination.collision import resolve_moves

def robots(*positions): return [Robot(f"R{i+1}", p) for i,p in enumerate(positions)]

def test_same_cell_conflict():
    rs=robots(Position(0,1),Position(2,1)); moves=resolve_moves(rs,{"R1":Position(1,1),"R2":Position(1,1)})
    assert len(set(moves.values())) == 2

def test_edge_swap_prevented():
    rs=robots(Position(0,0),Position(1,0)); moves=resolve_moves(rs,{"R1":Position(1,0),"R2":Position(0,0)})
    assert not (moves["R1"]==Position(1,0) and moves["R2"]==Position(0,0))

def test_stationary_occupancy():
    rs=robots(Position(0,0),Position(1,0)); moves=resolve_moves(rs,{"R1":Position(1,0),"R2":Position(1,0)})
    assert len(set(moves.values())) == 2

def test_three_robot_contention_is_unique():
    rs=robots(Position(0,1),Position(2,1),Position(1,2)); moves=resolve_moves(rs,{r.id:Position(1,1) for r in rs})
    assert len(set(moves.values())) == 3
    assert sum(r.conflicts for r in rs) >= 2

