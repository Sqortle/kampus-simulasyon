// Paylaşılan üst bar + sol sidebar'ı her sayfaya enjekte eder.
(function () {
  const groupsHtml = [1, 2, 3, 4, 5, 6, 7, 8]
    .map(i => `<a class="sb-link sub" href="/frontend/grup${i}/">Grup ${i}</a>`)
    .join("");

  const html = `
  <header class="topbar">
    <button class="hamburger" id="navToggle" aria-label="Menüyü aç">
      <span></span><span></span><span></span>
    </button>
    <a href="/" class="tb-logo-wrap">
      <img class="tb-logo" src="/frontend/assets/logo.png" alt="İstanbul Medeniyet Üniversitesi">
    </a>
    <nav class="tb-links">
      <a href="/">Ana Sayfa</a>
      <a href="/frontend/projeler/">Projeler</a>
    </nav>
  </header>
  <div class="sidebar-overlay" id="navOverlay"></div>
  <aside class="sidebar" id="navSidebar">
    <div class="sb-brand"><img src="/frontend/assets/logo.png" alt="İstanbul Medeniyet Üniversitesi"></div>
    <a class="sb-link" href="/">Ana Sayfa</a>
    <div class="sb-group">Örnekler</div>
    <a class="sb-link sub" href="/frontend/ornek-proje3/">Örnek Proje 3 — Enerji ve CO₂</a>
    <div class="sb-group">Gruplar</div>
    ${groupsHtml}
  </aside>`;

  document.body.insertAdjacentHTML("afterbegin", html);

  const footer = `
  <footer class="site-footer">
    <img class="footer-logo" src="/frontend/assets/logo.png" alt="İstanbul Medeniyet Üniversitesi">
    <p>İstanbul Medeniyet Üniversitesi — Kampüs Simülasyonu</p>
    <p>API dokümantasyonu: <a href="/docs">/docs</a></p>
  </footer>`;
  document.body.insertAdjacentHTML("beforeend", footer);

  const sidebar = document.getElementById("navSidebar");
  const overlay = document.getElementById("navOverlay");
  const setOpen = (open) => {
    sidebar.classList.toggle("open", open);
    overlay.classList.toggle("open", open);
  };
  document.getElementById("navToggle").addEventListener("click", () =>
    setOpen(!sidebar.classList.contains("open")));
  overlay.addEventListener("click", () => setOpen(false));

  // Aktif bağlantıyı işaretle
  const path = location.pathname;
  document.querySelectorAll(".sb-link, .tb-links a").forEach(a => {
    const href = a.getAttribute("href");
    if (href === "/") {
      if (path === "/" || path === "/frontend/" || path === "/index.html") a.classList.add("active");
    } else if (path.startsWith(href)) {
      a.classList.add("active");
    }
  });
})();
