/* Themed dropdown that replaces a native <select>'s browser popup.
 *
 *   SelectMenu.init(rootElement)      enhance every select.form-select inside root (idempotent)
 *   select._vsUpdate()                refresh the label after changing select.value in code
 *
 * The real <select> stays in the DOM (hidden), so forms, HTMX and existing change handlers keep
 * working: picking an option sets the select and fires a bubbling "change" event.
 * Options may carry  data-short="…"  (label shown on the button)  and  data-dot="#hex"  (status dot).
 * Lists with more than six options get a search box. Translate via window.SELECT_MENU_I18N.
 */
(function () {
  var I18N = function () { return Object.assign({ search: 'Search…', none: 'No match' }, window.SELECT_MENU_I18N || {}); };
  var CHEV = '<svg class="vs-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>';
  var pop = null, popSel = null, popBtn = null, popItems = [], popActive = -1;

  function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function dot(o) { return o && o.dataset.dot ? '<i class="vs-dot" style="background:' + esc(o.dataset.dot) + '"></i>' : ''; }

  function closePop(refocus) {
    if (!pop) return;
    pop.remove();
    popBtn.setAttribute('aria-expanded', 'false');
    if (refocus) popBtn.focus();
    pop = popSel = popBtn = null;
  }

  function pickOption(index) {
    popSel.selectedIndex = index;
    popSel.dispatchEvent(new Event('change', { bubbles: true }));
    closePop(true);
  }

  function openPop(sel, btn) {
    if (pop && popSel === sel) { closePop(true); return; }
    closePop();
    popSel = sel; popBtn = btn; btn.setAttribute('aria-expanded', 'true');
    var opts = Array.prototype.slice.call(sel.options), withSearch = opts.length > 6, text = I18N();
    pop = document.createElement('div');
    pop.className = 'vs-pop';
    var search = null;
    if (withSearch) {
      search = document.createElement('input');
      search.type = 'text'; search.className = 'vs-search'; search.placeholder = text.search; search.autocomplete = 'off';
      pop.appendChild(search);
    }
    var list = document.createElement('ul');
    list.className = 'vs-list'; list.setAttribute('role', 'listbox'); list.tabIndex = -1;
    pop.appendChild(list);
    document.body.appendChild(pop);

    function setActive(n, scroll) {
      var li = list.querySelectorAll('.vs-opt');
      if (!li.length) { popActive = -1; return; }
      popActive = (n + li.length) % li.length;
      li.forEach(function (el, k) { el.classList.toggle('is-active', k === popActive); });
      if (scroll !== false) li[popActive].scrollIntoView({ block: 'nearest' });
    }
    function render(q) {
      q = (q || '').trim().toLowerCase();
      popItems = opts.map(function (o, i) { return { o: o, i: i }; })
        .filter(function (x) { return !q || x.o.text.toLowerCase().indexOf(q) !== -1; });
      list.innerHTML = '';
      if (!popItems.length) {
        var none = document.createElement('li');
        none.className = 'vs-none'; none.textContent = text.none;
        list.appendChild(none); popActive = -1; return;
      }
      popItems.forEach(function (x) {
        var li = document.createElement('li');
        li.className = 'vs-opt' + (x.o.selected ? ' is-selected' : '') + (!x.o.value ? ' is-empty' : '');
        li.setAttribute('role', 'option'); li.setAttribute('aria-selected', x.o.selected ? 'true' : 'false');
        li.dataset.i = x.i;
        li.innerHTML = '<span class="vs-opt__t">' + dot(x.o) + '<span>' + esc(x.o.text) + '</span></span>';
        list.appendChild(li);
      });
      var at = popItems.findIndex(function (x) { return x.o.selected; });
      setActive(at >= 0 ? at : 0);
    }
    render('');

    // Position under the button (above if there is no room); fixed, so a table's scroll area never clips it.
    var r = btn.getBoundingClientRect(), width = Math.max(r.width, 200), rtl = getComputedStyle(btn).direction === 'rtl';
    var left = Math.max(8, Math.min(rtl ? r.right - width : r.left, window.innerWidth - width - 8));
    var below = window.innerHeight - r.bottom - 12, above = r.top - 12, up = below < 200 && above > below;
    var room = Math.min(300, up ? above : below);
    pop.style.left = left + 'px'; pop.style.width = width + 'px';
    if (up) pop.style.bottom = (window.innerHeight - r.top + 4) + 'px'; else pop.style.top = (r.bottom + 4) + 'px';
    list.style.maxHeight = Math.max(120, room - (withSearch ? 46 : 8)) + 'px';

    pop.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); setActive(popActive + 1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(popActive - 1); }
      else if (e.key === 'Enter') { e.preventDefault(); if (popActive >= 0 && popItems[popActive]) pickOption(popItems[popActive].i); }
      else if (e.key === 'Escape') { e.preventDefault(); closePop(true); }
      else if (e.key === 'Tab') closePop();
    });
    if (search) search.addEventListener('input', function () { render(search.value); });
    list.addEventListener('mousemove', function (e) {
      var li = e.target.closest('.vs-opt');
      if (li) setActive(Array.prototype.indexOf.call(list.children, li), false);
    });
    list.addEventListener('mousedown', function (e) {
      var li = e.target.closest('.vs-opt');
      if (li) { e.preventDefault(); pickOption(parseInt(li.dataset.i, 10)); }
    });
    (search || list).focus();
  }

  document.addEventListener('mousedown', function (e) { if (pop && !pop.contains(e.target) && !popBtn.contains(e.target)) closePop(); });
  window.addEventListener('scroll', function (e) { if (pop && !pop.contains(e.target)) closePop(); }, true);
  window.addEventListener('resize', function () { closePop(); });

  function init(root) {
    (root || document).querySelectorAll('select.form-select').forEach(function (sel) {
      if (sel._vsUpdate) return;
      var wrap = document.createElement('div');
      wrap.className = 'vs ' + (sel.className.match(/\bw-(?:xs|sm|md|lg)\b/) || [''])[0];
      var btn = document.createElement('button');
      btn.type = 'button'; btn.className = 'vs-btn';
      btn.setAttribute('aria-haspopup', 'listbox'); btn.setAttribute('aria-expanded', 'false');
      if (sel.getAttribute('aria-label')) btn.setAttribute('aria-label', sel.getAttribute('aria-label'));
      btn.innerHTML = '<span class="vs-val"></span>' + CHEV;
      sel.parentNode.insertBefore(wrap, sel);
      wrap.appendChild(btn); wrap.appendChild(sel);
      sel.style.display = 'none'; sel.tabIndex = -1;
      function update() {
        var o = sel.selectedOptions[0];
        btn.querySelector('.vs-val').innerHTML = o ? dot(o) + '<span>' + esc(o.dataset.short || o.text) + '</span>' : '';
        btn.classList.toggle('is-placeholder', !o || !o.value);
      }
      sel._vsUpdate = update; update();
      sel.addEventListener('change', update);
      btn.addEventListener('click', function () { openPop(sel, btn); });
      btn.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openPop(sel, btn); }
      });
    });
  }

  window.SelectMenu = { init: init };
})();
