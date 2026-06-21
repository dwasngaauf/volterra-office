# backend/database.py
from sqlalchemy import create_engine, Column, Integer, String, Date, Enum, DateTime, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import enum

import os
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./office_scheduler.db")

# Railway PostgreSQL URL dùng postgres:// nhưng SQLAlchemy cần postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    with engine.connect() as connection:
        connection.execute(text("PRAGMA journal_mode=WAL;"))
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ShiftEnum(str, enum.Enum):
    ca1 = "09:00-12:00"
    ca2 = "14:00-16:00"
    ca3 = "16:00-18:00"
    ca4 = "18:00-20:00"

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
    role          = Column(String(10), default="user")          
    department    = Column(String(20), nullable=True)           
    employee_code = Column(String(20), unique=True, nullable=True) 
    schedules     = relationship("Schedule", back_populates="user", cascade="all, delete-orphan")

class Schedule(Base):
    __tablename__ = "schedules"
    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    date       = Column(Date, nullable=False)
    shift      = Column(String(20), nullable=False)  # Đã chuyển thành VARCHAR để tránh lỗi Enum Postgres
    created_at = Column(DateTime, default=datetime.utcnow)
    user       = relationship("User", back_populates="schedules")

class AbsenceRequest(Base):
    __tablename__ = "absence_requests"
    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id"))
    schedule_id    = Column(Integer, ForeignKey("schedules.id", ondelete="SET NULL"), nullable=True)
    schedule_date  = Column(String(20), nullable=True)  # Lưu cứng thông tin ngày để hiển thị khi schedule bị xóa
    schedule_shift = Column(String(20), nullable=True)  # Lưu cứng ca
    reason         = Column(String, nullable=False)
    status         = Column(String, default="PENDING")   
    created_at     = Column(DateTime, default=datetime.utcnow)
    reviewed_at    = Column(DateTime, nullable=True)

def _backfill_employee_codes(conn):
    rows = conn.execute(text("SELECT id FROM users WHERE employee_code IS NULL ORDER BY id")).fetchall()
    for row in rows:
        uid = row[0]
        code = f"VOL{uid:03d}"
        conn.execute(text("UPDATE users SET employee_code = :code WHERE id = :id"), {"code": code, "id": uid})
    if rows:
        conn.commit()

def generate_employee_code(db) -> str:
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

def execute_safe(conn, query):
    """Thực thi SQL an toàn, tự động bỏ qua nếu đã tồn tại (ngăn sập Postgres transaction)"""
    try:
        conn.execute(text(query))
        conn.commit()
    except Exception:
        conn.rollback()

def init_db():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        # Tự động add các column mới nếu thiếu
        queries = [
            "ALTER TABLE users ADD COLUMN department VARCHAR(20)",
            "ALTER TABLE users ADD COLUMN employee_code VARCHAR(20)",
            "ALTER TABLE absence_requests ADD COLUMN reviewed_at TIMESTAMP",
            "ALTER TABLE absence_requests ADD COLUMN schedule_date VARCHAR(20)",
            "ALTER TABLE absence_requests ADD COLUMN schedule_shift VARCHAR(20)"
        ]
        for q in queries:
            execute_safe(conn, q)
            
        if "postgres" in DATABASE_URL:
            # Đổi kiểu Enum sang Varchar và bỏ khóa ngoại
            execute_safe(conn, "ALTER TABLE schedules ALTER COLUMN shift TYPE VARCHAR(20) USING shift::VARCHAR")
            execute_safe(conn, "ALTER TABLE absence_requests DROP CONSTRAINT absence_requests_schedule_id_fkey")

        _backfill_employee_codes(conn)
