# Office Scheduler 📅

Ứng dụng web nội bộ để nhân viên đăng ký và theo dõi lịch lên văn phòng theo ca.

## Tech Stack
- **Backend**: Python FastAPI + SQLAlchemy (ORM) + SQLite (database)
- **Frontend**: HTML/CSS/JS thuần, không cần build tool
- **Auth**: JWT token (lưu localStorage)

---

## Cài đặt & Chạy

### Yêu cầu
- Python 3.9+ (khuyến nghị 3.11)
- pip

### Bước 1: Clone / giải nén project

```bash
cd office-scheduler
```

### Bước 2: Tạo virtual environment (khuyến nghị)

```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate
```

### Bước 3: Cài dependencies

```bash
pip install -r requirements.txt
```

### Bước 4: Chạy server

```bash
# Chạy trên tất cả interfaces (để máy LAN khác truy cập được)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Server sẽ tự tạo file `office_scheduler.db` và tài khoản admin mặc định.

### Bước 5: Truy cập

| URL | Mô tả |
|-----|-------|
| `http://localhost:8000` | Trang đăng nhập |
| `http://<IP-máy-bạn>:8000` | Truy cập từ máy khác trong LAN |
| `http://localhost:8000/docs` | API documentation (Swagger UI) |

---

## Tài khoản mặc định

| Username | Password | Role |
|----------|----------|------|
| `admin`  | `admin123` | Admin |

> ⚠️ Đổi mật khẩu admin sau khi deploy!

---

## Cấu trúc thư mục

```
office-scheduler/
├── main.py                  # Entry point, khởi tạo FastAPI app
├── requirements.txt
├── run.sh                   # Script chạy nhanh (Linux/macOS)
├── office_scheduler.db      # SQLite DB (tự tạo khi chạy lần đầu)
│
├── backend/
│   ├── __init__.py
│   ├── database.py          # SQLAlchemy models (User, Schedule)
│   ├── auth.py              # JWT + bcrypt utilities
│   ├── schemas.py           # Pydantic request/response schemas
│   └── routers.py           # Tất cả API endpoints
│
└── frontend/
    ├── index.html           # Trang đăng nhập
    ├── dashboard.html       # Trang lịch chính
    ├── admin.html           # Trang quản lý nhân viên (admin only)
    └── static/
        ├── css/style.css    # Global styles
        └── js/api.js        # API client + auth helpers dùng chung
```

---

## API Endpoints

| Method | URL | Mô tả | Auth |
|--------|-----|-------|------|
| POST | `/api/auth/login` | Đăng nhập | — |
| GET | `/api/auth/me` | Thông tin user hiện tại | ✓ |
| GET | `/api/calendar?year=&month=` | Tóm tắt lịch cả tháng | ✓ |
| GET | `/api/calendar/detail?date_str=&shift=` | Danh sách người theo ngày+ca | ✓ |
| POST | `/api/schedules` | Đăng ký ca làm việc | ✓ |
| DELETE | `/api/schedules/{id}` | Hủy đăng ký | ✓ |
| GET | `/api/admin/users` | Danh sách nhân viên | Admin |
| POST | `/api/admin/users` | Tạo tài khoản | Admin |
| DELETE | `/api/admin/users/{id}` | Xóa tài khoản | Admin |

---

## Tìm IP máy chủ để share cho đồng nghiệp

```bash
# Windows:
ipconfig

# macOS/Linux:
hostname -I
```

Ví dụ: IP là `192.168.1.10` → đồng nghiệp truy cập `http://192.168.1.10:8000`

---

## Mở rộng sau này (gợi ý)

- [ ] Tự đổi mật khẩu trong profile
- [ ] Xuất Excel danh sách lịch theo tháng
- [ ] Gửi email nhắc nhở tự động
- [ ] Giới hạn số người tối đa mỗi ca
- [ ] Chuyển sang PostgreSQL khi team lớn hơn
