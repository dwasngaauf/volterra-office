# backend/schemas.py
from pydantic import BaseModel, field_validator
from datetime import date, datetime
from typing import Optional, List, Dict
from .database import ShiftEnum, ALL_SHIFTS

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    full_name: str
    role: str

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role: str = "user"

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ("admin", "user"):
            raise ValueError("Role phải là 'admin' hoặc 'user'")
        return v

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    model_config = {"from_attributes": True}

class ScheduleCreate(BaseModel):
    date: date
    shift: ShiftEnum

class ScheduleResponse(BaseModel):
    id: int
    user_id: int
    date: date
    shift: ShiftEnum
    created_at: datetime
    user: UserResponse
    model_config = {"from_attributes": True}

class ShiftSummary(BaseModel):
    count: int
    has_registered: bool
    schedule_id: Optional[int] = None

# DaySummary giờ dùng dict động thay vì field cố định morning/afternoon
class DaySummary(BaseModel):
    date: str
    shifts: Dict[str, ShiftSummary]  # key là "09:00", "10:00", ...

class CalendarResponse(BaseModel):
    days: List[DaySummary]

class DayDetailResponse(BaseModel):
    date: str
    shift: str
    attendees: List[UserResponse]

class AbsenceRequestCreate(BaseModel):
    schedule_id: int
    reason: str

class AbsenceRequestUpdate(BaseModel):
    status: str # ACCEPTED hoặc REJECTED