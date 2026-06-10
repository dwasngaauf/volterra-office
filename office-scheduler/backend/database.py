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

# 13 khung giờ từ 9h đến 21h, mỗi ca 1 tiếng
class ShiftEnum(str, enum.Enum):
    h09 = "09:00"
    h10 = "10:00"
    h11 = "11:00"
    h12 = "12:00"
    h13 = "13:00"
    h14 = "14:00"
    h15 = "15:00"
    h16 = "16:00"
    h17 = "17:00"
    h18 = "18:00"
    h19 = "19:00"
    h20 = "20:00"
    h21 = "21:00"

# Danh sách tất cả giờ theo thứ tự (dùng ở nhiều chỗ)
ALL_SHIFTS = [s.value for s in ShiftEnum]

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(10), default="user")
    schedules = relationship("Schedule", back_populates="user", cascade="all, delete-orphan")

class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    shift = Column(Enum(ShiftEnum), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="schedules")
    
class AbsenceRequest(Base):
    __tablename__ = "absence_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    schedule_id = Column(Integer, ForeignKey("schedules.id"))
    reason = Column(String, nullable=False)
    status = Column(String, default="PENDING") # PENDING, ACCEPTED, REJECTED
    created_at = Column(DateTime, default=datetime.utcnow)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
