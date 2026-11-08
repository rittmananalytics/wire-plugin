// Wire Studio: the theme. System (the default) follows the operating system;
// Light and Dark set data-theme on <html>. Kept per browser. Loaded in the
// page head so the saved theme applies before the page is drawn.
"use strict";
(function () {
  const KEY = "studio-theme";
  const THEMES = ["system", "light", "dark"];
  function saved() { try { const t = localStorage.getItem(KEY); return THEMES.includes(t) ? t : "system"; } catch { return "system"; } }
  function apply(theme) {
    if (theme === "light" || theme === "dark") document.documentElement.setAttribute("data-theme", theme);
    else document.documentElement.removeAttribute("data-theme");
  }
  apply(saved());
  document.addEventListener("DOMContentLoaded", () => {
    const buttons = document.querySelectorAll("#theme-switch [data-theme-choice]");
    function mark(theme) { buttons.forEach((b) => b.setAttribute("aria-checked", String(b.dataset.themeChoice === theme))); }
    buttons.forEach((b) => b.addEventListener("click", () => {
      const theme = b.dataset.themeChoice;
      try { if (theme === "system") localStorage.removeItem(KEY); else localStorage.setItem(KEY, theme); } catch { /* storage blocked */ }
      apply(theme);
      mark(theme);
    }));
    mark(saved());
  });
})();
