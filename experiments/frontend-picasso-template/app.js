const navItems = document.querySelectorAll(".nav-item");
const pages = document.querySelectorAll(".page");
const subtabGroups = document.querySelectorAll(".subtabs");
const jumpButtons = document.querySelectorAll("[data-jump]");
const clock = document.getElementById("clock");

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

updateClock();
setInterval(updateClock, 1000);
