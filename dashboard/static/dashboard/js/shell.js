(function () {
    "use strict";

    var sidebar = document.getElementById("app-sidebar");
    var toggle = document.querySelector(".sidebar-toggle");
    if (!sidebar || !toggle) return;

    toggle.addEventListener("click", function () {
        var isOpen = sidebar.classList.toggle("is-open");
        toggle.setAttribute("aria-expanded", String(isOpen));
        toggle.setAttribute("aria-label", isOpen ? "Close navigation" : "Open navigation");
    });

    document.addEventListener("click", function (event) {
        if (window.innerWidth <= 760 && sidebar.classList.contains("is-open") &&
            !sidebar.contains(event.target) && !toggle.contains(event.target)) {
            sidebar.classList.remove("is-open");
            toggle.setAttribute("aria-expanded", "false");
            toggle.setAttribute("aria-label", "Open navigation");
        }
    });
}());
