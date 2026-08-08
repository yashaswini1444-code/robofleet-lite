import random
from app.models import Position
from app.services.simulation import SimulationEngine

def test_seeded_multi_tick_collision_invariant():
    random.seed(2026); e=SimulationEngine()
    endpoints=list(e.grid.pickup_locations); destinations=list(e.grid.delivery_locations)
    for _ in range(12): e.add_task(random.choice(endpoints),random.choice(destinations))
    previous={r.id:r.position for r in e.robots}
    for _ in range(250):
        e.tick(); positions=[r.position for r in e.robots]
        assert len(positions)==len(set(positions))
        current={r.id:r.position for r in e.robots}
        for a in e.robots:
            for b in e.robots:
                assert not(a.id<b.id and previous[a.id]==current[b.id] and previous[b.id]==current[a.id] and previous[a.id]!=current[a.id])
        previous=current

