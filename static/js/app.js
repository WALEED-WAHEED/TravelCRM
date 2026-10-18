/* ============================================================
   NAHD Travels — app.js
   Lightweight Alpine.js-style interactivity + HTMX helpers
   ============================================================ */

// ── Sidebar toggle ────────────────────────────────────────
// Keep the sidebar list where it was across page loads (every link is a full
// page load, which otherwise resets it to the top), and make sure the current
// page's link is visible.
function initSidebarScroll() {
  var box = document.querySelector('[data-sidebar-scroll]');
  if (!box) return;
  var KEY = 'nahd-sidebar-scroll';
  try {
    var saved = parseInt(sessionStorage.getItem(KEY), 10);
    if (!isNaN(saved)) box.scrollTop = saved;
  } catch (e) { /* storage unavailable */ }
  var active = box.querySelector('.nav-item.active');
  if (active) {
    var a = active.getBoundingClientRect(), b = box.getBoundingClientRect();
    // Scroll only the sidebar list (scrollIntoView would also move the page).
    if (a.top < b.top || a.bottom > b.bottom) box.scrollTop += (a.top - b.top) - (b.height - a.height) / 2;
  }
  function save() { try { sessionStorage.setItem(KEY, String(box.scrollTop)); } catch (e) { /* ignore */ } }
  box.addEventListener('scroll', save, { passive: true });
  window.addEventListener('pagehide', save);
}

function initSidebar() {
  const sidebar = document.getElementById('sidebar');
  const mainContent = document.getElementById('main-content');
  const toggleBtn = document.getElementById('sidebar-toggle');
  if (!sidebar || !toggleBtn) return;

  const COLLAPSED_KEY = 'nahd_sidebar_collapsed';
  if (localStorage.getItem(COLLAPSED_KEY) === 'true') {
    sidebar.classList.add('collapsed');
    mainContent && mainContent.classList.add('sidebar-collapsed');
  }

  // Below 1024px the sidebar is an off-canvas menu; above it, the button collapses it to an icon rail.
  const mobile = window.matchMedia('(max-width: 1023px)');
  const backdrop = document.createElement('div');
  backdrop.className = 'sidebar-backdrop';
  document.body.appendChild(backdrop);
  const setMobileOpen = (open) => {
    sidebar.classList.toggle('mobile-open', open);
    backdrop.classList.toggle('is-open', open);
    document.body.classList.toggle('nav-locked', open);
    toggleBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
  };
  toggleBtn.addEventListener('click', () => {
    if (mobile.matches) { setMobileOpen(!sidebar.classList.contains('mobile-open')); return; }
    sidebar.classList.toggle('collapsed');
    mainContent && mainContent.classList.toggle('sidebar-collapsed');
    localStorage.setItem(COLLAPSED_KEY, sidebar.classList.contains('collapsed'));
  });
  backdrop.addEventListener('click', () => setMobileOpen(false));
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && sidebar.classList.contains('mobile-open')) setMobileOpen(false); });
  sidebar.addEventListener('click', (e) => { if (mobile.matches && e.target.closest('a')) setMobileOpen(false); });
  mobile.addEventListener('change', () => setMobileOpen(false));

  document.querySelectorAll('#sidebar .nav-item').forEach(function (a) {
    var label = a.querySelector('.nav-label');
    if (label && !a.getAttribute('title')) {
      a.setAttribute('title', label.textContent.trim());
    }
  });
}

// ── User dropdown (single document listener — avoids duplicate handlers when HTMX calls initDropdowns) ──
function initDropdowns() {
  if (window.__nahdDropdownDocumentBound) return;
  window.__nahdDropdownDocumentBound = true;

  document.addEventListener('click', function (e) {
    const trigger = e.target.closest('[data-dropdown-trigger]');
    if (trigger) {
      const dropdown = trigger.closest('.dropdown');
      if (!dropdown) return;
      document.querySelectorAll('.dropdown.open').forEach(function (el) {
        if (el !== dropdown) el.classList.remove('open');
      });
      dropdown.classList.toggle('open');
      return;
    }
    if (e.target.closest('.dropdown-menu')) {
      return;
    }
    document.querySelectorAll('.dropdown.open').forEach(function (d) {
      d.classList.remove('open');
    });
  });
}

// ── Modal ─────────────────────────────────────────────────
function openModal(id) {
  const el = document.getElementById(id);
  if (el) { el.classList.remove('hidden'); document.body.style.overflow = 'hidden'; }
}
function closeModal(id) {
  const el = document.getElementById(id);
  if (el) { el.classList.add('hidden'); document.body.style.overflow = ''; }
}
// Close modal on overlay click
document.addEventListener('click', function(e) {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.add('hidden');
    document.body.style.overflow = '';
  }
});

// ── Toast notifications ────────────────────────────────────
function showToast(message, type = 'info', duration = 4000) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      ${type === 'success' ? '<polyline points="20 6 9 17 4 12"/>' :
        type === 'error'   ? '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>' :
        '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>'}
    </svg>
    <span>${message}</span>
  `;
  container.appendChild(toast);
  setTimeout(() => { toast.remove(); }, duration);
}

// ── HTMX event hooks ──────────────────────────────────────
document.body.addEventListener('htmx:afterSwap', function(evt) {
  // Re-init any new dropdowns injected by HTMX
  initDropdowns();
  initPasswordFieldToggles();
  // Close modal after a form submission if data-close-modal is set
  const el = evt.detail.elt;
  if (el.dataset.closeModal) closeModal(el.dataset.closeModal);
});

document.body.addEventListener('htmx:responseError', function(evt) {
  showToast('An error occurred. Please try again.', 'error');
});

// Show response message from HTMX HX-Trigger header
document.body.addEventListener('showMessage', function(evt) {
  showToast(evt.detail.message || 'Done!', evt.detail.type || 'success');
});

// ── Active nav highlighting ───────────────────────────────
function highlightNav() {
  const path = window.location.pathname;
  document.querySelectorAll('.nav-item').forEach(link => {
    const href = link.getAttribute('href') || '';
    if (href && path.startsWith(href)) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });
}

// ── Search debounce ───────────────────────────────────────
function debounce(fn, delay) {
  let t;
  return function(...args) { clearTimeout(t); t = setTimeout(() => fn.apply(this, args), delay); };
}

// ── Theme (persists in localStorage; head script sets initial data-theme) ──
const THEME_KEY = 'nahd-theme';

function setTheme(theme) {
  if (theme !== 'light' && theme !== 'dark') return;
  document.documentElement.setAttribute('data-theme', theme);
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch (e) { /* ignore */ }
}

function bindThemeToggle() {
  if (window.__nahdThemeBound) return;
  window.__nahdThemeBound = true;
  function onThemeClick(e) {
    e.preventDefault();
    e.stopPropagation();
    var cur = document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
    setTheme(cur === 'light' ? 'dark' : 'light');
  }
  /* Direct listeners + capture: reliable when a full-viewport sibling (e.g. login .lp-root) wins hit-testing over document delegation. */
  document.querySelectorAll('.theme-toggle').forEach(function (btn) {
    btn.addEventListener('click', onThemeClick, true);
  });
}

function toggleTheme() {
  var cur = document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
  setTheme(cur === 'light' ? 'dark' : 'light');
}

window.NahdTheme = { set: setTheme, key: THEME_KEY, toggle: toggleTheme };

/* Bind as soon as this script runs so theme works even if DOMContentLoaded already fired. */
bindThemeToggle();

// ── Password visibility (forms using .form-input-wrap--password) ──
function initPasswordFieldToggles() {
  document.querySelectorAll('.form-input-wrap--password').forEach(function (wrap) {
    var input = wrap.querySelector('input');
    var btn = wrap.querySelector('.form-pw-toggle');
    if (!input || !btn || wrap.dataset.pwToggleBound === '1') return;
    wrap.dataset.pwToggleBound = '1';
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      var show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      wrap.classList.toggle('is-password-visible', show);
      btn.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
      btn.setAttribute('aria-pressed', show ? 'true' : 'false');
    });
  });
}

// ── Init ──────────────────────────────────────────────────
// ── Themed dropdown for <select data-nice-select> ───────────────────
// The native <select> stays in the form (and keeps working without JS);
// this draws an app-styled button + menu on top of it.
function initNiceSelects(root) {
  (root || document).querySelectorAll('select[data-nice-select]:not([data-nice-ready])').forEach(function (sel) {
    sel.dataset.niceReady = '1';
    var wrap = document.createElement('div');
    wrap.className = 'nice-select';
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'nice-select__btn';
    btn.setAttribute('aria-haspopup', 'listbox');
    btn.setAttribute('aria-expanded', 'false');
    if (sel.getAttribute('aria-label')) btn.setAttribute('aria-label', sel.getAttribute('aria-label'));
    var list = document.createElement('ul');
    list.className = 'nice-select__menu';
    list.setAttribute('role', 'listbox');
    list.hidden = true;
    sel.parentNode.insertBefore(wrap, sel);
    wrap.appendChild(sel);
    wrap.appendChild(btn);
    wrap.appendChild(list);
    sel.classList.add('nice-select__native');
    sel.tabIndex = -1;

    function paint() {
      var opt = sel.options[sel.selectedIndex];
      var prefix = sel.dataset.prefix;
      btn.innerHTML = '';
      if (prefix) {
        var p = document.createElement('span');
        p.className = 'nice-select__prefix';
        p.textContent = prefix + ':';
        btn.appendChild(p);
      }
      var v = document.createElement('span');
      v.className = 'nice-select__value' + (sel.value ? ' is-set' : '');
      v.textContent = opt ? opt.text : '';
      btn.appendChild(v);
      btn.insertAdjacentHTML('beforeend', '<svg class="nice-select__chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>');
      wrap.classList.toggle('is-set', !!sel.value);
    }
    function build() {
      list.innerHTML = '';
      Array.from(sel.options).forEach(function (o, i) {
        var li = document.createElement('li');
        li.setAttribute('role', 'option');
        li.tabIndex = -1;
        li.className = 'nice-select__opt' + (i === sel.selectedIndex ? ' is-selected' : '');
        li.setAttribute('aria-selected', i === sel.selectedIndex ? 'true' : 'false');
        li.textContent = o.text;
        li.addEventListener('click', function () { choose(i); });
        list.appendChild(li);
      });
    }
    function open(show) {
      if (show) document.querySelectorAll('.nice-select.is-open').forEach(function (w) {
        if (w !== wrap) { w.classList.remove('is-open'); w.querySelector('.nice-select__menu').hidden = true; w.querySelector('.nice-select__btn').setAttribute('aria-expanded', 'false'); }
      });
      list.hidden = !show;
      wrap.classList.toggle('is-open', show);
      btn.setAttribute('aria-expanded', show ? 'true' : 'false');
      if (show) { build(); (list.children[sel.selectedIndex] || list.firstChild).focus(); }
    }
    function choose(i) {
      open(false);
      btn.focus();
      if (i === sel.selectedIndex) return;
      sel.selectedIndex = i;
      paint();
      sel.dispatchEvent(new Event('change', { bubbles: true }));
    }
    btn.addEventListener('click', function () { open(list.hidden); });
    btn.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); open(true); }
    });
    list.addEventListener('keydown', function (e) {
      var items = Array.from(list.children), i = items.indexOf(document.activeElement);
      if (e.key === 'ArrowDown') { e.preventDefault(); (items[i + 1] || items[i]).focus(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); (items[i - 1] || items[i]).focus(); }
      else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); choose(i); }
      else if (e.key === 'Escape') { e.preventDefault(); open(false); btn.focus(); }
      else if (e.key === 'Tab') { open(false); }
    });
    document.addEventListener('click', function (e) { if (!list.hidden && !wrap.contains(e.target)) open(false); });
    paint();
  });
}

document.addEventListener('DOMContentLoaded', function() {
  initNiceSelects();
  initSidebar();
  initSidebarScroll();
  initDropdowns();
  highlightNav();
  initPasswordFieldToggles();
});

// ── Motion: count-up numbers and button ripples ─────────────────────────
(function () {
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // <span data-count="1234">1,234</span> counts up from 0 once, keeping the
  // server's formatting (thousand separators) for the final value.
  function countUp(el) {
    var target = parseFloat(el.getAttribute('data-count'));
    if (!isFinite(target) || target === 0) return;
    var finalText = el.textContent, start = null, dur = 700;
    function step(ts) {
      if (start === null) start = ts;
      var t = Math.min(1, (ts - start) / dur), eased = 1 - Math.pow(1 - t, 3);
      el.textContent = Math.round(target * eased).toLocaleString('en-PK');
      if (t < 1) requestAnimationFrame(step); else el.textContent = finalText;
    }
    requestAnimationFrame(step);
  }

  function ripple(e) {
    var btn = e.target.closest('.btn');
    if (!btn || btn.disabled) return;
    var r = btn.getBoundingClientRect(), size = Math.max(r.width, r.height);
    var dot = document.createElement('span');
    dot.className = 'mv-ripple';
    dot.style.width = dot.style.height = size + 'px';
    dot.style.left = (e.clientX - r.left - size / 2) + 'px';
    dot.style.top = (e.clientY - r.top - size / 2) + 'px';
    btn.appendChild(dot);
    setTimeout(function () { dot.remove(); }, 520);
  }

  document.addEventListener('DOMContentLoaded', function () {
    if (reduce) return;
    document.querySelectorAll('[data-count]').forEach(countUp);
    document.addEventListener('pointerdown', ripple);
  });
})();

// Pop-ups are attached to <body>: inside an animated page section "position: fixed" would follow that section.
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.modal-overlay').forEach(function (el) { if (el.parentNode !== document.body) document.body.appendChild(el); });
});

// ── Confirm dialog ────────────────────────────────────────
// Any form can ask for confirmation before it is sent:
//   <form data-confirm="Message" data-confirm-title="Title" data-confirm-ok="Delete" data-confirm-danger>
(function () {
  var pending = null;
  function box() { return document.getElementById('app-confirm'); }
  function close() { closeModal('app-confirm'); pending = null; }
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form || !form.hasAttribute || !form.hasAttribute('data-confirm') || form.__confirmed || !box()) return;
    e.preventDefault();
    pending = form;
    document.getElementById('app-confirm-title').textContent = form.getAttribute('data-confirm-title') || '';
    document.getElementById('app-confirm-text').textContent = form.getAttribute('data-confirm') || '';
    var ok = document.getElementById('app-confirm-ok'), danger = form.hasAttribute('data-confirm-danger');
    ok.textContent = form.getAttribute('data-confirm-ok') || 'OK';
    ok.classList.toggle('btn-danger', danger);
    ok.classList.toggle('btn-primary', !danger);
    box().classList.toggle('is-danger', danger);
    openModal('app-confirm');
    ok.focus();
  }, true);
  document.addEventListener('click', function (e) {
    if (e.target.closest && e.target.closest('#app-confirm-cancel')) close();
    else if (e.target.closest && e.target.closest('#app-confirm-ok') && pending) {
      var form = pending;
      form.__confirmed = true;
      close();
      form.submit();
    }
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && pending) close(); });
})();

// ── Notification bell: load the latest messages when the menu is opened ──
(function () {
  var menu = document.querySelector('.notif-menu');
  if (!menu) return;
  var trigger = menu.parentElement.querySelector('[data-dropdown-trigger]'), list = document.getElementById('notif-list'), loading = false;
  function load() {
    if (loading) return;
    loading = true;
    fetch(menu.getAttribute('data-notif-url'), { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (r) { return r.ok ? r.text() : Promise.reject(); })
      .then(function (html) { list.innerHTML = html; })
      .catch(function () {})
      .then(function () { loading = false; });
  }
  trigger.addEventListener('click', load);
})();
