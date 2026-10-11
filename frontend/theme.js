// Universal Theme Management Script for EduMatch
(function() {
    function applySavedTheme() {
        const savedTheme = localStorage.getItem("edumatch_theme") || "light";
        if (savedTheme === "dark") {
            document.documentElement.setAttribute("data-theme", "dark");
        } else {
            document.documentElement.removeAttribute("data-theme");
        }
        updateToggleButton(savedTheme);
    }

    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
        const newTheme = currentTheme === "dark" ? "light" : "dark";
        if (newTheme === "dark") {
            document.documentElement.setAttribute("data-theme", "dark");
            localStorage.setItem("edumatch_theme", "dark");
        } else {
            document.documentElement.removeAttribute("data-theme");
            localStorage.setItem("edumatch_theme", "light");
        }
        updateToggleButton(newTheme);
    }

    function updateToggleButton(theme) {
        const btn = document.getElementById("edumatchThemeToggleBtn");
        if (btn) {
            btn.textContent = theme === "dark" ? "☀️" : "🌙";
            btn.setAttribute("title", theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode");
            btn.setAttribute("aria-label", theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode");
        }
    }

    // Apply immediately to prevent flash
    applySavedTheme();

    document.addEventListener("DOMContentLoaded", function() {
        // Create floating toggle button if not present
        if (!document.getElementById("edumatchThemeToggleBtn")) {
            const btn = document.createElement("button");
            btn.id = "edumatchThemeToggleBtn";
            btn.className = "edumatch-theme-toggle";
            btn.setAttribute("type", "button");
            btn.addEventListener("click", toggleTheme);
            document.body.appendChild(btn);
            const current = localStorage.getItem("edumatch_theme") || "light";
            updateToggleButton(current);
        }
    });
})();
