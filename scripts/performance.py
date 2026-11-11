"""隔离临时数据库测量50条工单，顺序100次与10并发100次列表请求。"""
import sys,time,json,tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import main
from app.models import Base,User,Building,Room,Ticket,LoginSession,now

def main_test():
    old_engine,old_factory=main.engine,main.SessionLocal
    with tempfile.TemporaryDirectory() as tmp:
        engine=create_engine('sqlite:///'+str(Path(tmp)/'perf.db'),connect_args={'check_same_thread':False})
        factory=sessionmaker(engine,expire_on_commit=False);Base.metadata.create_all(engine)
        with factory() as db:
            u=User(username='perf',role='student',password_hash='unused-for-token-auth');db.add(u);db.flush()
            b=Building(name='性能测试楼');db.add(b);db.flush();r=Room(building_id=b.id,name='101');db.add(r);db.flush()
            db.add_all([Ticket(student_id=u.id,room_id=r.id,description=f'性能测试工单{i}：水龙头漏水',category='water') for i in range(50)])
            db.add(LoginSession(token_hash=main.hash_token('performance-token'),user_id=u.id,expires=now()+timedelta(minutes=20)));db.commit()
        main.engine,main.SessionLocal=engine,factory
        try:
            with TestClient(main.app) as client:
                def request(_):
                    start=time.perf_counter();res=client.get('/api/tickets?page_size=50',headers={'Authorization':'Bearer performance-token'});assert res.status_code==200 and res.json()['total']==50
                    return (time.perf_counter()-start)*1000
                results={}
                for concurrency in [1,10]:
                    start=time.perf_counter()
                    with ThreadPoolExecutor(max_workers=concurrency) as pool:latencies=list(pool.map(request,range(100)))
                    elapsed=time.perf_counter()-start;latencies.sort()
                    results[str(concurrency)]={'requests':100,'tickets':50,'concurrency':concurrency,'p50_ms':round(latencies[49],2),'p95_ms':round(latencies[94],2),'max_ms':round(max(latencies),2),'throughput_per_second':round(100/elapsed,2)}
        finally:
            main.engine,main.SessionLocal=old_engine,old_factory;engine.dispose()
    Path('artifacts/performance.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(results,ensure_ascii=False),flush=True)

if __name__=='__main__':main_test()
