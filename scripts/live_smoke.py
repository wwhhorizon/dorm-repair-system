"""对运行中的真实后端和 AI worker 做完整验收，可用于 MySQL Compose。"""
import os,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.dev import load_env
from datetime import datetime,timedelta,timezone
import httpx

def main():
    load_env()
    base=os.getenv('BACKEND_URL','http://127.0.0.1:8000')
    password=os.environ['DEMO_PASSWORD']
    with httpx.Client(base_url=base,headers={'X-Requested-With':'RepairApp'}) as c:
        def login(name):
            r=c.post('/api/auth/login',json={'username':name,'password':password});r.raise_for_status()
        login('student')
        locations=c.get('/api/locations').json()
        r=c.post('/api/tickets',json={'description':'水龙头一直漏水，请安排维修。','room_id':locations[0]['rooms'][0]['id'],'category':'other'});r.raise_for_status();t=r.json()
        for _ in range(60):
            detail=c.get('/api/tickets/'+str(t['id'])).json()
            if detail['prediction']:break
            time.sleep(1)
        assert detail['prediction'] and detail['prediction']['category']=='water'
        login('admin')
        workers=c.get('/api/admin/users').json();worker=next(u for u in workers if u['username']=='repair')
        def action(payload):
            nonlocal t
            r=c.post(f"/api/tickets/{t['id']}/actions",json={'version':t['version'],**payload});r.raise_for_status();t=r.json()
        action({'action':'classify','category':'water'})
        action({'action':'assign','assignee_id':worker['id'],'scheduled_at':(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()})
        login('repair');action({'action':'start'});action({'action':'finish','note':'更换密封圈，通水测试正常'})
        login('student');action({'action':'accept'})
        c.post(f"/api/tickets/{t['id']}/evaluation",json={'score':5,'comment':'及时解决'}).raise_for_status()
        login('student2');assert c.get('/api/tickets/'+str(t['id'])).status_code==404
        login('admin');assert c.get('/api/admin/export').status_code==200
        print('LIVE_SMOKE_PASS: AI, assignment, repair, acceptance, rating, permission, export')

if __name__=='__main__':main()
