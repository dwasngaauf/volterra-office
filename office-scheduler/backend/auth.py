# backend/auth.py
# Xử lý mã hóa mật khẩu và tạo/xác thực JWT token

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from . import database

# ─── Cấu hình JWT ────────────────────────────────────────────────────────────
# SECRET_KEY: Đổi thành chuỗi ngẫu nhiên dài khi deploy thực tế
SECRET_KEY = "office-scheduler-secret-key-change-in-production-2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # Token hết hạn sau 8 giờ (1 ngày làm việc)

# ─── Bcrypt context để hash mật khẩu ─────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme: lấy token từ header Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """So sánh mật khẩu nhập vào với hash lưu trong DB."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Tạo bcrypt hash từ mật khẩu plain text."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Tạo JWT token chứa thông tin user."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db)
) -> database.User:
    """
    Dependency: Giải mã JWT token và trả về user hiện tại.
    Dùng làm dependency trong các route cần authentication.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token không hợp lệ hoặc đã hết hạn",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(database.User).filter(database.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


def require_admin(current_user: database.User = Depends(get_current_user)) -> database.User:
    """Dependency: Chỉ cho phép admin truy cập route."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ admin mới có quyền thực hiện thao tác này"
        )
    return current_user
