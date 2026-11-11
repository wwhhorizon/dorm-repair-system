import os
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.orm import declarative_base, sessionmaker

def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

Path('data/uploads').mkdir(parents=True, exist_ok=True)
URL = os.getenv('DATABASE_URL', 'sqlite:///data/repair.db')
engine = create_engine(URL, connect_args={'check_same_thread': False, 'timeout': 20} if URL.startswith('sqlite') else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()
CATEGORIES = ['water', 'electric', 'door', 'furniture', 'other']
STATES = ['pending', 'assigned', 'working', 'review', 'completed', 'cancelled']

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(40), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(16), nullable=False)
    email = Column(String(120), default='')
    active = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=now)
    __table_args__ = (CheckConstraint("role in ('student','admin','technician')"),)

class LoginSession(Base):
    __tablename__ = 'login_sessions'
    token_hash = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    expires = Column(DateTime, nullable=False)

class Building(Base):
    __tablename__ = 'buildings'
    id = Column(Integer, primary_key=True)
    name = Column(String(60), unique=True, nullable=False)

class Room(Base):
    __tablename__ = 'rooms'
    id = Column(Integer, primary_key=True)
    building_id = Column(Integer, ForeignKey('buildings.id'), nullable=False)
    name = Column(String(30), nullable=False)

class Ticket(Base):
    __tablename__ = 'tickets'
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey('rooms.id'), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(20), nullable=False)
    status = Column(String(20), default='pending', nullable=False, index=True)
    assignee_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=now, index=True)
    updated_at = Column(DateTime, default=now)
    completed_at = Column(DateTime, nullable=True)
    __table_args__ = (CheckConstraint("category in ('water','electric','door','furniture','other')"), CheckConstraint("status in ('pending','assigned','working','review','completed','cancelled')"))

class Event(Base):
    __tablename__ = 'ticket_events'
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    action = Column(String(30), nullable=False)
    from_state = Column(String(20), nullable=False)
    to_state = Column(String(20), nullable=False)
    note = Column(Text, default='')
    created_at = Column(DateTime, default=now)

class Attachment(Base):
    __tablename__ = 'attachments'
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), nullable=False)
    actor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    path = Column(String(100), nullable=False)
    mime = Column(String(40), nullable=False)
    purpose = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=now)

class Evaluation(Base):
    __tablename__ = 'evaluations'
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), unique=True, nullable=False)
    score = Column(Integer, nullable=False)
    comment = Column(Text, default='')
    __table_args__ = (CheckConstraint('score >= 1 and score <= 5'),)

class Prediction(Base):
    __tablename__ = 'predictions'
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'), unique=True, nullable=False)
    category = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=False)
    model_version = Column(String(80), nullable=False)
    source = Column(String(10), default='AI', nullable=False)
    accepted = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, nullable=False)
    __table_args__ = (CheckConstraint('confidence >= 0 and confidence <= 1'), CheckConstraint("category in ('water','electric','door','furniture','other')"))

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    action = Column(String(60), nullable=False)
    detail = Column(Text, default='')
    created_at = Column(DateTime, default=now)
