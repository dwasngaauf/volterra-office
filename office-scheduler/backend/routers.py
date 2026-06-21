# backend/routers.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
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
        username=user.username, full_name=user.full_name,
        role=user.role, department=user.department,
        employee_code=user.employee_code
    )

@router.get("/auth/me", response_model=schemas.UserResponse, tags=["Auth"])
def get_me(current_user: database.User = Depends(auth.get_current_user)):
    return current_user

@router.put("/auth/change-password", tags=["Auth"])
def change_password(
    payload: schemas.ChangePasswordRequest,
    current_user: database.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    if not auth.verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng")
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu mới phải có ít nhất 6 ký tự")
    current_user.password_hash = auth.hash_password(payload.new_password)
    db.commit()
    return {"message": "Đổi mật khẩu thành công"}

# ── CALENDAR ──────────────────────────────────────────────────────────────────
@router.get("/calendar", response_model=schemas.CalendarResponse, tags=["Calendar"])
def get_calendar(
    year: int, month: int,
    current_user: database.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    schedules = db.query(database.Schedule).options(
        joinedload(database.Schedule.user)
    ).filter(
        and_(database.Schedule.date >= first_day, database.Schedule.date <= last_day)
    ).all()

    # { "YYYY-MM-DD": { "09:00-12:00": [schedule,...], ... } }
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

            # Đếm theo department
            dept_counts = {"hardware": 0, "software": 0, "business": 0}
            for s in slot:
                dept = s.user.department if s.user and s.user.department else None
                if dept in dept_counts:
                    dept_counts[dept] += 1

            shifts_summary[h] = schemas.ShiftSummary(
                count=len(slot),
                has_registered=user_schedule is not None,
                schedule_id=user_schedule.id if user_schedule else None,
                dept_counts=dept_counts
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

    if shift not in database.ALL_SHIFTS:
        raise HTTPException(status_code=400, detail=f"Ca không hợp lệ. Phải là một trong: {database.ALL_SHIFTS}")

    schedules = db.query(database.Schedule).filter(
        and_(database.Schedule.date == target_date, database.Schedule.shift == shift)
    ).order_by(database.Schedule.created_at).all()

    # Sắp xếp: business → hardware → software, rồi theo created_at
    DEPT_ORDER = {"business": 0, "hardware": 1, "software": 2, None: 3}
    schedules.sort(key=lambda s: (
        DEPT_ORDER.get(s.user.department if s.user else None, 3),
        s.created_at or datetime.min
    ))

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

    if not schedule:
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch đăng ký")

    if schedule.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Không có quyền hủy lịch của người khác")

    # Khóa 7 ngày — chỉ áp dụng cho user thường
    if current_user.role != "admin":
        today = date.today()
        sched_date = schedule.date
        if isinstance(sched_date, str):
            sched_date = datetime.strptime(sched_date, "%Y-%m-%d").date()
        if (sched_date - today).days <= 7:
            raise HTTPException(status_code=403, detail="LOCKED_7_DAYS")

    db.delete(schedule)
    db.commit()

# ── ADMIN ─────────────────────────────────────────────────────────────────────
@router.get("/admin/users", response_model=List[schemas.UserResponse], tags=["Admin"])
def get_all_users(admin=Depends(auth.require_admin), db: Session = Depends(database.get_db)):
    return db.query(database.User).all()

@router.post("/admin/users", response_model=schemas.UserResponse, tags=["Admin"])
def create_user(
    payload: schemas.UserCreate,
    admin=Depends(auth.require_admin),
    db: Session = Depends(database.get_db)
):
    if db.query(database.User).filter(database.User.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Username đã tồn tại")
    emp_code = database.generate_employee_code(db)
    new_user = database.User(
        username=payload.username,
        password_hash=auth.hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        department=payload.department,
        employee_code=emp_code
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
    # Xóa absence_requests liên quan trước (PostgreSQL strict foreign key)
    schedule_ids = [s.id for s in db.query(database.Schedule).filter(database.Schedule.user_id == user_id).all()]
    if schedule_ids:
        db.query(database.AbsenceRequest).filter(database.AbsenceRequest.schedule_id.in_(schedule_ids)).delete(synchronize_session=False)
    db.query(database.AbsenceRequest).filter(database.AbsenceRequest.user_id == user_id).delete(synchronize_session=False)
    db.query(database.Schedule).filter(database.Schedule.user_id == user_id).delete(synchronize_session=False)
    db.delete(user)
    db.commit()

@router.put("/admin/users/{user_id}/role", response_model=schemas.UserResponse, tags=["Admin"])
def update_user_role(
    user_id: int,
    payload: schemas.UpdateRoleRequest,
    admin=Depends(auth.require_admin),
    db: Session = Depends(database.get_db)
):
    """Admin cấp/thu hồi quyền admin cho user."""
    user = db.query(database.User).filter(database.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")
    # Không cho tự đổi role của chính mình
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Không thể thay đổi role của chính mình")
    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user

@router.put("/admin/users/{user_id}/department", response_model=schemas.UserResponse, tags=["Admin"])
def update_user_department(
    user_id: int,
    payload: schemas.UpdateDepartmentRequest,
    admin=Depends(auth.require_admin),
    db: Session = Depends(database.get_db)
):
    """Admin đổi department của user."""
    user = db.query(database.User).filter(database.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")
    user.department = payload.department
    db.commit()
    db.refresh(user)
    return user

# ── ABSENCE REQUESTS ──────────────────────────────────────────────────────────
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

@router.get("/admin/absence-requests/", tags=["Admin"])
def get_all_requests(
    admin=Depends(auth.require_admin),
    db: Session = Depends(database.get_db)
):
    requests = db.query(database.AbsenceRequest).all()
    result = []
    for r in requests:
        user = db.query(database.User).filter(database.User.id == r.user_id).first()
        schedule = db.query(database.Schedule).filter(database.Schedule.id == r.schedule_id).first()
        result.append({
            "id": r.id,
            "user_id": r.user_id,
            "user_full_name": user.full_name if user else "?",
            "user_username": user.username if user else "?",
            "user_employee_code": user.employee_code if user else None,
            "schedule_id": r.schedule_id,
            "schedule_date": schedule.date.isoformat() if schedule and schedule.date else None,
            "schedule_shift": schedule.shift.value if schedule and schedule.shift else None,
            "reason": r.reason,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })
    return result

@router.put("/admin/absence-requests/{req_id}/status", tags=["Admin"])
def update_absence_status(
    req_id: int,
    payload: schemas.AbsenceRequestUpdate,
    admin=Depends(auth.require_admin),
    db: Session = Depends(database.get_db)
):
    req = db.query(database.AbsenceRequest).filter(database.AbsenceRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Không tìm thấy request")
    if req.status != "PENDING":
        raise HTTPException(status_code=400, detail="Request này đã được xử lý rồi")

    if payload.status == "ACCEPTED":
        schedule_id = req.schedule_id
        req.status = "ACCEPTED"
        req.reviewed_at = datetime.utcnow()
        sched_to_del = db.query(database.Schedule).filter(database.Schedule.id == schedule_id).first()
        if sched_to_del:
            db.delete(sched_to_del)
    else:
        req.status = "REJECTED"
        req.reviewed_at = datetime.utcnow()

    db.commit()
    return {"message": f"Đã cập nhật trạng thái thành {payload.status}"}
