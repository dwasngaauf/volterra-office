# backend/routers.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import date, datetime, timedelta
from typing import List
import calendar

from . import database, schemas, auth

router = APIRouter()

# ── AUTH ──────────────────────────────────────────────────────────────────────
@router.post("/auth/login", response_model=schemas.TokenResponse, tags=["Auth"])
def login(payload: schemas.LoginRequest, db: Session = Depends(database.get_db)):
    user = db.query(database.User).filter(database.User.username == payload.username).first()
    if not user or not auth.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Username hoặc mật khẩu không đúng")
    token = auth.create_access_token(data={"sub": user.username})
    return schemas.TokenResponse(
        access_token=token, user_id=user.id,
        username=user.username, full_name=user.full_name, role=user.role
    )

@router.get("/auth/me", response_model=schemas.UserResponse, tags=["Auth"])
def get_me(current_user: database.User = Depends(auth.get_current_user)):
    return current_user

# ── CALENDAR ──────────────────────────────────────────────────────────────────
@router.get("/calendar", response_model=schemas.CalendarResponse, tags=["Calendar"])
def get_calendar(
    year: int, month: int,
    current_user: database.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    # 1 query lấy toàn bộ tháng
    schedules = db.query(database.Schedule).filter(
        and_(database.Schedule.date >= first_day, database.Schedule.date <= last_day)
    ).all()

    # Tổ chức: { "YYYY-MM-DD": { "09:00": [schedule,...], ... } }
    schedule_map: dict = {}
    for s in schedules:
        key = s.date.isoformat()
        if key not in schedule_map:
            schedule_map[key] = {h: [] for h in database.ALL_SHIFTS}
        schedule_map[key][s.shift.value].append(s)

    days = []
    for day_num in range(1, last_day.day + 1):
        d = date(year, month, day_num)
        key = d.isoformat()
        day_data = schedule_map.get(key, {h: [] for h in database.ALL_SHIFTS})

        shifts_summary = {}
        for h in database.ALL_SHIFTS:
            slot = day_data.get(h, [])
            user_schedule = next((s for s in slot if s.user_id == current_user.id), None)
            shifts_summary[h] = schemas.ShiftSummary(
                count=len(slot),
                has_registered=user_schedule is not None,
                schedule_id=user_schedule.id if user_schedule else None
            )

        days.append(schemas.DaySummary(date=key, shifts=shifts_summary))

    return schemas.CalendarResponse(days=days)


@router.get("/calendar/detail", response_model=schemas.DayDetailResponse, tags=["Calendar"])
def get_day_detail(
    date_str: str, shift: str,
    current_user: database.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Định dạng ngày không hợp lệ")

    # Validate shift là một trong các giờ hợp lệ
    if shift not in database.ALL_SHIFTS:
        raise HTTPException(status_code=400, detail=f"Giờ không hợp lệ. Phải là một trong: {database.ALL_SHIFTS}")

    schedules = db.query(database.Schedule).filter(
        and_(database.Schedule.date == target_date, database.Schedule.shift == shift)
    ).all()

    attendees = [schemas.UserResponse.model_validate(s.user) for s in schedules]
    return schemas.DayDetailResponse(date=date_str, shift=shift, attendees=attendees)

# ── BOOKING ───────────────────────────────────────────────────────────────────
@router.post("/schedules", response_model=schemas.ScheduleResponse, tags=["Booking"])
def create_schedule(
    payload: schemas.ScheduleCreate,
    current_user: database.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    existing = db.query(database.Schedule).filter(
        and_(
            database.Schedule.user_id == current_user.id,
            database.Schedule.date == payload.date,
            database.Schedule.shift == payload.shift
        )
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Bạn đã đăng ký khung giờ này rồi")

    new_schedule = database.Schedule(user_id=current_user.id, date=payload.date, shift=payload.shift)
    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)
    return new_schedule

@router.delete("/schedules/{schedule_id}", status_code=204, tags=["Booking"])
def delete_schedule(
    schedule_id: int,
    current_user: database.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    schedule = db.query(database.Schedule).filter(database.Schedule.id == schedule_id).first()
    
    # 1. Kiểm tra lịch có tồn tại không
    if not schedule:
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch đăng ký")
        
    # 2. Kiểm tra quyền sở hữu
    if schedule.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Không có quyền hủy lịch của người khác")

    # 3. LOGIC KHÓA 7 NGÀY (Chỉ áp dụng cho User bình thường)
    if current_user.role != "admin":
        from datetime import datetime, date
        today = date.today()
        
        # Ép kiểu schedule.date từ chuỗi String của SQLite về dạng Date chuẩn của Python
        sched_date = schedule.date
        if isinstance(sched_date, str):
            sched_date = datetime.strptime(sched_date, "%Y-%m-%d").date()
        
        days_difference = (sched_date - today).days
        
        # Nếu lịch diễn ra trong vòng 7 ngày đổ lại, hoặc lịch đã qua trong quá khứ
        if days_difference <= 7:
            raise HTTPException(
                status_code=403, 
                detail="LOCKED_7_DAYS"
            )

    # 4. Nếu qua hết các ải trên thì cho phép xóa
    db.delete(schedule)
    db.commit()

# ── ADMIN ─────────────────────────────────────────────────────────────────────
@router.get("/admin/users", response_model=List[schemas.UserResponse], tags=["Admin"])
def get_all_users(admin=Depends(auth.require_admin), db: Session = Depends(database.get_db)):
    return db.query(database.User).all()

@router.post("/admin/users", response_model=schemas.UserResponse, tags=["Admin"])
def create_user(payload: schemas.UserCreate, admin=Depends(auth.require_admin), db: Session = Depends(database.get_db)):
    if db.query(database.User).filter(database.User.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Username đã tồn tại")
    new_user = database.User(
        username=payload.username,
        password_hash=auth.hash_password(payload.password),
        full_name=payload.full_name, role=payload.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.delete("/admin/users/{user_id}", status_code=204, tags=["Admin"])
def delete_user(user_id: int, admin=Depends(auth.require_admin), db: Session = Depends(database.get_db)):
    user = db.query(database.User).filter(database.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Không thể xóa tài khoản admin")
    db.delete(user)
    db.commit()

# API 1: User gửi yêu cầu vắng mặt
@router.post("/absence-requests/", tags=["Absence"])
def create_absence_request(
    req: schemas.AbsenceRequestCreate, 
    db: Session = Depends(database.get_db), 
    current_user: database.User = Depends(auth.get_current_user)
):
    new_request = database.AbsenceRequest(
        user_id=current_user.id,
        schedule_id=req.schedule_id,
        reason=req.reason
    )
    db.add(new_request)
    db.commit()
    return {"message": "Đã gửi yêu cầu chờ duyệt"}

# API 2: Admin lấy danh sách yêu cầu vắng mặt
@router.get("/admin/absence-requests/", tags=["Admin"])
def get_all_requests(
    admin = Depends(auth.require_admin),
    db: Session = Depends(database.get_db)
):
    requests = db.query(database.AbsenceRequest).all()
    # Chuyển đổi thủ công sang dict để tránh lỗi định dạng JSON của SQLAlchemy instance
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "schedule_id": r.schedule_id,
            "reason": r.reason,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None
        } for r in requests
    ]

# API 3: Admin duyệt yêu cầu
@router.put("/admin/absence-requests/{req_id}/status", tags=["Admin"])
def update_absence_status(
    req_id: int,
    payload: schemas.AbsenceStatusUpdate,
    admin=Depends(auth.require_admin),
    db: Session = Depends(database.get_db)
):
    req = db.query(database.AbsenceRequest).filter(
        database.AbsenceRequest.id == req_id
    ).first()
    if not req:
        raise HTTPException(status_code=404, detail="Không tìm thấy request")
    if req.status != "PENDING":
        raise HTTPException(status_code=400, detail="Request này đã được xử lý rồi")

    req.status = payload.status
    req.reviewed_at = datetime.utcnow()

    if payload.status == "ACCEPTED":
        schedule = db.query(database.Schedule).filter(
            database.Schedule.id == req.schedule_id
        ).first()
        if schedule:
            db.delete(req)
            db.flush()
            db.delete(schedule)
    
    db.commit()
    return {"message": f"Đã cập nhật trạng thái thành {payload.status}"}
