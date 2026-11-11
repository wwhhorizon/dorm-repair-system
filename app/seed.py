"""显式演示初始化；不覆盖已有账号，不生成虚构的历史提交记录。"""
import os,secrets
import bcrypt
from sqlalchemy import select
from app.models import Base,engine,SessionLocal,User,Building,Room

def seed():
    Base.metadata.create_all(engine)
    password=os.getenv('DEMO_PASSWORD') or ('Demo-'+secrets.token_urlsafe(12)+'8')
    with SessionLocal() as db:
        for name,role in [('student','student'),('student2','student'),('admin','admin'),('repair','technician')]:
            if not db.scalar(select(User).where(User.username==name)):
                db.add(User(username=name,role=role,password_hash=bcrypt.hashpw(password.encode(),bcrypt.gensalt()).decode()))
        if not db.scalar(select(Building)):
            for name in ['1号宿舍楼','2号宿舍楼','3号宿舍楼']:
                b=Building(name=name);db.add(b);db.flush()
                for room in ['101','102','201','202','301','405']:db.add(Room(building_id=b.id,name=room))
        db.commit()
    print('Demo users: student / student2 / admin / repair')
    print('Password for newly created users:',password)
    print('Existing passwords were not changed.')

if __name__=='__main__':seed()
