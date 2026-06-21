# backend/database.py
from sqlalchemy import create_engine, Column, Integer, String, Date, Enum, DateTime, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import enum

DATABASE_URL = "sqlite:///./office_scheduler.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

with engine.connect() as connection:
    connection.execute(text("PRAGMA journal_mode=WAL;"))

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 4 ca một ngày
class ShiftEnum(str, enum.Enum):
    ca1 = "09:00-12:00"   # Sáng
    ca2 = "14:00-16:00"   # Chiều sớm
    ca3 = "16:00-18:00"   # Chiều
    ca4 = "18:00-20:00"   # Tối

ALL_SHIFTS = [s.value for s in ShiftEnum]

SHIFT_LABELS = {
    "09:00-12:00": "9h – 12h",
    "14:00-16:00": "14h – 16h",
    "16:00-18:00": "16h – 18h",
    "18:00-20:00": "18h – 20h",
}

class DepartmentEnum(str, enum.Enum):
    hardware = "hardware"
    software = "software"
    business = "business"

class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name     = Column(String(100), nullable=False)
    role          = Column(String(10), default="user")          # admin | user
    department    = Column(String(20), nullable=True)           # hardware | software | business
    employee_code = Column(String(20), unique=True, nullable=True)  # VOL001, VOL002, ...
    schedules     = relationship("Schedule", back_populates="user", cascade="all, delete-orphan")

class Schedule(Base):
    __tablename__ = "schedules"
    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    date       = Column(Date, nullable=False)
    shift      = Column(Enum(ShiftEnum), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user       = relationship("User", back_populates="schedules")

class AbsenceRequest(Base):
    __tablename__ = "absence_requests"
    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"))
    schedule_id = Column(Integer, ForeignKey("schedules.id"))
    reason      = Column(String, nullable=False)
    status      = Column(String, default="PENDING")   # PENDING | ACCEPTED | REJECTED
    created_at  = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

def _backfill_employee_codes(conn):
    """Gán mã nhân viên cho các user cũ chưa có."""
    rows = conn.execute(text("SELECT id FROM users WHERE employee_code IS NULL ORDER BY id")).fetchall()
    for row in rows:
        uid = row[0]
        code = f"VOL{uid:03d}"
        conn.execute(text("UPDATE users SET employee_code = :code WHERE id = :id"), {"code": code, "id": uid})
    if rows:
        conn.commit()

def generate_employee_code(db) -> str:
    """Tạo mã nhân viên tiếp theo dạng VOL001."""
    from sqlalchemy import text as t
    result = db.execute(t("SELECT MAX(CAST(SUBSTR(employee_code,4) AS INTEGER)) FROM users WHERE employee_code LIKE 'VOL%'")).fetchone()
    next_num = (result[0] or 0) + 1
    return f"VOL{next_num:03d}"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    # Migration: thêm cột department nếu chưa có (upgrade từ DB cũ)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN department VARCHAR(20)"))
            conn.commit()
        except Exception:
            pass  # Cột đã tồn tại
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN employee_code VARCHAR(20)"))
            conn.commit()
        except Exception:
            pass  # Cột đã tồn tại
        # Backfill employee_code cho user cũ chưa có
        _backfill_employee_codes(conn)
