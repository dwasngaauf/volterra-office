#!/usr/bin/env bash
# setup.sh — Cài đặt và chạy lần đầu

echo "📦 Cài đặt dependencies..."
pip install -r requirements.txt

echo ""
echo "🚀 Khởi động server trên http://0.0.0.0:8000"
echo "   → Máy bạn:       http://localhost:8000"
echo "   → Máy khác LAN:  http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo "🔑 Tài khoản mặc định: admin / admin123"
echo ""

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
