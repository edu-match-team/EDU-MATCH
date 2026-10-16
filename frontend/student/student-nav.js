/**
 * EduMatch - Student Portal Navigation & Notification Bell
 */
(function() {
    "use strict";

    const API_BASE = window.location.protocol.startsWith("http")
        ? (window.location.origin + "/api")
        : "http://127.0.0.1:5000/api";

    function getAuthHeaders() {
        const token = localStorage.getItem("edumatch_token");
        const headers = { "Content-Type": "application/json" };
        if (token) headers["Authorization"] = "Bearer " + token;
        return headers;
    }

    // 1. Remove "Notifications" text link from student sidebar
    function removeSidebarNotificationLink() {
        const sidebarLinks = document.querySelectorAll(".nav-link, .sidebar a");
        sidebarLinks.forEach(link => {
            const href = link.getAttribute("href") || "";
            const text = link.textContent.toLowerCase();
            if (href.includes("notifications.html") || (text.includes("notification") && !link.closest(".notif-wrapper"))) {
                link.remove();
            }
        });
    }

    // 2. Inject sleek Notification Bell icon to the left of student avatar in topbar
    function setupNotificationBell() {
        // Locate target container: .topbar-right or .user-menu or header right
        const topbarRight = document.querySelector(".topbar-right") || document.querySelector(".header-right") || document.querySelector(".user-info-wrap");
        const avatarEl = document.getElementById("topbarAvatar") || document.getElementById("userAvatar") || document.querySelector(".avatar");

        if (!topbarRight && !avatarEl) return;

        // Hide any name label to the left of the notification bell
        const nameLabel = document.getElementById("topbarName") || document.querySelector(".student-label");
        if (nameLabel) {
            nameLabel.style.display = "none";
        }

        // Prevent duplicate
        if (document.getElementById("studentNotifBellBtn")) return;

        const notifWrapper = document.createElement("div");
        notifWrapper.className = "student-notif-wrapper";
        notifWrapper.style.cssText = "position: relative; display: inline-flex; align-items: center; margin-right: 12px;";

        notifWrapper.innerHTML = `
            <button type="button" id="studentNotifBellBtn" title="View Notifications" aria-label="Notifications" style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:50%; width:40px; height:40px; display:grid; place-items:center; font-size:18px; cursor:pointer; position:relative; transition:all 0.2s ease;">
                🔔
                <span id="studentNotifBadge" style="display:none; position:absolute; top:-3px; right:-3px; background:#ef4444; color:#ffffff; font-size:10px; font-weight:800; border-radius:50%; min-width:18px; height:18px; padding:0 4px; display:flex; align-items:center; justify-content:center; border:2px solid #ffffff; box-shadow:0 2px 5px rgba(239,68,68,0.4);">0</span>
            </button>
            <div id="studentNotifDropdown" style="display:none; position:absolute; top:calc(100% + 12px); right:0; width:340px; background:#ffffff; border-radius:14px; box-shadow:0 12px 35px rgba(15,23,42,0.15); border:1px solid #e2e8f0; z-index:9999; overflow:hidden;">
                <div style="display:flex; justify-content:space-between; align-items:center; padding:12px 16px; background:#f8fafc; border-bottom:1px solid #e2e8f0;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <strong style="font-size:13.5px; color:#0f172a; font-weight:800;">Notifications</strong>
                        <button type="button" id="markReadBellBtn" style="background:#ede9fe; border:none; color:#6d28d9; font-size:11px; font-weight:700; padding:3px 8px; border-radius:5px; cursor:pointer;">✓ Mark read</button>
                    </div>
                    <a href="notifications.html" style="font-size:11.5px; font-weight:700; color:#6c4df6; text-decoration:none;">View all ↗</a>
                </div>
                <div id="studentNotifList" style="max-height:280px; overflow-y:auto; padding:6px 0;">
                    <div style="text-align:center; padding:25px; color:#94a3b8; font-size:12.5px;">Loading notifications...</div>
                </div>
            </div>
        `;

        if (avatarEl && avatarEl.parentNode) {
            avatarEl.parentNode.insertBefore(notifWrapper, avatarEl);
        } else if (topbarRight) {
            topbarRight.prepend(notifWrapper);
        }

        // Dropdown toggle
        const bellBtn = document.getElementById("studentNotifBellBtn");
        const dropdown = document.getElementById("studentNotifDropdown");
        const markReadBtn = document.getElementById("markReadBellBtn");

        if (markReadBtn) {
            markReadBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                markBellNotificationsAsRead();
            });
        }

        if (bellBtn && dropdown) {
            bellBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                dropdown.style.display = dropdown.style.display === "block" ? "none" : "block";
                if (dropdown.style.display === "block") {
                    fetchStudentNotifications();
                }
            });

            document.addEventListener("click", (e) => {
                if (!dropdown.contains(e.target) && e.target !== bellBtn) {
                    dropdown.style.display = "none";
                }
            });
        }
    }

    async function markBellNotificationsAsRead() {
        const badge = document.getElementById("studentNotifBadge");
        if (badge) badge.style.display = "none";

        const notifVal = document.getElementById("notifsStatValue");
        const notifCap = document.getElementById("notifsStatCaption");
        if (notifVal) notifVal.textContent = "0";
        if (notifCap) notifCap.textContent = "All caught up • 0 unread";

        const notifList = document.getElementById("studentNotifList");
        if (notifList) {
            notifList.querySelectorAll("div").forEach(d => {
                if (d.style.background.includes("faf5ff")) {
                    d.style.background = "transparent";
                }
            });
        }

        try {
            const userRaw = localStorage.getItem("eduMatchUser");
            const user = userRaw ? JSON.parse(userRaw) : null;
            await fetch(`${API_BASE}/notifications/mark-read`, {
                method: "POST",
                headers: getAuthHeaders(),
                credentials: "include",
                body: JSON.stringify({ user_id: user ? user.id : null })
            });
        } catch(e) {}
    }

    // 3. Fetch notifications for student
    async function fetchStudentNotifications() {
        const notifList = document.getElementById("studentNotifList");
        const badge = document.getElementById("studentNotifBadge");
        if (!notifList) return;

        try {
            const userRaw = localStorage.getItem("eduMatchUser");
            const user = userRaw ? JSON.parse(userRaw) : null;
            const url = `${API_BASE}/notifications` + (user && user.id ? `?user_id=${user.id}` : "");

            const res = await fetch(url, {
                headers: getAuthHeaders(),
                credentials: "include"
            });
            if (res.ok) {
                const data = await res.json();
                const notifs = data.notifications || [];
                if (badge) {
                    const unread = data.unread_count != null ? data.unread_count : notifs.filter(n => !n.is_read).length;
                    if (unread > 0) {
                        badge.textContent = unread > 9 ? "9+" : unread;
                        badge.style.display = "flex";
                    } else {
                        badge.style.display = "none";
                    }
                }

                if (notifs.length === 0) {
                    notifList.innerHTML = `<div style="text-align:center; padding:25px; color:#94a3b8; font-size:12.5px;">No notifications yet. You're all caught up!</div>`;
                    return;
                }

                notifList.innerHTML = notifs.slice(0, 5).map(n => `
                    <div style="padding:10px 16px; border-bottom:1px solid #f1f5f9; display:flex; gap:10px; align-items:flex-start; text-decoration:none; color:inherit; ${n.is_read ? '' : 'background:#faf5ff;'}">
                        <span style="font-size:16px;">${n.icon || '📌'}</span>
                        <div style="flex:1; min-width:0;">
                            <div style="font-size:12.5px; font-weight:700; color:#1e293b; margin-bottom:2px;">${escapeHtml(n.title || 'Notification')}</div>
                            <div style="font-size:11.5px; color:#64748b; line-height:1.4;">${escapeHtml(n.message || '')}</div>
                            <div style="font-size:10px; color:#94a3b8; margin-top:3px;">${n.created_at ? n.created_at.slice(0, 16) : ''}</div>
                        </div>
                    </div>
                `).join("");
            }
        } catch(e) {
            notifList.innerHTML = `<div style="text-align:center; padding:20px; color:#94a3b8; font-size:12px;">Unable to load live notifications.</div>`;
        }
    }

    function escapeHtml(str) {
        return String(str || "").replace(/[&<>"']/g, c => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
        }[c]));
    }

    // 4. Student Avatar Sync
    function syncStudentAvatar() {
        const uAvatar = document.getElementById("topbarAvatar") || document.getElementById("userAvatar");
        if (!uAvatar) return;
        let u = {};
        try {
            u = JSON.parse(localStorage.getItem("eduMatchUser") || localStorage.getItem("edumatch_user") || "{}");
        } catch(e) {}
        const name = u.fullName || u.full_name || u.name || localStorage.getItem("eduMatchUserName") || localStorage.getItem("studentName") || "Student";
        const uid = u.id || u.user_id;
        let photo = u.profile_photo || (uid ? localStorage.getItem("edumatch_student_photo_" + uid) : "") || "";

        if (photo) {
            uAvatar.innerHTML = `<img src="${photo}" alt="${name}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;display:block;">`;
            uAvatar.style.padding = "0";
            uAvatar.style.overflow = "hidden";
        } else {
            uAvatar.textContent = name.trim().charAt(0).toUpperCase() || "S";
            uAvatar.style.padding = "";
            uAvatar.style.overflow = "";
        }
    }

    // Run on load
    function init() {
        removeSidebarNotificationLink();
        setupNotificationBell();
        syncStudentAvatar();
        fetchStudentNotifications();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
