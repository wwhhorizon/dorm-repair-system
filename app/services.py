import csv
import io
from collections import Counter
from sqlalchemy import update
from fastapi import HTTPException
from app.models import Ticket, User, Event, AuditLog, Evaluation, Prediction, Room, Building, now
from app.repository import username

def fail(status, message):
    raise HTTPException(status, message)

def audit(db, user_id, action, detail=''):
    db.add(AuditLog(actor_id=user_id, action=action, detail=detail))

def serialize(db, t):
    room = db.get(Room, t.room_id)
    building = db.get(Building, room.building_id)
    p = db.query(Prediction).filter_by(ticket_id=t.id).first()
    return dict(id=t.id, student_id=t.student_id, student=username(db,t.student_id), room_id=t.room_id,
        building=building.name, building_id=building.id, room=room.name, description=t.description, category=t.category,
        status=t.status, assignee_id=t.assignee_id, assignee=username(db,t.assignee_id), scheduled_at=t.scheduled_at,
        version=t.version, created_at=t.created_at, updated_at=t.updated_at, completed_at=t.completed_at,
        prediction=dict(category=p.category, confidence=p.confidence, model_version=p.model_version, accepted=bool(p.accepted), created_at=p.created_at, source=p.source) if p else None)

def transition(db, user, t, payload):
    action = payload.action
    old = t.status
    values = dict(version=t.version+1, updated_at=now())
    if payload.version != t.version:
        fail(409, '工单已更新，请刷新后重试')
    if action == 'cancel' and user.role == 'student' and old == 'pending':
        target = 'cancelled'
    elif action == 'assign' and user.role == 'admin' and old in ['pending','assigned','working']:
        if old != 'pending' and not payload.note.strip():
            fail(422, '重新派单必须填写原因')
        worker = db.get(User, payload.assignee_id) if payload.assignee_id else None
        if not worker or worker.role != 'technician' or not worker.active:
            fail(422, '请选择有效维修人员')
        if not payload.scheduled_at or payload.scheduled_at < now():
            fail(422, '请设置未来的预约维修时间')
        target = 'assigned'
        values.update(assignee_id=worker.id, scheduled_at=payload.scheduled_at)
    elif action == 'start' and user.role == 'technician' and old == 'assigned':
        target = 'working'
    elif action == 'finish' and user.role == 'technician' and old == 'working':
        if not payload.note.strip(): fail(422, '请填写维修说明')
        target = 'review'
    elif action == 'accept' and user.role == 'student' and old == 'review':
        target = 'completed'
        values['completed_at'] = now()
    elif action == 'reject' and user.role == 'student' and old == 'review':
        if not payload.note.strip(): fail(422, '请填写返修原因')
        target = 'working'
    elif action == 'comment' and old not in ['completed','cancelled'] and payload.note.strip():
        target = old
    elif action == 'classify' and user.role == 'admin' and old not in ['completed','cancelled'] and payload.category:
        target = old
        values['category'] = payload.category
    else:
        fail(409, '当前角色或工单状态不允许此操作')
    values['status'] = target
    result = db.execute(update(Ticket).where(Ticket.id == t.id, Ticket.version == payload.version).values(**values))
    if result.rowcount != 1:
        db.rollback(); fail(409, '工单已更新，请刷新后重试')
    detail = payload.note
    if action == 'assign':
        detail = f'分配给 {username(db,payload.assignee_id)}；时间 {payload.scheduled_at}。{detail}'
    if action == 'classify':
        detail = f'分类确认：{t.category} → {payload.category}。{detail}'
        p = db.query(Prediction).filter_by(ticket_id=t.id).first()
        if p: p.accepted = int(p.category == payload.category)
    db.add(Event(ticket_id=t.id, actor_id=user.id, action=action, from_state=old, to_state=target, note=detail))
    audit(db,user.id,'ticket.'+action,str(t.id))
    db.commit()
    db.refresh(t)
    return serialize(db,t)

def statistics(tickets):
    completed = [t for t in tickets if t.completed_at]
    return dict(total=len(tickets), open=sum(t.status not in ['completed','cancelled'] for t in tickets),
        completed=len(completed), average_hours=round(sum((t.completed_at-t.created_at).total_seconds()/3600 for t in completed)/len(completed),2) if completed else None,
        categories=dict(Counter(t.category for t in tickets)), states=dict(Counter(t.status for t in tickets)),
        days=dict(sorted(Counter(t.created_at.strftime('%Y-%m-%d') for t in tickets).items())))

def safe_cell(value):
    text = '' if value is None else str(value)
    return "'"+text if text.lstrip().startswith(('=','+','-','@','\t','\r','\n')) else text

def export_csv(db,tickets):
    out=io.StringIO(newline='')
    writer=csv.writer(out)
    writer.writerow(['工单编号','学生','楼栋','房间','描述','类别','状态','维修人员','创建时间'])
    for t in tickets:
        d=serialize(db,t)
        writer.writerow([safe_cell(d[k]) for k in ['id','student','building','room','description','category','status','assignee','created_at']])
    return '\ufeff'+out.getvalue()
