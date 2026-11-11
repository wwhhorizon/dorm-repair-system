import io
import os
from datetime import datetime,timedelta,timezone
from PIL import Image
import pytest
from app.models import User,AuditLog,Prediction
from app.services import safe_cell
from ai_service.dataset import dataset
from ai_service.classifier import predict
from ai_service.main import app as ai_app
from fastapi.testclient import TestClient

@pytest.mark.parametrize('value',['=SUM(1,2)','+cmd','-1','@evil','  =x','\t=x','\r=x','\n=x'])
def test_csv_injection(value):assert safe_cell(value).startswith("'")

def test_csv_escaping_and_audit(clients):
    clients['student'].post('/api/tickets',json={'room_id':1,'description':'=SUM(1,2)\n故障说明','category':'other'})
    res=clients['admin'].get('/api/admin/export')
    assert res.status_code==200 and "'=SUM" in res.text and res.text.startswith('\ufeff')
    with clients['factory']() as db:assert db.query(AuditLog).filter_by(action='csv.export').count()==1

def test_ai_pipeline_and_distinct_auth(clients,ticket):
    c=clients['student'];headers={'X-Service-Token':os.environ['AI_SERVICE_TOKEN']}
    assert c.get('/api/ai/pending').status_code==401
    assert c.get('/api/ai/pending',headers=headers).json()[0]['id']==ticket['id']
    with TestClient(ai_app) as ai:
        assert ai.post('/predict',json={'text':ticket['description']}).status_code==401
        result=ai.post('/predict',headers=headers,json={'text':ticket['description']}).json()
    assert result['category']=='water'
    data={**result,'ticket_id':ticket['id'],'timestamp':datetime.now(timezone.utc).isoformat()}
    assert c.post('/api/ai/results',json=data).status_code==401
    res=c.post('/api/ai/results',headers=headers,json=data);assert res.status_code==200 and res.json()['accepted']
    assert c.post('/api/ai/results',headers=headers,json=data).json()['duplicate']
    assert c.get('/api/ai/pending',headers=headers).json()==[]
    d=c.get(f"/api/tickets/{ticket['id']}").json()['prediction']
    assert d['source']=='AI' and 0<=d['confidence']<=1

def test_ai_low_confidence_invalid_score_and_stale_time(clients,ticket):
    c=clients['admin'];headers={'X-Service-Token':os.environ['AI_SERVICE_TOKEN']}
    data=dict(ticket_id=ticket['id'],category='water',confidence=.01,model_version='test',timestamp=datetime.now(timezone.utc).isoformat())
    assert not c.post('/api/ai/results',headers=headers,json=data).json()['accepted']
    assert c.post('/api/ai/results',headers=headers,json={**data,'confidence':2}).status_code==422
    assert c.post('/api/ai/results',headers=headers,json={**data,'timestamp':'2020-01-01T00:00:00Z'}).status_code==422
    with clients['factory']() as db:assert db.query(Prediction).count()==0

def test_ai_outage_does_not_block_creation(clients,ticket):assert ticket['status']=='pending'

def test_dataset_no_group_leakage():
    rows=dataset();groups={}
    for r in rows:groups.setdefault(r['group'],set()).add(r['split'])
    assert all(len(v)==1 for v in groups.values())
    assert len(rows)==300 and len({r['label'] for r in rows})==5

def test_password_change_revokes_all_sessions(clients):
    c=clients['student']
    assert c.put('/api/auth/password',json={'old_password':'wrong','new_password':'Changed12345'}).status_code==400
    assert c.put('/api/auth/password',json={'old_password':'Testing12345','new_password':'Changed12345'}).status_code==200
    assert c.get('/api/users/me').status_code==401
    assert c.post('/api/auth/login',json={'username':'student','password':'Changed12345'}).status_code==200

def test_register_privilege_and_weak_password(clients,monkeypatch):
    c=clients['student']
    assert c.post('/api/auth/register',json={'username':'newadmin','password':'Testing12345','role':'admin'}).status_code==403
    assert c.post('/api/auth/register',json={'username':'newstudent','password':'weak'}).status_code==422
    monkeypatch.setenv('ADMIN_INVITE_CODE','invite-for-tests')
    r=c.post('/api/auth/register',json={'username':'newadmin','password':'Testing12345','role':'admin','invite_code':'invite-for-tests'})
    assert r.status_code==201 and 'password_hash' not in r.json()
    assert c.post('/api/auth/register',json={'username':'newadmin','password':'Testing12345'}).status_code==409
    with clients['factory']() as db:assert not db.query(User).filter_by(username='newadmin').one().password_hash.startswith('Testing')

def test_disabled_account_and_logout(clients):
    c=clients['student'];assert clients['admin'].put('/api/admin/users/1',json={'active':False}).status_code==200
    assert c.get('/api/users/me').status_code==401
    assert c.post('/api/auth/login',json={'username':'student','password':'Testing12345'}).status_code==401
    assert clients['admin'].put('/api/admin/users/3',json={'active':False}).status_code==409
    assert clients['other'].post('/api/auth/logout').status_code==200
    assert clients['other'].get('/api/users/me').status_code==401

def test_sql_injection_and_csrf(clients):
    c=clients['student']
    assert c.post('/api/auth/login',json={'username':"' OR 1=1 --",'password':'Testing12345'}).status_code==422
    r=c.post('/api/tickets',json={'room_id':1,'description':'test description'},headers={'Origin':'https://evil.example'})
    assert r.status_code==403
    c.headers.pop('X-Requested-With')
    assert c.post('/api/auth/logout').status_code==403

def test_image_validation_and_authorization(clients,ticket):
    url=f"/api/tickets/{ticket['id']}/attachments"
    assert clients['student'].post(url,files={'file':('bad.jpg',b'<script>alert(1)</script>','image/jpeg')}).status_code==422
    buf=io.BytesIO();Image.new('RGB',(32,32),'green').save(buf,format='PNG')
    result=clients['student'].post(url,files={'file':('../../evil.png',buf.getvalue(),'image/png')})
    assert result.status_code==201
    aid=result.json()['id']
    assert clients['other'].get(f'/api/attachments/{aid}').status_code==404
    r=clients['student'].get(f'/api/attachments/{aid}')
    assert r.status_code==200 and r.headers['content-type']=='image/jpeg'

def test_worker_network_failure_retry_and_ingestion(monkeypatch):
    import httpx
    from ai_service import worker
    calls=[]
    def handler(request):
        calls.append(request.url.path)
        if request.url.path=='/api/ai/pending':return httpx.Response(200,json=[{'id':7,'description':'水龙头一直漏水，请维修'}])
        if request.url.path=='/predict':return httpx.Response(200,json={'category':'water','confidence':.8,'model_version':'test'})
        return httpx.Response(200,json={'accepted':True})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert worker.run_once(client)==1
    assert calls==['/api/ai/pending','/predict','/api/ai/results']
    sleeps=[];attempts=[]
    monkeypatch.setattr('sys.argv',['worker'])
    def fail_then_stop(client):
        attempts.append(1)
        if len(attempts)<=3:raise httpx.ConnectError('simulated disconnect')
        raise KeyboardInterrupt
    monkeypatch.setattr(worker,'run_once',fail_then_stop)
    monkeypatch.setattr(worker.time,'sleep',lambda seconds:sleeps.append(seconds))
    with pytest.raises(KeyboardInterrupt):worker.main()
    assert sleeps==[1,2,4]

def test_login_rate_limit_and_attachment_size(clients,ticket):
    c=clients['student']
    for _ in range(10):assert c.post('/api/auth/login',json={'username':'unknown','password':'Unknown12345'}).status_code==401
    assert c.post('/api/auth/login',json={'username':'unknown','password':'Unknown12345'}).status_code==429
    r=c.post(f"/api/tickets/{ticket['id']}/attachments",files={'file':('huge.jpg',b'x'*(5*1024*1024+1),'image/jpeg')})
    assert r.status_code==413
