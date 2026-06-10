// api.js — shared utilities
const API_BASE = "/api";

async function apiFetch(path, options = {}) {
  const token = localStorage.getItem("token");
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(API_BASE + path, { ...options, headers });
  if (res.status === 401) {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    window.location.href = "/";
    return;
  }
  return res;
}

function saveAuth(data) {
  localStorage.setItem("token", data.access_token);
  localStorage.setItem("user", JSON.stringify({
    id: data.user_id, username: data.username,
    full_name: data.full_name, role: data.role
  }));
}
function getUser() {
  try { return JSON.parse(localStorage.getItem("user")); } catch { return null; }
}
function logout() {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
  window.location.href = "/";
}
function requireAuth() {
  if (!localStorage.getItem("token")) { window.location.href = "/"; return null; }
  return getUser();
}
function requireAdmin() {
  const u = requireAuth();
  if (u && u.role !== "admin") { window.location.href = "/dashboard"; return null; }
  return u;
}

// Toast
function showToast(msg, type = "success") {
  const c = document.getElementById("toast-container");
  if (!c) return;
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3200);
}

// Helpers
function getInitial(name) { return (name || "?").charAt(0).toUpperCase(); }

const SHIFTS = [
  "09:00","10:00","11:00","12:00","13:00",
  "14:00","15:00","16:00","17:00","18:00",
  "19:00","20:00","21:00"
];
const SHIFT_LABELS = {
  "09:00":"9h","10:00":"10h","11:00":"11h","12:00":"12h","13:00":"13h",
  "14:00":"14h","15:00":"15h","16:00":"16h","17:00":"17h","18:00":"18h",
  "19:00":"19h","20:00":"20h","21:00":"21h"
};
const DOW_VI  = ["CN","T2","T3","T4","T5","T6","T7"];
const MONTH_VI = ["Tháng 1","Tháng 2","Tháng 3","Tháng 4","Tháng 5","Tháng 6",
                  "Tháng 7","Tháng 8","Tháng 9","Tháng 10","Tháng 11","Tháng 12"];

function pad(n) { return String(n).padStart(2,"0"); }
function toDateStr(y,m,d) { return `${y}-${pad(m)}-${pad(d)}`; }
function todayStr() {
  const d = new Date();
  return toDateStr(d.getFullYear(), d.getMonth()+1, d.getDate());
}
function isPast(ds) { return ds < todayStr(); }
function getDaysInMonth(y,m) { return new Date(y,m,0).getDate(); }
function getWeekStart(date) { // Monday
  const d = new Date(date);
  const dow = d.getDay(); // 0=Sun
  const diff = dow === 0 ? -6 : 1 - dow;
  d.setDate(d.getDate() + diff);
  return d;
}
function addDays(date, n) {
  const d = new Date(date);
  d.setDate(d.getDate() + n);
  return d;
}
function formatWeekRange(monday) {
  const sunday = addDays(monday, 6);
  const opts = { day: "numeric", month: "short" };
  return `${monday.toLocaleDateString("vi-VN",opts)} – ${sunday.toLocaleDateString("vi-VN",opts)}, ${sunday.getFullYear()}`;
}
function dateObjToStr(d) {
  return toDateStr(d.getFullYear(), d.getMonth()+1, d.getDate());
}

// ── ABSENCE REQUESTS (XIN VẮNG MẶT) ──────────────────────────────────────────

/**
 * Gọi API Hủy lịch. Nếu server báo lỗi 403 (LOCKED_7_DAYS),
 * tự động hỏi lý do và gọi API xin vắng mặt.
 */
async function cancelScheduleWithLock(scheduleId, dateStr) {
  try {
    const res = await apiFetch(`/schedules/${scheduleId}`, { method: 'DELETE' });

    if (res && res.status === 403) {
      const errorData = await res.json();
      
      // Nếu lỗi là do luật khóa 7 ngày
      if (errorData.detail === "LOCKED_7_DAYS") {
        const reason = prompt(`Lịch ngày ${dateStr} đã bị khóa (dưới 7 ngày).\nBạn có việc đột xuất? Vui lòng nhập lý do xin vắng mặt để Admin duyệt:`);
        
        // Nếu user có nhập lý do và bấm OK
        if (reason && reason.trim() !== "") {
          const reqRes = await apiFetch('/absence-requests/', {
            method: 'POST',
            body: JSON.stringify({
              schedule_id: scheduleId,
              reason: reason.trim()
            })
          });

          if (reqRes && reqRes.ok) {
            showToast("Đã gửi yêu cầu xin vắng mặt thành công!", "success");
            return false; // Báo cho giao diện biết là chưa hủy ngay, đang chờ duyệt
          } else {
            showToast("Lỗi khi gửi yêu cầu vắng mặt", "error");
          }
        } else if (reason !== null) {
            showToast("Lý do không được để trống", "error");
        }
        return false;
      } else {
         // Lỗi 403 khác (vd: xóa lịch của người khác)
         showToast(errorData.detail, "error");
         return false;
      }
    }

    if (res && res.ok) {
      showToast("Hủy lịch thành công!", "success");
      return true; // Báo cho giao diện biết là đã hủy thành công để load lại lịch
    }
    
    return false;

  } catch (error) {
    console.error("Lỗi khi hủy lịch:", error);
    showToast("Lỗi kết nối", "error");
    return false;
  }
}

/**
 * Admin: Lấy danh sách yêu cầu xin vắng mặt
 */
async function getAbsenceRequests() {
  const res = await apiFetch('/admin/absence-requests/');
  if (res && res.ok) {
    return await res.json();
  }
  return [];
}

/**
 * Admin: Duyệt (Chấp nhận / Từ chối) yêu cầu
 */
async function updateRequestStatus(reqId, newStatus) {
  // Thay vì hardcode path ở đây, hãy gọi theo đúng format chuẩn
  const res = await apiFetch(`/admin/absence-requests/${reqId}`, {
    method: 'PUT',
    body: JSON.stringify({ status: newStatus })
  });
  
  if (res && res.ok) {
    showToast(`Đã cập nhật trạng thái`, "success");
    return true;
  }
  
  // Debug lỗi để xem thực hư server trả về cái gì
  const errorText = await res.text();
  console.error("Lỗi từ server:", errorText);
  showToast("Lỗi khi cập nhật trạng thái", "error");
  return false;
}
