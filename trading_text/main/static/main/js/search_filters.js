(() => {
  const toggle = document.getElementById("filter-toggle");
  const panel = document.getElementById("filter-panel");
  const close = document.getElementById("filter-close");

  if (!toggle || !panel || !close) {
    return;
  }

  const setOpen = (isOpen) => {
    panel.hidden = !isOpen;
    toggle.setAttribute("aria-expanded", String(isOpen));
    toggle.setAttribute("aria-label", isOpen ? "検索条件を閉じる" : "検索条件を開く");
    if (isOpen) {
      panel.querySelector("select")?.focus();
    }
  };

  toggle.addEventListener("click", () => {
    setOpen(panel.hidden);
  });

  close.addEventListener("click", () => {
    setOpen(false);
    toggle.focus();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) {
      setOpen(false);
      toggle.focus();
    }
  });
})();
