# backend/schemas.py
from pydantic import BaseModel, field_validator, Field
from datetime import date, datetime
from typing import Optional, List, Dict, Any
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
    department: Optional[str] = None
    employee_code: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role: str = "user"
    department: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ("admin", "user"):
            raise ValueError("Role phải là 'admin' hoặc 'user'")
        return v

    @field_validator("department")
    @classmethod
    def validate_department(cls, v):
        if v is not None and v not in ("hardware", "software", "business"):
            raise ValueError("Department phải là 'hardware', 'software' hoặc 'business'")
        return v

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    department: Optional[str] = None
    employee_code: Optional[str] = None
    model_config = {"from_attributes": True}

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class UpdateRoleRequest(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ("admin", "user"):
            raise ValueError("Role phải là 'admin' hoặc 'user'")
        return v

class UpdateDepartmentRequest(BaseModel):
    department: str

    @field_validator("department")
    @classmethod
    def validate_department(cls, v):
        if v not in ("hardware", "software", "business"):
            raise ValueError("Department phải là 'hardware', 'software' hoặc 'business'")
        return v

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
    # Tỉ lệ theo department để render thanh màu
    dept_counts: Dict[str, int] = Field(default_factory=lambda: {"hardware": 0, "software": 0, "business": 0})

class DaySummary(BaseModel):
    date: str
    shifts: Dict[str, ShiftSummary]

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
    status: str  # ACCEPTED hoặc REJECTED

# Response phong phú hơn cho admin xem danh sách vắng mặt
class AbsenceRequestDetail(BaseModel):
    id: int
    user_id: int
    user_full_name: str
    user_username: str
    schedule_id: int
    schedule_date: Optional[str] = None
    schedule_shift: Optional[str] = None
    reason: str
    status: str
    created_at: Optional[str] = None
