/**
 * EduMatch - Provider Workspace Unified Navigation & State
 */
(function() {
    "use strict";

    const API_BASE = window.location.protocol.startsWith("http")
        ? (window.location.origin + "/api")
        : "http://127.0.0.1:5000/api";

    function getAuthHeaders() {
        const token = localStorage.getItem("edumatch_token");
        const headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        };
        if (token) headers["Authorization"] = "Bearer " + token;
        return headers;
    }

    // Determine current active page
    function getCurrentPageKey() {
        const path = window.location.pathname.toLowerCase();
        if (path.includes("dashboard")) return "dashboard";
        if (path.includes("profile")) return "profile";
        if (path.includes("services")) return "services";
        if (path.includes("portfolio")) return "portfolio";
        if (path.includes("skills")) return "skills";
        if (path.includes("certifications")) return "certifications";
        if (path.includes("requests")) return "requests";
        if (path.includes("order-details") || path.includes("orders")) return "orders";
        if (path.includes("chat")) return "chat";
        if (path.includes("earnings")) return "earnings";
        if (path.includes("settings")) return "settings";
        return "dashboard";
    }

    // Render canonical sidebar HTML if #sidebar or aside.sidebar is present
    function buildCanonicalSidebar() {
        const sidebarEl = document.getElementById("sidebar") || document.querySelector("aside.sidebar");
        if (!sidebarEl) return;

        const currentKey = getCurrentPageKey();

        const navHtml = `
            <a href="dashboard.html" class="sidebar-brand">
                <div class="logo-text">Edu<span>Match</span></div>
                <span class="provider-badge">Provider</span>
            </a>

            <a href="profile.html" class="sidebar-account" title="View & Edit Provider Profile">
                <div class="sidebar-avatar" id="sidebarAvatar">P</div>
                <div class="sidebar-user-meta">
                    <strong id="sidebarProviderName">Loading...</strong>
                    <div class="status-row">
                        <span class="status-dot"></span>
                        <span>Project Provider</span>
                    </div>
                </div>
            </a>

            <div class="nav-section-title">Workspace</div>
            <nav class="sidebar-nav">
                <a href="dashboard.html" class="sidebar-link ${currentKey === 'dashboard' ? 'active' : ''}">
                    <span class="link-icon">⌂</span> Dashboard
                </a>
                <a href="profile.html" class="sidebar-link ${currentKey === 'profile' ? 'active' : ''}">
                    <span class="link-icon">👤</span> My Profile
                </a>
                <a href="services.html" class="sidebar-link ${currentKey === 'services' ? 'active' : ''}">
                    <span class="link-icon">🛠️</span> Services & Pricing
                </a>
                <a href="portfolio.html" class="sidebar-link ${currentKey === 'portfolio' ? 'active' : ''}">
                    <span class="link-icon">💼</span> My Portfolio
                </a>
                <a href="skills.html" class="sidebar-link ${currentKey === 'skills' ? 'active' : ''}">
                    <span class="link-icon">⚡</span> My Skills
                </a>
                <a href="certifications.html" class="sidebar-link ${currentKey === 'certifications' ? 'active' : ''}">
                    <span class="link-icon">📜</span> Certifications
                </a>
            </nav>

            <div class="nav-section-title">Collaboration</div>
            <nav class="sidebar-nav">
                <a href="requests.html" class="sidebar-link ${currentKey === 'requests' ? 'active' : ''}">
                    <span class="link-icon">📥</span> Project Requests
                </a>
                <a href="orders.html" class="sidebar-link ${currentKey === 'orders' ? 'active' : ''}">
                    <span class="link-icon">📦</span> My Orders
                </a>
                <a href="chat.html" class="sidebar-link ${currentKey === 'chat' ? 'active' : ''}">
                    <span class="link-icon">💬</span> Messages & Chat
                </a>
                <a href="earnings.html" class="sidebar-link ${currentKey === 'earnings' ? 'active' : ''}">
                    <span class="link-icon">💰</span> Earnings & Payouts
                </a>
            </nav>

            <div class="sidebar-footer">
                <a href="settings.html" class="sidebar-link ${currentKey === 'settings' ? 'active' : ''}">
                    <span class="link-icon">⚙️</span> Settings
                </a>
                <a href="../index.html" class="sidebar-link">
                    <span class="link-icon">🌐</span> Back to Website
                </a>
                <a href="#" class="sidebar-link logout-link" id="sidebarLogoutBtn">
                    <span class="link-icon">🚪</span> Log Out
                </a>
            </div>
        `;

        sidebarEl.innerHTML = navHtml;

        // Wire logout
        const logoutBtn = document.getElementById("sidebarLogoutBtn");
        if (logoutBtn) {
            logoutBtn.addEventListener("click", (e) => {
                e.preventDefault();
                if (confirm("Are you sure you want to log out of your provider workspace?")) {
                    localStorage.removeItem("edumatch_token");
                    localStorage.removeItem("edumatch_user");
                    localStorage.removeItem("eduMatchUser");
                    localStorage.removeItem("edumatch_provider_photo");
                    window.location.href = "login.html";
                }
            });
        }
    }

    // Fetch and populate provider details into sidebar
    async function syncProviderProfile() {
        const token = localStorage.getItem("edumatch_token");
        if (!token) return;

        // Quick populate from cached storage
        try {
            const cachedName = localStorage.getItem("edumatch_provider_name") || localStorage.getItem("providerName");
            const cachedPhoto = localStorage.getItem("edumatch_provider_photo");
            if (cachedName) {
                const nameEl = document.getElementById("sidebarProviderName") || document.getElementById("providerName");
                if (nameEl) nameEl.textContent = cachedName;
            }
            if (cachedPhoto) {
                const avatarEl = document.getElementById("sidebarAvatar") || document.getElementById("providerAvatar");
                if (avatarEl) {
                    avatarEl.innerHTML = `<img src="${cachedPhoto}" alt="Avatar">`;
                }
            }
        } catch(e) {}

        // Network fetch for active profile
        try {
            const res = await fetch(`${API_BASE}/provider/profile`, {
                headers: getAuthHeaders(),
                credentials: "include"
            });
            if (res.ok) {
                const data = await res.json();
                if (data.profile) {
                    const prof = data.profile;
                    const name = prof.name || prof.full_name || "Provider Account";
                    const photo = prof.profile_photo || "";

                    localStorage.setItem("edumatch_provider_name", name);
                    if (photo) {
                        localStorage.setItem("edumatch_provider_photo", photo);
                    } else {
                        localStorage.removeItem("edumatch_provider_photo");
                    }

                    const nameEl = document.getElementById("sidebarProviderName") || document.getElementById("providerName");
                    if (nameEl) nameEl.textContent = name;

                    const avatarEl = document.getElementById("sidebarAvatar") || document.getElementById("providerAvatar");
                    if (avatarEl) {
                        if (photo) {
                            avatarEl.innerHTML = `<img src="${photo}" alt="${name}">`;
                        } else {
                            avatarEl.textContent = name.charAt(0).toUpperCase();
                        }
                    }
                }
            }
        } catch(err) {
            console.warn("Could not sync provider profile:", err);
        }
    }

    // Mobile menu toggle
    function initMobileMenu() {
        const toggleBtn = document.getElementById("menuToggle") || document.querySelector(".menu-button");
        const sidebar = document.getElementById("sidebar") || document.querySelector("aside.sidebar");
        if (!toggleBtn || !sidebar) return;

        // Add overlay if missing
        let overlay = document.querySelector(".sidebar-overlay");
        if (!overlay) {
            overlay = document.createElement("div");
            overlay.className = "sidebar-overlay";
            document.body.appendChild(overlay);
        }

        toggleBtn.addEventListener("click", () => {
            sidebar.classList.toggle("open");
            overlay.classList.toggle("active");
        });

        overlay.addEventListener("click", () => {
            sidebar.classList.remove("open");
            overlay.classList.remove("active");
        });
    }

    // Initialize when DOM is ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => {
            buildCanonicalSidebar();
            syncProviderProfile();
            initMobileMenu();
        });
    } else {
        buildCanonicalSidebar();
        syncProviderProfile();
        initMobileMenu();
    }
})();
