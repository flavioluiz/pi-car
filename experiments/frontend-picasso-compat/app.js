const navItems = document.querySelectorAll(".nav-item");
const pages = document.querySelectorAll(".page");
const subtabGroups = document.querySelectorAll(".subtabs");
const jumpButtons = document.querySelectorAll("[data-jump]");
const clock = document.getElementById("clock");
const themeButtons = document.querySelectorAll(".theme-card[data-theme]");
const themePreviewName = document.getElementById("theme-preview-name");
const themePreviewCopy = document.getElementById("theme-preview-copy");

const themeDescriptions = {
    "picasso-red": "Default cockpit",
    "signal-cyan": "Cooler telemetry look",
    "amber-dusk": "Warmer night panel"
};

function showPage(pageId) {
    navItems.forEach((item) => {
        item.classList.toggle("active", item.dataset.page === pageId);
    });

    const appShell = document.querySelector(".app-shell");
    if (appShell) {
        appShell.classList.toggle("page-home-active", pageId === "home");
    }

    const panelIdMap = {
        home: "panel-home",
        music: "panel-music",
        navigation: "panel-gps",
        vehicle: "panel-vehicle",
        radio: "panel-radio",
        settings: "panel-settings"
    };

    pages.forEach((page) => {
        page.classList.toggle("active", page.id === panelIdMap[pageId]);
    });
}

navItems.forEach((item) => {
    item.addEventListener("click", () => {
        showPage(item.dataset.page);
    });
});

jumpButtons.forEach((button) => {
    button.addEventListener("click", () => {
        showPage(button.dataset.jump);
    });
});

subtabGroups.forEach((group) => {
    const subtabs = group.querySelectorAll(".subtab, .music-tab, .radio-tab");
    const page = group.closest(".page");
    if (!page) return;

    subtabs.forEach((subtab) => {
        subtab.addEventListener("click", () => {
            subtabs.forEach((item) => item.classList.remove("active"));
            subtab.classList.add("active");

            const targetId = subtab.dataset.subtab
                || (subtab.dataset.music ? `music-${subtab.dataset.music}` : "")
                || (subtab.dataset.radio ? `radio-${subtab.dataset.radio}` : "");

            page.querySelectorAll(".subpage").forEach((subpage) => {
                subpage.classList.toggle("active", subpage.id === targetId);
            });
        });
    });
});

function updateClock() {
    if (!clock) return;
    const now = new Date();
    clock.textContent = now.toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false
    });
}

function applyTheme(themeName, label) {
    document.body.dataset.theme = themeName;

    themeButtons.forEach((button) => {
        button.classList.toggle("active", button.dataset.theme === themeName);
    });

    const resolvedLabel = label || document.querySelector(`[data-theme="${themeName}"]`)?.dataset.themeLabel || themeName;
    const resolvedCopy = themeDescriptions[themeName] || "";

    if (themePreviewName) themePreviewName.textContent = resolvedLabel;
    if (themePreviewCopy) themePreviewCopy.textContent = resolvedCopy;

    localStorage.setItem("picasso-compat-theme", themeName);
}

themeButtons.forEach((button) => {
    button.addEventListener("click", () => {
        applyTheme(button.dataset.theme, button.dataset.themeLabel);
    });
});

applyTheme(localStorage.getItem("picasso-compat-theme") || "picasso-red");
updateClock();
setInterval(updateClock, 1000);
