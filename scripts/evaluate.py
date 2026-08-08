import json
from pathlib import Path
from app.models import Grid, Position
from app.services.pathfinding import astar, dijkstra
from app.services.simulation import SimulationEngine

def main():
    engine=SimulationEngine(); cases=[("default_cross_map",engine.grid,Position(1,1),Position(17,11)),("short_route",engine.grid,Position(1,1),Position(2,2))]
    output={"pathfinding":[]}
    for name,grid,start,goal in cases:
        row={"scenario":name}
        for planner in (astar,dijkstra):
            r=planner(grid,start,goal); row[r.algorithm]={"reachable":r.reachable,"path_length":r.path_length,"expanded_nodes":r.expanded_nodes}
        output["pathfinding"].append(row)
    for p,d in [(Position(2,2),Position(17,2)),(Position(2,11),Position(17,11)),(Position(10,2),Position(10,11))]: engine.add_task(p,d)
    for _ in range(100): engine.tick()
    output["simulation"]=engine.snapshot()["metrics"]
    target=Path("docs/evaluation-results.json"); target.parent.mkdir(exist_ok=True); target.write_text(json.dumps(output,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(output,indent=2))
if __name__=="__main__": main()
