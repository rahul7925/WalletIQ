/* WalletIQ — UI interactions & responsive helpers */

function toggleSidebar(force) {
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  if (!sidebar || !backdrop) return;
  const open = force !== undefined ? force : !sidebar.classList.contains('open');
  sidebar.classList.toggle('open', open);
  backdrop.classList.toggle('show', open);
  document.body.style.overflow = open ? 'hidden' : '';
}

function closeSidebar() {
  toggleSidebar(false);
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.sidebar .nav-item[href]').forEach(link => {
    link.addEventListener('click', () => {
      if (window.innerWidth <= 1024) closeSidebar();
    });
  });

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeSidebar();
  });
});

/* Chart.js — resize on viewport change */
let _chartResizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(_chartResizeTimer);
  _chartResizeTimer = setTimeout(() => {
    if (typeof Chart === 'undefined') return;
    Object.values(Chart.instances || {}).forEach(chart => {
      try { chart.resize(); } catch (_) {}
    });
  }, 150);
});

/* Observe container size changes (sidebar toggle, etc.) */
if (typeof ResizeObserver !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    const main = document.querySelector('.main-content');
    if (!main || typeof Chart === 'undefined') return;
    new ResizeObserver(() => {
      Object.values(Chart.instances || {}).forEach(c => {
        try { c.resize(); } catch (_) {}
      });
    }).observe(main);
  });
}
