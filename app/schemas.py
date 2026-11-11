from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator

Category = Literal['water','electric','door','furniture','other']
class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class Credentials(Input):
    username: str = Field(min_length=3,max_length=40,pattern=r'^[\w.-]+$')
    password: str = Field(min_length=10,max_length=64)
    @field_validator('password')
    @classmethod
    def strong(cls,v):
        if len(v.encode('utf-8'))>72:
            raise ValueError('密码的UTF-8编码不能超过72字节')
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError('密码需要同时包含字母和数字，至少10位')
        return v

class Register(Credentials):
    role: Literal['student','technician','admin']='student'
    email: str = Field(default='',max_length=120)
    invite_code: str = Field(default='',max_length=128)

class Password(Input):
    old_password: str = Field(max_length=64)
    new_password: str = Field(min_length=10,max_length=64)
    _strong = field_validator('new_password')(Credentials.strong.__func__)

class CreateTicket(Input):
    room_id: int = Field(gt=0)
    description: str = Field(min_length=5,max_length=2000)
    category: Category='other'

class Action(Input):
    action: Literal['cancel','assign','start','finish','accept','reject','comment','classify']
    version: int = Field(ge=1)
    note: str = Field(default='',max_length=2000)
    assignee_id: int | None = None
    scheduled_at: datetime | None = None
    category: Category | None = None
    @field_validator('scheduled_at')
    @classmethod
    def utc(cls,v):
        if v and v.tzinfo:
            from datetime import timezone
            return v.astimezone(timezone.utc).replace(tzinfo=None)
        return v

class Rating(Input):
    score: int = Field(ge=1,le=5)
    comment: str = Field(default='',max_length=1000)

class PredictResult(Input):
    ticket_id: int = Field(gt=0)
    category: Category
    confidence: float = Field(ge=0,le=1,allow_inf_nan=False)
    model_version: str = Field(min_length=1,max_length=80)
    timestamp: datetime

class Location(Input):
    name: str = Field(min_length=1,max_length=30)
    building_id: int | None = None

class UserStatus(Input):
    active: bool
