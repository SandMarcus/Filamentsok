/* Språkvalg: norsk (standard) og engelsk. Siden er skrevet på norsk, og engelsk vises ved å bytte ut tekst i nettleseren.
   Ordlisten ligger i i18n-en.js og lastes bare når engelsk er valgt. Valget huskes i localStorage («lang»).
   Tekst som ikke står i ordlisten (for eksempel produktnavn) vises uendret. */
(function () {
  var KEY = 'lang', ATTRS = ['placeholder', 'aria-label', 'title', 'alt'];
  var btn = document.getElementById('lang');
  var SRC = (document.currentScript && document.currentScript.src) || '';
  var lang = 'no', dict = null, loading = false, obs = null, busy = false;
  try { if (localStorage.getItem(KEY) === 'en') lang = 'en'; } catch (e) {}

  function norm(s) { return s.replace(/\s+/g, ' ').trim(); }

  /* Oversetter én tekst: eksakt treff, «A: B» og «A · B»-deler, og mønstre med tall. */
  function tr(s) {
    var k = norm(s);
    if (!k || !dict) return null;
    var D = dict.map, hit = D[k];
    if (hit !== undefined) return hit;
    var i, m, r;
    for (i = 0; i < dict.rx.length; i++) {
      r = dict.rx[i];
      m = k.match(r[0]);
      if (m) return typeof r[1] === 'function' ? r[1](m, sub) : k.replace(r[0], r[1]);
    }
    var seps = [': ', ' · ', ', ', ' / '];
    for (i = 0; i < seps.length; i++) {
      if (k.indexOf(seps[i]) > 0) {
        var parts = k.split(seps[i]), out = [], any = false;
        parts.forEach(function (p) { var t = tr(p); if (t !== null) { any = true; out.push(t); } else out.push(p); });
        if (any) return out.join(seps[i]);
      }
    }
    return null;
  }

  function sub(x) { var t = tr(x); return t === null ? x : t; }

  function skip(el) {
    var n = el.nodeName;
    return n === 'SCRIPT' || n === 'STYLE' || n === 'TEXTAREA' || n === 'CODE' || n === 'PRE' || n === 'NOSCRIPT' || (el.closest && el.closest('[data-i18n="skip"]'));
  }

  function textNode(n, toEn) {
    var v = n.nodeValue;
    if (toEn) {
      if (n.__t === undefined || v !== n.__t) n.__o = v;       // ny eller endret original
      var t = tr(n.__o);
      if (t === null) { n.__t = undefined; return; }
      var lead = n.__o.match(/^\s*/)[0], trail = n.__o.match(/\s*$/)[0];
      n.__t = lead + t + trail;
      if (n.nodeValue !== n.__t) n.nodeValue = n.__t;
    } else if (n.__t !== undefined) {
      if (n.nodeValue === n.__t) n.nodeValue = n.__o;
      n.__t = undefined;
    }
  }

  function attrs(el, toEn) {
    ATTRS.forEach(function (a) {
      if (!el.hasAttribute || !el.hasAttribute(a)) return;
      var key = '__a_' + a, cur = el.getAttribute(a), rec = el[key];
      if (toEn) {
        if (!rec || cur !== rec.t) rec = el[key] = { o: cur, t: undefined };
        var t = tr(rec.o);
        if (t === null) { rec.t = undefined; return; }
        rec.t = t;
        if (cur !== t) el.setAttribute(a, t);
      } else if (rec && rec.t !== undefined) {
        if (cur === rec.t) el.setAttribute(a, rec.o);
        rec.t = undefined;
      }
    });
  }

  function walk(root, toEn) {
    if (root.nodeType === 3) { if (root.parentNode && !skip(root.parentNode)) textNode(root, toEn); return; }
    if (root.nodeType !== 1 || skip(root)) return;
    attrs(root, toEn);
    var c = root.firstChild;
    while (c) { walk(c, toEn); c = c.nextSibling; }
  }

  function meta(toEn) {
    var d = document.querySelector('meta[name="description"]');
    if (d) {
      if (d.__o === undefined) d.__o = d.getAttribute('content');
      var t = toEn ? tr(d.__o) : null;
      d.setAttribute('content', t !== null ? t : d.__o);
    }
    if (document.__title === undefined) document.__title = document.title;
    var tt = toEn ? tr(document.__title) : null;
    document.title = tt !== null ? tt : document.__title;
  }

  function apply() {
    busy = true;
    if (obs) obs.disconnect();
    var toEn = lang === 'en' && !!dict;
    walk(document.body, toEn);
    meta(toEn);
    document.documentElement.setAttribute('lang', toEn ? 'en' : 'nb');
    if (btn) {
      btn.textContent = toEn ? 'NO' : 'EN';
      btn.setAttribute('aria-label', toEn ? 'Bytt til norsk' : 'Switch language to English');
      btn.setAttribute('title', toEn ? 'Norsk' : 'English');
      btn.setAttribute('aria-pressed', toEn ? 'true' : 'false');
    }
    if (toEn) observe();
    busy = false;
  }

  /* Innhold som siden tegner opp etterpå (kort, filter, tabeller) oversettes når det dukker opp. */
  var pending = false;
  function observe() {
    if (!window.MutationObserver) return;
    if (!obs) {
      obs = new MutationObserver(function (list) {
        if (busy || pending) return;
        pending = true;
        (window.requestAnimationFrame || setTimeout)(function () {
          pending = false;
          if (lang !== 'en' || !dict) return;
          busy = true;
          list = list.concat(obs.takeRecords());   // ikke mist endringer som kom mens vi ventet
          obs.disconnect();
          list.forEach(function (m) {
            if (m.type === 'characterData') walk(m.target, true);
            else if (m.type === 'attributes') attrs(m.target, true);
            else m.addedNodes.forEach(function (n) { walk(n, true); });
          });
          meta(true);
          observe(); busy = false;
        });
      });
    }
    obs.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS });
  }

  function load(cb) {
    if (dict) return cb();
    if (loading) return;
    loading = true;
    var s = document.createElement('script');
    var base = SRC || (document.querySelector('script[src$="i18n.js"]') || {}).src || 'i18n.js';
    s.src = base.replace(/i18n\.js(\?.*)?$/, 'i18n-en.js$1');
    s.onload = function () { dict = window.I18N_EN; loading = false; cb(); };
    s.onerror = function () { loading = false; lang = 'no'; apply(); };
    document.head.appendChild(s);
  }

  function set(l) {
    lang = l;
    try { localStorage.setItem(KEY, l); } catch (e) {}
    if (l === 'en') load(apply); else apply();
  }

  if (btn) btn.addEventListener('click', function () { set(lang === 'en' ? 'no' : 'en'); });
  if (lang === 'en') load(apply); else if (btn) apply();
  window.i18n = { get: function () { return lang; }, set: set };
})();
