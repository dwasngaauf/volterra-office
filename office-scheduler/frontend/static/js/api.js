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
    full_name: data.full_name, role: data.role,
    department: data.department || null,
    employee_code: data.employee_code || null
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

// ── 4 ca mới ──────────────────────────────────────────────────────────────
const SHIFTS = [
  "09:00-12:00",
  "14:00-16:00",
  "16:00-18:00",
  "18:00-20:00"
];
const SHIFT_LABELS = {
  "09:00-12:00": "9h – 12h",
  "14:00-16:00": "14h – 16h",
  "16:00-18:00": "16h – 18h",
  "18:00-20:00": "18h – 20h",
};

// ── Department colors ──────────────────────────────────────────────────────
const DEPT_COLORS = {
  hardware: "#f97316",   // cam
  software: "#ec4899",   // hồng
  business: "#3b82f6",   // xanh nước biển
};
const DEPT_LABELS = {
  hardware: "Hardware",
  software: "Software",
  business: "Business",
};
const DEPT_ORDER = ["business", "hardware", "software"];

/**
 * Render thanh màu 3 phân khúc dựa trên dept_counts.
 * Trả về HTML string của element .dept-bar
 */
function renderDeptBar(deptCounts, total) {
  if (!total || total === 0) return "";
  const hw  = (deptCounts && deptCounts.hardware)  ? deptCounts.hardware  : 0;
  const sw  = (deptCounts && deptCounts.software)  ? deptCounts.software  : 0;
  const biz = (deptCounts && deptCounts.business)  ? deptCounts.business  : 0;
  const known = hw + sw + biz;

  // Nếu không ai có dept -> bar xám toàn bộ
  if (known === 0) {
    return `<div style="height:6px;border-radius:3px;background:#e2e8f0;margin-bottom:3px;width:100%"></div>`;
  }

  const parts = [
    { dept: "business", n: biz, color: DEPT_COLORS.business },
    { dept: "hardware", n: hw,  color: DEPT_COLORS.hardware },
    { dept: "software", n: sw,  color: DEPT_COLORS.software },
  ].filter(p => p.n > 0);

  const segments = parts.map(p =>
    `<div style="flex:${p.n};background:${p.color};min-width:4px" title="${DEPT_LABELS[p.dept]}: ${p.n}"></div>`
  ).join("");

  return `<div style="display:flex;height:6px;border-radius:3px;overflow:hidden;margin-bottom:3px;width:100%;gap:1px">${segments}</div>`;
}

/**
 * Render badge màu department cho một user
 */
function renderDeptBadge(department) {
  if (!department) return "";
  const color = DEPT_COLORS[department] || "#94a3b8";
  const label = DEPT_LABELS[department] || department;
  return `<span class="dept-badge" style="background:${color}20;color:${color};border:1px solid ${color}40">${label}</span>`;
}

/**
 * Render avatar có màu department
 */
function renderAvatar(name, department, size = "") {
  const color = department ? DEPT_COLORS[department] : "var(--brand)";
  const sizeStyle = size === "sm" ? "width:24px;height:24px;font-size:10px" : "";
  return `<div class="avatar" style="background:${color};${sizeStyle}">${getInitial(name)}</div>`;
}

const DOW_VI   = ["CN","T2","T3","T4","T5","T6","T7"];
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
function getWeekStart(date) {
  const d = new Date(date);
  const dow = d.getDay();
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

// ── CHANGE PASSWORD ────────────────────────────────────────────────────────
async function changePassword(oldPass, newPass) {
  const res = await apiFetch("/auth/change-password", {
    method: "PUT",
    body: JSON.stringify({ old_password: oldPass, new_password: newPass })
  });
  return res;
}

// ── ADMIN: CẬP NHẬT ROLE ──────────────────────────────────────────────────
async function updateUserRole(userId, role) {
  const res = await apiFetch(`/admin/users/${userId}/role`, {
    method: "PUT",
    body: JSON.stringify({ role })
  });
  return res;
}

// ── ADMIN: CẬP NHẬT DEPARTMENT ────────────────────────────────────────────
async function updateUserDepartment(userId, department) {
  const res = await apiFetch(`/admin/users/${userId}/department`, {
    method: "PUT",
    body: JSON.stringify({ department })
  });
  return res;
}

// ── BOOK/CANCEL CẢ NGÀY ───────────────────────────────────────────────────
/**
 * Đăng ký hoặc hủy tất cả ca trong một ngày.
 * action: "book" | "cancel"
 */
async function bookOrCancelDay(dateStr, calData, action) {
  const dayData = calData[dateStr];
  if (!dayData?.shifts) return { ok: 0, fail: 0 };

  let ok = 0, fail = 0;

  for (const shift of SHIFTS) {
    const sd = dayData.shifts[shift];
    if (!sd) continue;

    if (action === "book") {
      if (sd.has_registered) { ok++; continue; } // đã đăng ký rồi
      const res = await apiFetch("/schedules", {
        method: "POST",
        body: JSON.stringify({ date: dateStr, shift })
      });
      if (res && (res.ok || res.status === 409)) ok++; else fail++;
    } else {
      if (!sd.has_registered || !sd.schedule_id) { ok++; continue; }
      const success = await cancelScheduleWithLock(sd.schedule_id, dateStr);
      if (success) ok++; else fail++;
    }
  }

  return { ok, fail };
}

// ── ABSENCE REQUESTS ──────────────────────────────────────────────────────
async function cancelScheduleWithLock(scheduleId, dateStr) {
  try {
    const res = await apiFetch(`/schedules/${scheduleId}`, { method: "DELETE" });

    if (res && res.status === 403) {
      const errorData = await res.json();
      if (errorData.detail === "LOCKED_7_DAYS") {
        const reason = prompt(`Lịch ngày ${dateStr} đã bị khóa (dưới 7 ngày).\nBạn có việc đột xuất? Vui lòng nhập lý do xin vắng mặt để Admin duyệt:`);
        if (reason && reason.trim() !== "") {
          const reqRes = await apiFetch("/absence-requests/", {
            method: "POST",
            body: JSON.stringify({ schedule_id: scheduleId, reason: reason.trim() })
          });
          if (reqRes && reqRes.ok) {
            showToast("Đã gửi yêu cầu xin vắng mặt thành công!", "success");
            return false;
          } else {
            showToast("Lỗi khi gửi yêu cầu vắng mặt", "error");
          }
        } else if (reason !== null) {
          showToast("Lý do không được để trống", "error");
        }
        return false;
      } else {
        showToast(errorData.detail, "error");
        return false;
      }
    }

    if (res && res.ok) {
      showToast("Hủy lịch thành công!", "success");
      return true;
    }
    return false;
  } catch (error) {
    console.error("Lỗi khi hủy lịch:", error);
    showToast("Lỗi kết nối", "error");
    return false;
  }
}

async function getAbsenceRequests() {
  const res = await apiFetch("/admin/absence-requests/");
  if (res && res.ok) return await res.json();
  return [];
}

async function updateRequestStatus(reqId, newStatus) {
  const res = await apiFetch(`/admin/absence-requests/${reqId}/status`, {
    method: "PUT",
    body: JSON.stringify({ status: newStatus })
  });
  if (res && res.ok) {
    showToast("Đã cập nhật trạng thái", "success");
    return true;
  }
  const errorText = await res.text();
  console.error("Lỗi từ server:", errorText);
  showToast("Lỗi khi cập nhật trạng thái", "error");
  return false;
}
