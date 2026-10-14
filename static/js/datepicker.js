/* Shared themed date / date-time picker (flatpickr). Styles: static/css/datepicker.css.
   Page sets window.DATEPICKER_I18N = {lang, date, dateTime, today, clear} before loading this file. */
(function () {
  var I18N = window.DATEPICKER_I18N || {};
  var UR = {
    weekdays: { shorthand: ['اتوار', 'پیر', 'منگل', 'بدھ', 'جمعرات', 'جمعہ', 'ہفتہ'], longhand: ['اتوار', 'پیر', 'منگل', 'بدھ', 'جمعرات', 'جمعہ', 'ہفتہ'] },
    months: {
      shorthand: ['جنوری', 'فروری', 'مارچ', 'اپریل', 'مئی', 'جون', 'جولائی', 'اگست', 'ستمبر', 'اکتوبر', 'نومبر', 'دسمبر'],
      longhand: ['جنوری', 'فروری', 'مارچ', 'اپریل', 'مئی', 'جون', 'جولائی', 'اگست', 'ستمبر', 'اکتوبر', 'نومبر', 'دسمبر']
    },
    firstDayOfWeek: 1, rangeSeparator: ' تا ', amPM: ['AM', 'PM'], rtl: true
  };
  var LOCALE = I18N.lang === 'ur' ? UR
    : (flatpickr.l10ns[I18N.lang] || Object.assign({}, flatpickr.l10ns.default, { firstDayOfWeek: 1 }));
  var PREV = '<svg viewBox="0 0 24 24"><path d="M15.4 5.4 14 4l-8 8 8 8 1.4-1.4L8.8 12z"/></svg>';
  var NEXT = '<svg viewBox="0 0 24 24"><path d="M8.6 5.4 10 4l8 8-8 8-1.4-1.4 6.6-6.6z"/></svg>';

  // opts: { time: bool, altClass: 'w-sm'…, onChange: fn }
  function create(el, opts) {
    opts = opts || {};
    if (el._flatpickr) return el._flatpickr;
    var withTime = !!opts.time;
    return flatpickr(el, {
      locale: LOCALE, disableMobile: true, altInput: true, altInputClass: 'form-input fp-alt ' + (opts.altClass || ''),
      altFormat: withTime ? 'j M Y, h:i K' : 'j M Y', dateFormat: withTime ? 'Y-m-d\TH:i' : 'Y-m-d',
      enableTime: withTime, time_24hr: false, minuteIncrement: 5, monthSelectorType: 'dropdown',
      prevArrow: PREV, nextArrow: NEXT,
      onReady: function (sel, str, fp) {
        fp.altInput.placeholder = withTime ? I18N.dateTime : I18N.date;
        fp.altInput.required = el.required;  // the original input becomes hidden, so keep native validation on the visible one
        if (el.id) {  // keep <label for> working: point it at the visible input
          fp.altInput.id = el.id + '-display';
          var lb = document.querySelector('label[for="' + el.id + '"]');
          if (lb) lb.htmlFor = fp.altInput.id;
        }
        var foot = document.createElement('div');
        foot.className = 'fp-foot';
        foot.innerHTML = '<button type="button" data-fp="today"></button><button type="button" data-fp="clear"></button>';
        foot.querySelector('[data-fp=today]').textContent = I18N.today;
        foot.querySelector('[data-fp=clear]').textContent = I18N.clear;
        foot.addEventListener('click', function (e) {
          var b = e.target.closest('button'); if (!b) return;
          if (b.dataset.fp === 'clear') fp.clear();
          else { fp.setDate(new Date(), true); fp.close(); }
        });
        fp.calendarContainer.appendChild(foot);
      },
      onChange: function () { if (opts.onChange) opts.onChange(); }
    });
  }

  // Programmatic set (no change event); falsy iso clears. Plain inputs just get .value.
  function set(el, iso) {
    if (!el._flatpickr) { el.value = iso || ''; return; }
    if (iso) el._flatpickr.setDate(iso, false); else el._flatpickr.clear(false);
  }

  window.AppDatePicker = { create: create, set: set };
})();
