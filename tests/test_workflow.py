from datetime import datetime,timedelta,timezone
from app.models import Ticket,Event,LoginSession,User

def assign(c,t,worker=4):
    return c['admin'].post(f"/api/tickets/{t['id']}/actions",json={'action':'assign','version':t['version'],'assignee_id':worker,'scheduled_at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(),'note':'例行维修'})

def act(client,t,action,note=''):
    return client.post(f"/api/tickets/{t['id']}/actions",json={'action':action,'version':t['version'],'note':note})

def test_full_workflow_with_rework_and_rating(clients,ticket):
    c=clients;t=assign(c,ticket).json();assert t['status']=='assigned'
    t=act(c['repair'],t,'start').json();assert t['status']=='working'
    t=act(c['repair'],t,'finish','更换密封圈').json();assert t['status']=='review'
    t=act(c['student'],t,'reject','仍然漏水').json();assert t['status']=='working'
    t=act(c['repair'],t,'finish','重新紧固接头').json()
    t=act(c['student'],t,'accept').json();assert t['status']=='completed'
    assert c['student'].post(f"/api/tickets/{t['id']}/evaluation",json={'score':5,'comment':'处理及时'}).status_code==201
    assert c['student'].post(f"/api/tickets/{t['id']}/evaluation",json={'score':5}).status_code==409
    detail=c['admin'].get(f"/api/tickets/{t['id']}").json()
    assert len(detail['events'])==7
    stats=c['admin'].get('/api/statistics').json()
    assert stats['completed']==1 and stats['open']==0 and stats['average_hours']>=0 and stats['average_rating']==5

def test_horizontal_and_vertical_access(clients,ticket):
    c=clients;url=f"/api/tickets/{ticket['id']}"
    assert c['other'].get(url).status_code==404
    assert c['repair'].get(url).status_code==404
    assert c['other'].get('/api/tickets').json()['total']==0
    assert c['student'].get('/api/admin/users').status_code==403
    assert c['student'].get('/api/admin/export').status_code==403
    assert act(c['student'],ticket,'start').status_code==409

def test_optimistic_version_and_duplicate_operation(clients,ticket):
    r=assign(clients,ticket);assert r.status_code==200
    assert assign(clients,ticket).status_code==409
    with clients['factory']() as db:assert db.query(Event).count()==2

def test_reassignment_and_old_worker_revoked(clients,ticket):
    t=assign(clients,ticket).json()
    assert assign(clients,t,worker=5).status_code==200
    assert clients['repair'].get(f"/api/tickets/{t['id']}").status_code==404
    assert clients['repair2'].get(f"/api/tickets/{t['id']}").status_code==200

def test_cancel_and_illegal_transition(clients,ticket):
    assert act(clients['student'],ticket,'accept').status_code==409
    t=act(clients['student'],ticket,'cancel').json();assert t['status']=='cancelled'
    assert assign(clients,t).status_code==409

def test_past_schedule_rejected(clients,ticket):
    r=clients['admin'].post(f"/api/tickets/{ticket['id']}/actions",json={'action':'assign','version':1,'assignee_id':4,'scheduled_at':'2020-01-01T00:00:00Z'})
    assert r.status_code==422

def test_required_finish_note(clients,ticket):
    t=assign(clients,ticket).json();t=act(clients['repair'],t,'start').json()
    assert act(clients['repair'],t,'finish').status_code==422

def test_date_building_category_filters(clients,ticket):
    c=clients['admin']
    assert c.get('/api/statistics?building=1&category=water').json()['total']==1
    assert c.get('/api/statistics?building=999').json()['total']==0
    assert c.get('/api/statistics?category=electric').json()['total']==0
    assert c.get('/api/statistics?start=2099-01-01T00:00:00').json()['total']==0
    assert c.get('/api/tickets?page=0').status_code==422

def test_websocket_scoping(clients,ticket):
    with clients['student'].websocket_connect('/ws/dashboard') as ws:assert ws.receive_json()['total']==1
    with clients['other'].websocket_connect('/ws/dashboard') as ws:assert ws.receive_json()['total']==0
