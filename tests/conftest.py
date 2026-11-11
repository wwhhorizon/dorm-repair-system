import os
os.environ['AI_SERVICE_TOKEN']='test-service-token-not-for-deployment'
import bcrypt
import pytest
from contextlib import ExitStack
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app import main
from app.models import Base,User,Building,Room

@pytest.fixture
def clients(monkeypatch):
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    factory=sessionmaker(engine,expire_on_commit=False)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(main,'engine',engine)
    monkeypatch.setattr(main,'SessionLocal',factory)
    password=bcrypt.hashpw(b'Testing12345',bcrypt.gensalt()).decode()
    with factory() as db:
        for name,role in [('student','student'),('other','student'),('admin','admin'),('repair','technician'),('repair2','technician')]:db.add(User(username=name,role=role,password_hash=password))
        b=Building(name='1号楼');db.add(b);db.flush();db.add(Room(building_id=b.id,name='101'));db.commit()
    with ExitStack() as stack:
        result={}
        for name in ['student','other','admin','repair','repair2']:
            client=stack.enter_context(TestClient(main.app))
            client.headers['X-Requested-With']='RepairApp'
            response=client.post('/api/auth/login',json={'username':name,'password':'Testing12345'})
            assert response.status_code==200,response.text
            result[name]=client
        result['factory']=factory
        yield result
    engine.dispose()

@pytest.fixture
def ticket(clients):
    r=clients['student'].post('/api/tickets',json={'room_id':1,'description':'洗手池水龙头一直漏水','category':'water'})
    assert r.status_code==201,r.text
    return r.json()
