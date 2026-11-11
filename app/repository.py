from sqlalchemy import select
from app.models import Ticket, Room, User

def scoped_tickets(db, user, status=None, category=None, building=None, start=None, end=None):
    query = select(Ticket).join(Room, Room.id == Ticket.room_id)
    if user.role == 'student':
        query = query.where(Ticket.student_id == user.id)
    elif user.role == 'technician':
        query = query.where(Ticket.assignee_id == user.id)
    if status:
        query = query.where(Ticket.status == status)
    if category:
        query = query.where(Ticket.category == category)
    if building:
        query = query.where(Room.building_id == building)
    if start:
        query = query.where(Ticket.created_at >= start)
    if end:
        query = query.where(Ticket.created_at <= end)
    return query.order_by(Ticket.id.desc())

def visible(db, user, ticket_id):
    return db.scalar(scoped_tickets(db, user).where(Ticket.id == ticket_id))

def username(db, user_id):
    user = db.get(User, user_id) if user_id else None
    return user.username if user else None
