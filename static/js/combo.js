/* Themed suggestions for a text input backed by a <datalist> (replaces the browser's own popup).
 *
 *   Combo.init(rootElement)   enhance every input[list] inside root (idempotent)
 *
 * The input stays a normal text input, so free typing, forms and existing "input"/"change" handlers keep
 * working; picking a suggestion sets the value and fires bubbling "input" and "change" events.
 * <option value="Rent" label="note"> shows the label as a muted note on the right.
 * Looks like the dropdowns from select-menu.css (loaded on the same page).
 */
(function () {
  var pop = null, popInput = null, shown = [], active = -1;

  function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  function close() {
    if (pop) { pop.remove(); pop = null; popInput = null; shown = []; active = -1; }
  }

  function setActive(n, scroll) {
    var lis = pop ? pop.querySelectorAll('.vs-opt') : [];
    active = n;
    lis.forEach(function (li, i) {
      li.classList.toggle('is-active', i === n);
      if (i === n && scroll) li.scrollIntoView({ block: 'nearest' });
    });
  }

  function choose(i) {
    var input = popInput, item = shown[i];
    if (!input || !item) return;
    input.value = item.value;
    close();
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function open(input, showAll) {
    close();  // first: it also resets `shown`, which is computed below
    var q = input.value.trim().toLowerCase();
    var all = input._comboItems;
    // Opening on focus/click lists everything; typing narrows the list.
    shown = (showAll || !q) ? all.slice() : all.filter(function (o) { return o.value.toLowerCase().indexOf(q) !== -1; });
    if (!shown.length) return;
    popInput = input;
    pop = document.createElement('div');
    pop.className = 'vs-pop';
    pop.setAttribute('role', 'listbox');
    var list = document.createElement('ul');
    list.className = 'vs-list';
    shown.forEach(function (o, i) {
      var li = document.createElement('li');
      li.className = 'vs-opt' + (o.value.toLowerCase() === q ? ' is-selected' : '');
      li.dataset.i = i;
      li.innerHTML = '<span class="vs-opt__t">' + esc(o.value) + '</span>' + (o.label ? '<span class="vs-opt__sub">' + esc(o.label) + '</span>' : '');
      list.appendChild(li);
    });
    pop.appendChild(list);
    document.body.appendChild(pop);
    var r = input.getBoundingClientRect();
    var below = window.innerHeight - r.bottom - 12, above = r.top - 12;
    var up = below < 180 && above > below;
    var room = Math.min(260, up ? above : below);
    var width = Math.max(r.width, 200);
    var rtl = getComputedStyle(input).direction === 'rtl';
    var left = Math.max(8, Math.min(rtl ? r.right - width : r.left, window.innerWidth - width - 8));
    list.style.maxHeight = Math.max(120, room) + 'px';
    pop.style.width = width + 'px';
    pop.style.left = left + 'px';
    if (up) pop.style.bottom = (window.innerHeight - r.top + 6) + 'px'; else pop.style.top = (r.bottom + 6) + 'px';
    list.addEventListener('mousemove', function (e) {
      var li = e.target.closest('.vs-opt');
      if (li) setActive(parseInt(li.dataset.i, 10), false);
    });
    pop.addEventListener('mousedown', function (e) {
      e.preventDefault();  // keep focus in the input
      var li = e.target.closest('.vs-opt');
      if (li) choose(parseInt(li.dataset.i, 10));
    });
    setActive(-1, false);
  }

  document.addEventListener('mousedown', function (e) {
    if (pop && !pop.contains(e.target) && e.target !== popInput) close();
  });
  window.addEventListener('scroll', function (e) { if (pop && !pop.contains(e.target)) close(); }, true);
  window.addEventListener('resize', close);

  function init(root) {
    (root || document).querySelectorAll('input[list]').forEach(function (input) {
      if (input._comboItems) return;
      var dl = document.getElementById(input.getAttribute('list'));
      if (!dl) return;
      input._comboItems = Array.prototype.map.call(dl.options, function (o) {
        return { value: o.value, label: o.getAttribute('label') || '' };
      });
      input.removeAttribute('list');  // no native popup
      input.setAttribute('autocomplete', 'off');
      input.setAttribute('role', 'combobox');
      input.setAttribute('aria-autocomplete', 'list');
      input.addEventListener('focus', function () { open(input, true); });
      input.addEventListener('click', function () { if (!pop || !pop.isConnected) open(input, true); });
      input.addEventListener('input', function () { open(input, false); });
      input.addEventListener('blur', function () { setTimeout(function () { if (popInput === input) close(); }, 120); });
      input.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
          e.preventDefault();
          if (!pop) { open(input, true); return; }
          var n = active + (e.key === 'ArrowDown' ? 1 : -1);
          setActive(Math.max(0, Math.min(shown.length - 1, n < 0 && e.key === 'ArrowDown' ? 0 : n)), true);
        } else if (e.key === 'Enter' && pop && active >= 0) {
          e.preventDefault();
          choose(active);
        } else if (e.key === 'Escape' && pop) {
          e.stopPropagation();
          close();
        } else if (e.key === 'Tab') {
          close();
        }
      });
    });
  }

  window.Combo = { init: init };
})();
