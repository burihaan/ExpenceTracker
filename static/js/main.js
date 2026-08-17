// main.js — students will add JavaScript here as features are built

(function () {
    var STORAGE_KEY = "spendly-theme";
    var root = document.documentElement;

    function getPreferredTheme() {
        var stored = localStorage.getItem(STORAGE_KEY);
        if (stored === "light" || stored === "dark") {
            return stored;
        }
        return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }

    function applyTheme(theme) {
        root.setAttribute("data-theme", theme);
    }

    applyTheme(getPreferredTheme());

    var toggleButton = document.getElementById("theme-toggle");
    if (toggleButton) {
        toggleButton.addEventListener("click", function () {
            var current = root.getAttribute("data-theme") === "dark" ? "dark" : "light";
            var next = current === "dark" ? "light" : "dark";
            applyTheme(next);
            localStorage.setItem(STORAGE_KEY, next);
        });
    }
})();
