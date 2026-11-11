import asyncio
import hashlib
import hmac
import io
import os
import secrets
import time
import warnings
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import FastAPI, Depends, Request, Response, UploadFile, File, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from PIL import Image, UnidentifiedImageError
import bcrypt
from app.models import Base, engine, SessionLocal, User, LoginSession, Ticket, Event, Attachment, Evaluation, Prediction, Building, Room, AuditLog, now
from app import schemas as S
from app.repository import scoped_tickets, visible, username
from app.services import fail, audit, serialize, statistics, transition, export_csv

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    yield

app=FastAPI(title='宿修 · 智能宿舍报修', version='1.1.0', lifespan=lifespan,
    description='宿舍报修、分类派单、维修验收与统计管理接口。')
app.mount('/static',StaticFiles(directory=Path(__file__).parent/'static'),name='static')

@app.middleware('http')
async def protection(request, call_next):
    if request.url.path.startswith('/api/') and request.method in ['POST','PUT','PATCH','DELETE']:
        if request.headers.get('x-requested-with') != 'RepairApp':
            return JSONResponse({'code':'CSRF_REJECTED','message':'缺少请求校验头'},status_code=403)
        origin=request.headers.get('origin')
        if origin and origin.rstrip('/') != str(request.base_url).rstrip('/'):
            return JSONResponse({'code':'ORIGIN_REJECTED','message':'请求来源不合法'},status_code=403)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob:; connect-src 'self' ws: wss:; frame-ancestors 'none'"
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control']='no-store'
    return response

@app.exception_handler(HTTPException)
async def http_error(request,exc):
    return JSONResponse({'code':f'HTTP_{exc.status_code}','message':str(exc.detail)},status_code=exc.status_code)

@app.exception_handler(RequestValidationError)
async def validation_error(request,exc):
    messages=['.'.join(map(str,e['loc'][1:]))+': '+e['msg'] for e in exc.errors()]
    return JSONResponse({'code':'VALIDATION_ERROR','message':'；'.join(messages)},status_code=422)

@app.exception_handler(IntegrityError)
async def integrity_error(request,exc):
    return JSONResponse({'code':'CONFLICT','message':'数据已存在或关联数据无效'},status_code=409)

def db_session():
    with SessionLocal() as db:
        yield db

def hash_token(token): return hashlib.sha256(token.encode()).hexdigest()

def resolve_user(db,token):
    session=db.get(LoginSession,hash_token(token)) if token else None
    if not session or session.expires<=now(): return None
    u=db.get(User,session.user_id)
    return u if u and u.active else None

def current_user(request: Request,db=Depends(db_session)):
    auth=request.headers.get('authorization','')
    token=auth[7:] if auth.startswith('Bearer ') else request.cookies.get('repair_session')
    user=resolve_user(db,token)
    if not user: fail(401,'请先登录，或登录已失效')
    return user

def admin(user=Depends(current_user)):
    if user.role!='admin': fail(403,'需要管理员权限')
    return user

def public_user(u): return dict(id=u.id,username=u.username,role=u.role,email=u.email,active=bool(u.active))

@app.get('/',include_in_schema=False)
def index(): return FileResponse(Path(__file__).parent/'static/index.html')

@app.get('/health')
def health(db=Depends(db_session)):
    db.execute(select(1))
    return {'status':'ok'}

@app.post('/api/auth/register',status_code=201)
def register(data:S.Register,db=Depends(db_session)):
    if data.role!='student':
        expected=os.getenv('ADMIN_INVITE_CODE' if data.role=='admin' else 'TECHNICIAN_INVITE_CODE','')
        if not expected or not hmac.compare_digest(expected,data.invite_code): fail(403,'该角色需要有效邀请码')
    if db.scalar(select(User).where(User.username==data.username)): fail(409,'用户名已存在')
    user=User(username=data.username,password_hash=bcrypt.hashpw(data.password.encode(),bcrypt.gensalt()).decode(),role=data.role,email=data.email)
    db.add(user);db.flush();audit(db,user.id,'auth.register');db.commit()
    return public_user(user)

# 失败记录保存在数据库审计表中，进程重启和多实例不会重置计数。
@app.post('/api/auth/login')
def login(data:S.Credentials,request:Request,response:Response,db=Depends(db_session)):
    key=hash_token((request.client.host if request.client else 'unknown')+'|'+data.username)
    failures=db.query(AuditLog).filter(AuditLog.action=='auth.failed',AuditLog.detail==key,AuditLog.created_at>now()-timedelta(minutes=5)).count()
    if failures>=10: fail(429,'登录失败次数过多，请5分钟后重试')
    user=db.scalar(select(User).where(User.username==data.username))
    if not user or not user.active or not bcrypt.checkpw(data.password.encode(),user.password_hash.encode()):
        audit(db,None,'auth.failed',key);db.commit();fail(401,'用户名或密码错误')
    token=secrets.token_urlsafe(32)
    db.add(LoginSession(token_hash=hash_token(token),user_id=user.id,expires=now()+timedelta(hours=8)))
    audit(db,user.id,'auth.login');db.commit()
    response.set_cookie('repair_session',token,httponly=True,samesite='strict',secure=os.getenv('COOKIE_SECURE')=='1',max_age=28800)
    return dict(user=public_user(user),access_token=token,token_type='bearer')

@app.post('/api/auth/logout')
def logout(request:Request,response:Response,db=Depends(db_session),user=Depends(current_user)):
    auth=request.headers.get('authorization','')
    token=auth[7:] if auth.startswith('Bearer ') else request.cookies.get('repair_session','')
    db.execute(delete(LoginSession).where(LoginSession.token_hash==hash_token(token)));db.commit()
    response.delete_cookie('repair_session');return {'message':'已退出'}

@app.put('/api/auth/password')
def password(data:S.Password,db=Depends(db_session),user=Depends(current_user)):
    if not bcrypt.checkpw(data.old_password.encode(),user.password_hash.encode()): fail(400,'原密码错误')
    user.password_hash=bcrypt.hashpw(data.new_password.encode(),bcrypt.gensalt()).decode()
    db.execute(delete(LoginSession).where(LoginSession.user_id==user.id));audit(db,user.id,'auth.password');db.commit()
    return {'message':'密码已修改，请重新登录'}

@app.get('/api/users/me')
def me(user=Depends(current_user)): return public_user(user)

@app.get('/api/admin/users')
def users(db=Depends(db_session),user=Depends(admin)):
    return [public_user(u) for u in db.scalars(select(User).order_by(User.id))]

@app.put('/api/admin/users/{uid}')
def update_user(uid:int,data:S.UserStatus,db=Depends(db_session),user=Depends(admin)):
    target=db.get(User,uid)
    if not target: fail(404,'用户不存在')
    if target.role=='admin': fail(409,'管理员账号状态不可在此修改')
    target.active=int(data.active);audit(db,user.id,'user.status',str(uid));db.commit()
    return public_user(target)

@app.get('/api/locations')
def locations(db=Depends(db_session),user=Depends(current_user)):
    return [dict(id=b.id,name=b.name,rooms=[dict(id=r.id,name=r.name) for r in db.scalars(select(Room).where(Room.building_id==b.id))]) for b in db.scalars(select(Building))]

@app.post('/api/admin/locations',status_code=201)
def create_location(data:S.Location,db=Depends(db_session),user=Depends(admin)):
    if data.building_id:
        if not db.get(Building,data.building_id): fail(404,'楼栋不存在')
        if db.scalar(select(Room).where(Room.building_id==data.building_id,Room.name==data.name)): fail(409,'房间已存在')
        obj=Room(building_id=data.building_id,name=data.name)
    else: obj=Building(name=data.name)
    db.add(obj);audit(db,user.id,'location.create',data.name);db.commit()
    return {'id':obj.id}

@app.post('/api/tickets',status_code=201)
def create_ticket(data:S.CreateTicket,db=Depends(db_session),user=Depends(current_user)):
    if user.role!='student': fail(403,'学生账号可以创建报修')
    if not db.get(Room,data.room_id): fail(422,'房间不存在')
    t=Ticket(student_id=user.id,room_id=data.room_id,description=data.description,category=data.category)
    db.add(t);db.flush()
    db.add(Event(ticket_id=t.id,actor_id=user.id,action='create',from_state='pending',to_state='pending',note='提交报修'))
    audit(db,user.id,'ticket.create',str(t.id));db.commit()
    return serialize(db,t)

@app.get('/api/tickets')
def tickets(status:str|None=None,category:str|None=None,building:int|None=None,start:datetime|None=None,end:datetime|None=None,page:int=1,page_size:int=30,db=Depends(db_session),user=Depends(current_user)):
    if page<1 or not 1<=page_size<=100: fail(422,'分页参数无效')
    query=scoped_tickets(db,user,status,category,building,start,end)
    total=db.query(query.subquery()).count()
    return {'items':[serialize(db,t) for t in db.scalars(query.offset((page-1)*page_size).limit(page_size))],'total':total,'page':page}

def get_ticket(db,user,tid):
    t=visible(db,user,tid)
    if not t: fail(404,'工单不存在或没有访问权限')
    return t

@app.get('/api/tickets/{tid}')
def ticket(tid:int,db=Depends(db_session),user=Depends(current_user)):
    t=get_ticket(db,user,tid)
    d=serialize(db,t)
    d['events']=[dict(id=e.id,actor=username(db,e.actor_id),action=e.action,from_state=e.from_state,to_state=e.to_state,note=e.note,created_at=e.created_at) for e in db.scalars(select(Event).where(Event.ticket_id==tid).order_by(Event.id))]
    d['attachments']=[dict(id=a.id,purpose=a.purpose,url=f'/api/attachments/{a.id}',created_at=a.created_at) for a in db.scalars(select(Attachment).where(Attachment.ticket_id==tid))]
    rating=db.scalar(select(Evaluation).where(Evaluation.ticket_id==tid))
    d['evaluation']=dict(score=rating.score,comment=rating.comment) if rating else None
    return d

@app.post('/api/tickets/{tid}/actions')
def action(tid:int,data:S.Action,db=Depends(db_session),user=Depends(current_user)):
    return transition(db,user,get_ticket(db,user,tid),data)

@app.post('/api/tickets/{tid}/attachments',status_code=201)
async def upload(tid:int,file:UploadFile=File(...),db=Depends(db_session),user=Depends(current_user)):
    t=get_ticket(db,user,tid)
    if t.status in ['completed','cancelled']: fail(409,'已结束工单不能上传附件')
    if db.query(Attachment).filter_by(ticket_id=tid).count()>=10: fail(422,'每张工单最多10张图片')
    raw=await file.read(5*1024*1024+1)
    if len(raw)>5*1024*1024: fail(413,'图片最大5MB')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            im=Image.open(io.BytesIO(raw))
            if im.format not in ['JPEG','PNG','WEBP'] or im.width*im.height>20000000: fail(422,'仅支持不超过2000万像素的 JPEG/PNG/WebP 图片')
            im.load()
            # 重新编码去掉 EXIF、用户文件名和附带内容。
            cleaned=io.BytesIO();im.convert('RGB').save(cleaned,format='JPEG',quality=88)
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError,Image.DecompressionBombWarning):
        fail(422,'无效图片')
    path=secrets.token_hex(20)+'.jpg'
    Path('data/uploads',path).write_bytes(cleaned.getvalue())
    a=Attachment(ticket_id=tid,actor_id=user.id,path=path,mime='image/jpeg',purpose='repair' if user.role=='technician' else 'report')
    db.add(a);db.commit();return {'id':a.id}

@app.get('/api/attachments/{aid}')
def attachment(aid:int,db=Depends(db_session),user=Depends(current_user)):
    a=db.get(Attachment,aid)
    if not a: fail(404,'附件不存在')
    get_ticket(db,user,a.ticket_id)
    return FileResponse(Path('data/uploads',a.path),media_type=a.mime)

@app.post('/api/tickets/{tid}/evaluation',status_code=201)
def evaluate(tid:int,data:S.Rating,db=Depends(db_session),user=Depends(current_user)):
    t=get_ticket(db,user,tid)
    if user.role!='student' or t.status!='completed': fail(409,'完成验收后可以评价')
    if db.scalar(select(Evaluation).where(Evaluation.ticket_id==tid)): fail(409,'已评价')
    db.add(Evaluation(ticket_id=tid,**data.model_dump()));db.commit();return {'message':'评价已提交'}

@app.get('/api/statistics')
def stats(category:str|None=None,building:int|None=None,start:datetime|None=None,end:datetime|None=None,db=Depends(db_session),user=Depends(current_user)):
    ts=list(db.scalars(scoped_tickets(db,user,category=category,building=building,start=start,end=end)))
    result=statistics(ts)
    ids=[t.id for t in ts]
    ratings=list(db.scalars(select(Evaluation).where(Evaluation.ticket_id.in_(ids)))) if ids else []
    from collections import Counter
    result['ratings']=dict(Counter(e.score for e in ratings))
    result['average_rating']=round(sum(e.score for e in ratings)/len(ratings),2) if ratings else None
    return result

@app.get('/api/admin/export')
def export(status:str|None=None,category:str|None=None,building:int|None=None,start:datetime|None=None,end:datetime|None=None,db=Depends(db_session),user=Depends(admin)):
    result=export_csv(db,list(db.scalars(scoped_tickets(db,user,status=status,category=category,building=building,start=start,end=end))))
    audit(db,user.id,'csv.export');db.commit()
    return Response(result,media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="repair-tickets.csv"'})

@app.get('/api/admin/audit')
def audits(db=Depends(db_session),user=Depends(admin)):
    return [dict(id=e.id,actor=username(db,e.actor_id),action=e.action,detail=e.detail,created_at=e.created_at) for e in db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(100))]

def service_auth(request:Request):
    expected=os.getenv('AI_SERVICE_TOKEN','')
    supplied=request.headers.get('x-service-token','')
    if not expected or not hmac.compare_digest(expected,supplied): fail(401,'AI 服务认证失败')

@app.get('/api/ai/pending',dependencies=[Depends(service_auth)])
def ai_pending(db=Depends(db_session)):
    query=select(Ticket).outerjoin(Prediction,Prediction.ticket_id==Ticket.id).where(Prediction.id.is_(None),Ticket.status.notin_(['completed','cancelled'])).order_by(Ticket.id).limit(100)
    return [dict(id=t.id,description=t.description) for t in db.scalars(query)]

@app.post('/api/ai/results',dependencies=[Depends(service_auth)])
def ai_result(data:S.PredictResult,db=Depends(db_session)):
    if not db.get(Ticket,data.ticket_id): fail(404,'工单不存在')
    timestamp=data.timestamp
    if timestamp.tzinfo: timestamp=timestamp.astimezone(timezone.utc).replace(tzinfo=None)
    if abs((timestamp-now()).total_seconds())>300: fail(422,'推理时间与服务端相差超过5分钟')
    threshold=float(os.getenv('AI_CONFIDENCE_THRESHOLD','0.35'))
    if data.confidence<threshold: return {'accepted':False,'reason':'below_threshold'}
    previous=db.scalar(select(Prediction).where(Prediction.ticket_id==data.ticket_id))
    if previous: return {'accepted':True,'id':previous.id,'duplicate':True}
    p=Prediction(ticket_id=data.ticket_id,category=data.category,confidence=data.confidence,model_version=data.model_version,created_at=timestamp,source='AI')
    db.add(p);audit(db,None,'ai.ingest',str(data.ticket_id));db.commit()
    return {'accepted':True,'id':p.id,'duplicate':False}

@app.websocket('/ws/dashboard')
async def dashboard(ws:WebSocket):
    origin=ws.headers.get('origin')
    if origin and origin.split('://',1)[-1].rstrip('/')!=ws.headers.get('host'):
        await ws.close(code=1008);return
    with SessionLocal() as db:
        user=resolve_user(db,ws.cookies.get('repair_session'))
        if not user: await ws.close(code=1008);return
    await ws.accept()
    try:
        while True:
            with SessionLocal() as db:
                user=resolve_user(db,ws.cookies.get('repair_session'))
                if not user: await ws.close(code=1008);return
                await ws.send_json(statistics(list(db.scalars(scoped_tickets(db,user)))))
            await asyncio.sleep(3)
    except (WebSocketDisconnect,RuntimeError): pass
