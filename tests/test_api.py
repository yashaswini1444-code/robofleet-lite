from fastapi.testclient import TestClient
from app.main import app

def test_smoke_and_assets():
    with TestClient(app) as c:
        assert c.get('/health').json()=={'status':'ok'}
        assert c.get('/').status_code==200
        assert c.get('/static/app.js').status_code==200
        state=c.get('/api/state').json(); assert len(state['robots'])==3

def test_task_tick_compare_and_validation():
    with TestClient(app) as c:
        c.post('/api/simulation/reset')
        created=c.post('/api/tasks',json={'pickup':{'x':2,'y':2},'delivery':{'x':17,'y':2}})
        assert created.status_code==201 and created.json()['tasks'][0]['id']=='T1'
        assert c.post('/api/simulation/tick').status_code==200
        comparison=c.post('/api/pathfinding/compare',json={'start':{'x':1,'y':1},'goal':{'x':2,'y':2}}).json()
        assert [x['algorithm'] for x in comparison]==['astar','dijkstra']
        assert c.post('/api/tasks',json={'pickup':{'x':2,'y':2},'delivery':{'x':2,'y':2}}).status_code==400

def test_websocket_initial_snapshot():
    with TestClient(app) as c:
        with c.websocket_connect('/ws/simulation') as ws:
            assert len(ws.receive_json()['robots'])==3
