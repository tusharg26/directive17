/* Directive 17 — site behaviour (generated into docs/assets/site.js by build.py) */
(function () {
  'use strict';
  var d = document, root = d.documentElement, body = d.body;
  var RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var $ = function (s, r) { return (r || d).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || d).querySelectorAll(s)); };
  var clamp = function (v, a, b) { a = a === undefined ? 0 : a; b = b === undefined ? 1 : b; return Math.min(b, Math.max(a, v)); };
  var page = body.getAttribute('data-page') || '';
  // room the scrollbar takes (0 on Macs and phones), kept as padding while scrolling is locked
  var lockPad = function (on) {
    if (!on) { root.style.removeProperty('--sbw'); return; }
    if (!root.style.getPropertyValue('--sbw')) root.style.setProperty('--sbw', Math.max(0, innerWidth - root.clientWidth) + 'px');
  };

  /* ---------- old links keep working: /blog/#slug and /#founder-note */
  (function () {
    var h = '';
    try { h = decodeURIComponent(location.hash.slice(1)); } catch (e) { h = location.hash.slice(1); }
    if (!h) return;
    if (page === 'blog') { var a = $$('a.prow').filter(function (x) { return x.getAttribute('data-slug') === h; })[0]; if (a) location.replace(a.getAttribute('href')); }
    
  })();

  /* ---------- headline word reveal */
  requestAnimationFrame(function () { requestAnimationFrame(function () { body.classList.add('shown'); }); });
  setTimeout(function () { body.classList.add('done'); }, RM ? 0 : 2800);

  /* ---------- 'we don't' lines: detect wrapping so the strike follows every line */
  var nts = $$('.way .nt');
  var fitStrike = function () {
    nts.forEach(function (t) {
      var no = t.parentNode, base = no.querySelector('svg'), rs = t.getClientRects();
      $$('svg.extra', no).forEach(function (x) { x.parentNode.removeChild(x); });
      no.classList.toggle('multi', rs.length > 1);
      if (rs.length < 2) { base.removeAttribute('style'); base.classList.remove('ln'); return; }
      var o = no.getBoundingClientRect(), h = parseFloat(getComputedStyle(no).fontSize) * .5;
      [].forEach.call(rs, function (r, k) {
        var sv = k ? base.cloneNode(true) : base;
        if (k) { sv.classList.add('extra'); no.appendChild(sv); }
        sv.classList.add('ln');
        sv.setAttribute('style', 'left:' + (r.left - o.left - r.width * .02) + 'px;top:' + (r.top - o.top + r.height * .62 - h / 2) + 'px;width:' + (r.width * 1.04) + 'px;--k:' + k);
      });
    });
  };
  if (nts.length) { fitStrike(); addEventListener('resize', fitStrike, { passive: true }); if (document.fonts) document.fonts.ready.then(fitStrike); }

  /* ---------- reveal on scroll (headings/blocks; body text is never scrubbed) */
  var rv = $$('.rv, .way');
  if (RM || !('IntersectionObserver' in window)) rv.forEach(function (e) { e.classList.add('in'); });
  else {
    var watch = function (els, margin) {
      var io = new IntersectionObserver(function (es) {
        es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
      }, { rootMargin: margin, threshold: 0 });
      els.forEach(function (e) { io.observe(e); });
    };
    var quick = function (e) { return e.classList.contains('card') || !!e.closest('.ov-page'); };
    watch(rv.filter(function (e) { return !quick(e); }), '0px 0px -8% 0px');
    watch(rv.filter(quick), '0px 0px 4% 0px');
    // something sitting in the last strip of a page (inside the 8% margin above) can never cross the line, because the page cannot
    // scroll any further: once the foot of the page is reached, or the page does not scroll at all, show whatever is on screen
    var atEnd = function () {
      if (innerHeight + scrollY < d.documentElement.scrollHeight - 6) return;
      rv.forEach(function (e) { if (!e.classList.contains('in') && e.getBoundingClientRect().top < innerHeight) e.classList.add('in'); });
    };
    addEventListener('scroll', atEnd, { passive: true }); addEventListener('resize', atEnd); addEventListener('load', atEnd);
    if (d.fonts) d.fonts.ready.then(atEnd); atEnd();
  }


  /* ---------- Companies orbit: one ring with the companies evenly spaced along the track, drifting slowly.
     Hover pauses the orbit, dims the others and names the company in the middle (the enso fades back).
     Click slides the company's overview in from the right; the page stays visible beside it. */
  (function () {
    var orb = $('#orb'); if (!orb) return;
    var pls = $$('.pl', orb), core = $('#core'), ro = $('#readout'), cg = $('#coreG'), cn = $('#coreN'), svg = $('svg.tracks', orb), eIn = $('#trIn');
    var phI = $('#phI'), capI = $('#capI'), lit = null;
    var L = null, t = 0, paused = false, last = performance.now(), offT = null, PER = 240000;
    // arc-length table so items sit (and move) at equal distances along an ellipse
    var track = function (c, r) {
      var N = 720, th = [], len = [0], tot = 0, px = c[0] + r[0] * Math.cos(-Math.PI / 2), py = c[1] + r[1] * Math.sin(-Math.PI / 2);
      for (var k = 0; k <= N; k++) { var a = -Math.PI / 2 + k * 2 * Math.PI / N, x = c[0] + r[0] * Math.cos(a), y = c[1] + r[1] * Math.sin(a);
        if (k) { tot += Math.hypot(x - px, y - py); len.push(tot); } th.push(a); px = x; py = y; }
      return { at: function (f) { f = ((f % 1) + 1) % 1; var s = f * tot, lo = 0, hi = N; while (hi - lo > 1) { var m = (lo + hi) >> 1; if (len[m] < s) lo = m; else hi = m; }
        var a = th[lo] + (th[hi] - th[lo]) * ((s - len[lo]) / ((len[hi] - len[lo]) || 1)); return [c[0] + r[0] * Math.cos(a), c[1] + r[1] * Math.sin(a), a]; }, len: tot };
    };
    var pos = function (el, x, y) { el.style.transform = 'translate(' + x.toFixed(1) + 'px,' + y.toFixed(1) + 'px)'; };
    var layout = function () {
      var W = orb.clientWidth, phone = W < 820, g;  // phones and portrait tablets get a round ring with the group's title above it
      orb.classList.toggle('phone', phone);
      if (!phone) {
        // the ring takes the height of the stage; discs shrink on short or narrow screens so they never crowd each other
        // and the space inside the ring always holds the hover readout
        var H = orb.clientHeight, dI = clamp(Math.min(W * .125, H * .215), 84, 160), rx, ry;
        for (var k = 0; k < 40; k++, dI -= 3) {
          ry = H / 2 - dI / 2 - 10; rx = Math.min(W / 2 - dI / 2 - 8, ry * 1.5);
          var per = 2 * Math.PI * Math.sqrt((rx * rx + ry * ry) / 2);
          if ((ry - dI / 2 - 16 >= 80 && per / pls.length >= dI + 18) || dI <= 70) break;
        }
        var hx = rx - dI / 2 - 18, hy = ry - dI / 2 - 14;
        g = { dI: dI, cI: [W / 2, H / 2], rI: [rx, ry], e: Math.min(320, 1.55 * Math.min(hx, hy)), free: [hx, hy] };
      } else {
        // phones: the group's title above the ring and the company passing the top named below it
        var dI2 = clamp(W * .2, 64, 116), rI2 = Math.min(W / 2 - dI2 / 2 - 8, 250), capH = 56, y;
        pos(phI, 0, 0); y = phI.offsetHeight + 18;
        var cyI = y + rI2 + dI2 / 2; y = cyI + rI2 + dI2 / 2 + 14; pos(capI, 0, y); y += capH;
        orb.style.height = Math.round(y) + 'px';
        g = { dI: dI2, cI: [W / 2, cyI], rI: [rI2, rI2], e: Math.min(300, (rI2 - dI2 / 2 - 12) * 2), phone: 1 };
      }
      if (!phone) orb.style.height = '';
      g.tI = track(g.cI, g.rI);
      pls.forEach(function (x) { x.style.setProperty('--d', g.dI + 'px'); });
      svg.setAttribute('width', W); svg.setAttribute('height', orb.clientHeight);
      eIn.setAttribute('cx', g.cI[0]); eIn.setAttribute('cy', g.cI[1]); eIn.setAttribute('rx', g.rI[0]); eIn.setAttribute('ry', g.rI[1]);
      core.style.width = core.style.height = g.e + 'px'; pos(core, g.cI[0] - g.e / 2, g.cI[1] - g.e / 2);
      L = g; place(); fit();
    };
    // the company name is sized so the whole readout sits inside the free oval within the ring (long names get
    // smaller type and never touch the logos), then centred on the enso
    var textW = function (el) { var rg = d.createRange(); rg.selectNodeContents(el); return rg.getBoundingClientRect().width; };
    var fit = function () {
      if (!L || L.phone) return;
      var hx = L.free[0], hy = L.free[1], fs = Math.min(34, Math.max(18, hy * .37));
      ro.style.width = Math.round(2 * hx * .92) + 'px';
      var ok = function () {
        var tw = Math.max(textW(cn), textW(cg)), th = ro.offsetHeight;
        return cn.scrollWidth <= cn.clientWidth + 1 && cn.offsetHeight <= fs * 1.1 * 3 + 2 &&
          Math.pow(tw / (2 * hx), 2) + Math.pow(th / (2 * hy), 2) <= 1;
      };
      cn.style.fontSize = fs + 'px';
      while (fs > 14 && !ok()) { fs -= 1; cn.style.fontSize = fs + 'px'; }
      pos(ro, L.cI[0] - ro.offsetWidth / 2, L.cI[1] - ro.offsetHeight / 2);
    };
    var place = function () {
      if (!L) return;
      pls.forEach(function (x, i) {
        var q = L.tI.at(t / PER + i / pls.length); x._a = q[2];
        x.style.transform = 'translate(' + (q[0] - L.dI / 2).toFixed(1) + 'px,' + (q[1] - L.dI / 2).toFixed(1) + 'px)';
      });
      if (L.phone) {
        var best = null, bd = 9; pls.forEach(function (x) { var dd = Math.abs(Math.atan2(Math.sin(x._a + Math.PI / 2), Math.cos(x._a + Math.PI / 2))); if (dd < bd) { bd = dd; best = x; } });
        pls.forEach(function (x) { x.classList.toggle('top', x === best); });
        if (best && capI && capI.textContent !== best.getAttribute('data-name')) capI.textContent = best.getAttribute('data-name');
      }
    };
    (function tick(now) { var dt = Math.min(50, now - last); last = now; if (!paused && !RM) { t += dt; place(); } requestAnimationFrame(tick); })(last);
    var light = function (x) {
      clearTimeout(offT); paused = true; lit = x; orb.classList.add('pointing'); pls.forEach(function (y) { y.classList.toggle('on', y === x); });
      cg.textContent = x.getAttribute('data-group'); cn.textContent = x.getAttribute('data-name'); fit();
    };
    var unlight = function () { clearTimeout(offT); offT = setTimeout(function () { paused = false; lit = null; orb.classList.remove('pointing'); pls.forEach(function (y) { y.classList.remove('on'); }); }, 160); };
    pls.forEach(function (x) {
      x.addEventListener('pointerenter', function (e) { if (e.pointerType !== 'touch') light(x); });
      x.addEventListener('pointerleave', unlight); x.addEventListener('focus', function () { light(x); }); x.addEventListener('blur', unlight);
    });
    // overview panel (moved to <body> so it sits above the top bar)
    var drawer = $('#drawer'), scrim = $('#scrim'), BASE = (d.baseURI || location.href).replace(/[#?].*$/, '').replace(/[^/]*$/, '');
    var abs = function (u) { try { return new URL(u, BASE).href; } catch (e) { return u; } };  // the bundled preview has no real base URL
    body.appendChild(scrim); body.appendChild(drawer);
    var pushed = false, opener = null, mainEl = $('#main');
    var openD = function (slug, push) {
      var tp = $('#ov-' + slug); if (!tp) return false;
      var was = root.classList.contains('dopen');
      drawer.innerHTML = tp.innerHTML; drawer.scrollTop = 0;
      $$('[data-src]', drawer).forEach(function (im) { im.src = abs(im.getAttribute('data-src')); });
      $$('a[data-go]', drawer).forEach(function (a) { a.href = abs(a.getAttribute('href')); });
      lockPad(true); root.classList.add('dopen'); drawer.setAttribute('aria-hidden', 'false'); if (mainEl) mainEl.setAttribute('inert', '');
      $('[data-close]', drawer).addEventListener('click', function () { closeD(); });
      try { var u = new URL('companies/' + slug + '.html', BASE).href;
        if (push && !was) { history.pushState({ d: slug }, '', u); pushed = true; } else history.replaceState({ d: slug }, '', u); } catch (e) {}
      var cb = $('[data-close]', drawer); if (cb) cb.focus({ preventScroll: true });
      return true;
    };
    var shut = function () {
      root.classList.remove('dopen'); lockPad(false); drawer.setAttribute('aria-hidden', 'true'); if (mainEl) mainEl.removeAttribute('inert');
      if (opener && opener.isConnected) opener.focus({ preventScroll: true }); opener = null;
    };
    var closeD = function () {
      if (!root.classList.contains('dopen')) return;
      if (pushed) { pushed = false; try { history.back(); return; } catch (e) {} }   // popstate below finishes closing
      shut(); try { history.replaceState(null, '', new URL('companies.html', BASE).href); } catch (e) {}
    };
    d.addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest('.pl, .drawer [data-go]'); if (!a || e.metaKey || e.ctrlKey || e.shiftKey) return;
      var inside = !!a.closest('.drawer'); if (!inside) opener = a;
      if (openD(a.getAttribute('data-slug') || a.getAttribute('data-go'), !inside)) e.preventDefault();
    });
    scrim.addEventListener('click', closeD);
    addEventListener('keydown', function (e) { if (e.key === 'Escape' && root.classList.contains('dopen')) closeD(); });
    addEventListener('popstate', function (e) { if (e.state && e.state.d) openD(e.state.d, false); else { pushed = false; shut(); } });
    // "View as a list" glides down to the list
    var tol = $('.tolist'), allc = $('#all-companies');
    if (tol && allc) tol.addEventListener('click', function (e) { e.preventDefault(); allc.scrollIntoView({ behavior: RM ? 'auto' : 'smooth', block: 'start' }); });
    layout(); addEventListener('resize', layout); if (d.fonts) d.fonts.ready.then(layout);
    window.__orb = { open: function (s) { return openD(s, true); }, light: function (i) { light(pls[i]); } };
  })();

  /* ---------- circular menu: hovering an item dims the others and the enso turns its brush tail toward it */
  var menu = $('#menu'), btn = $('#menuBtn'), circle = $('#circle');
  var setMenu = function () {};
  if (menu && btn && circle) {
    var TAIL = 122, items = $$('a.item', circle), spinEl = $('#spin'), sparkEl = $('#spark'), curRot = 0, offT = null;
    var pointAt = function (deg) {
      var t = deg - TAIL; while (t - curRot > 180) t -= 360; while (t - curRot < -180) t += 360; curRot = t;
      circle.style.setProperty('--rot', curRot + 'deg');   // the enso turns about its clear middle (see .circle .spin), so Contact stays put
      sparkEl.style.transform = 'rotate(' + (TAIL + curRot) + 'deg) translateY(calc(var(--cw) * var(--sw) * -.4096))';
    };
    var light = function (a) { clearTimeout(offT); circle.classList.add('pointing'); items.forEach(function (x) { x.classList.toggle('on', x === a); }); pointAt(+a.getAttribute('data-deg')); };
    var unlight = function () { clearTimeout(offT); offT = setTimeout(function () { circle.classList.remove('pointing'); items.forEach(function (x) { x.classList.remove('on'); }); }, 160); };
    items.forEach(function (a) {
      a.addEventListener('pointerenter', function () { light(a); }); a.addEventListener('focus', function () { light(a); });
      a.addEventListener('pointerleave', unlight); a.addEventListener('blur', unlight);
    });
    // while the menu is open the page behind it can't be tabbed into or scrolled; closing returns focus to the button
    var behind = [$('#main'), $('#ring'), $('.skip')].filter(Boolean);
    setMenu = function (o) {
      var hadFocus = menu.contains(d.activeElement);
      if (o) lockPad(true);
      body.classList.toggle('menu-open', o);
      if (!o && !root.classList.contains('dopen')) lockPad(false);
      behind.forEach(function (x) { if (o) x.setAttribute('inert', ''); else x.removeAttribute('inert'); });
      if (!o && hadFocus) btn.focus();
      btn.setAttribute('aria-expanded', o); btn.setAttribute('aria-label', o ? 'Close menu' : 'Open menu');
      menu.setAttribute('aria-hidden', !o); if (o) menu.removeAttribute('inert'); else menu.setAttribute('inert', '');
      if (o) { var im = $('img', spinEl); im.style.animation = 'none'; void im.offsetWidth; im.style.animation = ''; }
      else { circle.classList.remove('pointing'); items.forEach(function (x) { x.classList.remove('on'); }); }
    };
    btn.addEventListener('click', function () { setMenu(!body.classList.contains('menu-open')); });
    menu.addEventListener('click', function (e) { if (e.target === menu) setMenu(false); });
    addEventListener('keydown', function (e) { if (e.key === 'Escape') setMenu(false); });
    addEventListener('pageshow', function () { setMenu(false); });
    setMenu(false);   // closed and out of reach from the start
  }

  /* ---------- live background on forest sections: drifting points in enso colours that move away from the cursor */
  var COLS = ['227,160,82', '232,116,59', '178,196,170', '251,247,236', '217,139,51'];
  var skies = [], mx = -1e4, my = -1e4;
  addEventListener('pointermove', function (e) { if (e.pointerType === 'touch') return; mx = e.clientX; my = e.clientY; }, { passive: true });
  $$('canvas.skyc').forEach(function (cv) {
    var dpr = Math.min(2, devicePixelRatio || 1), st = { cv: cv, cx: cv.getContext('2d'), pts: [], w: 0, h: 0, vis: false };
    st.fit = function () {
      var w = cv.offsetWidth, h = cv.offsetHeight; if (!w || !h) return;
      st.w = w; st.h = h; cv.width = w * dpr; cv.height = h * dpr; st.cx.setTransform(dpr, 0, 0, dpr, 0, 0);
      var n = Math.min(1600, Math.round(w * h / 1150)); st.pts = [];
      for (var i = 0; i < n; i++) st.pts.push({ x: Math.random() * w, y: Math.random() * h, vx: (Math.random() - .5) * .06, vy: (Math.random() - .5) * .05 - .02,
        s: .8 + Math.random() * 1.9, c: COLS[(Math.random() * COLS.length) | 0], a: .35 + Math.random() * .6, tw: Math.random() * 6.3 });
    };
    st.fit();
    if ('IntersectionObserver' in window) new IntersectionObserver(function (es) { es.forEach(function (e) { st.vis = e.isIntersecting; }); }).observe(cv); else st.vis = true;
    skies.push(st);
  });
  if (skies.length) {
    (function loop(t) {
      skies.forEach(function (st) {
        if (!st.vis || !st.pts.length) return;
        var r = st.cv.getBoundingClientRect(), lx = mx - r.left, ly = my - r.top, c = st.cx;
        c.clearRect(0, 0, st.w, st.h);
        for (var i = 0; i < st.pts.length; i++) {
          var p = st.pts[i];
          if (!RM) { p.x += p.vx; p.y += p.vy; if (p.x < -5) p.x = st.w + 5; if (p.x > st.w + 5) p.x = -5; if (p.y < -5) p.y = st.h + 5; if (p.y > st.h + 5) p.y = -5; }
          var x = p.x, y = p.y, dx = x - lx, dy = y - ly, dd = dx * dx + dy * dy;
          if (dd < 19600) { var dist = Math.sqrt(dd) || 1, k = (1 - dist / 140) * 34; x += dx / dist * k; y += dy / dist * k; }
          var tw = RM ? 1 : .6 + .4 * Math.sin(t * .0015 + p.tw);
          c.fillStyle = 'rgba(' + p.c + ',' + (p.a * tw).toFixed(3) + ')'; c.fillRect(x, y, p.s, p.s);
        }
      });
      requestAnimationFrame(loop);
    })(0);
    addEventListener('resize', function () { skies.forEach(function (s) { s.fit(); }); });
  }

  /* ---------- scroll-driven bits */
  var hooks = [];
  var bar = $('#bar'), navEnso = $('#navEnso'), iris = $('#iris');
  var barTone = function () {
    if (!bar) return;
    var els = d.elementsFromPoint(innerWidth / 2, bar.offsetHeight + 2);
    var under = null; for (var i = 0; i < els.length; i++) if (!bar.contains(els[i])) { under = els[i]; break; }
    var onDark = !!(under && under.closest('.dark,.stick.dk'));
    bar.classList.toggle('inv', onDark); root.classList.toggle('ondark', onDark);
  };
  var lastY = scrollY, vel = 0;
  var onScroll = function () {
    var y = scrollY;
    if (bar) bar.classList.toggle('solid', y > 40 && (!iris || y > iris.offsetHeight - innerHeight + 8));
    vel = Math.min(1, Math.abs(y - lastY) / 60); lastY = y;
    if (!RM) root.style.setProperty('--vel', vel.toFixed(2));
    if (navEnso) navEnso.style.transform = 'rotate(' + (y * .12) + 'deg)';
    hooks.forEach(function (f) { f(); });
    barTone();
  };
  addEventListener('scroll', onScroll, { passive: true });
  addEventListener('resize', onScroll);
  (function settle() { vel *= .9; root.style.setProperty('--vel', vel.toFixed(3)); requestAnimationFrame(settle); })();
  // no rubber-band gap past the very top or bottom of the page
  addEventListener('wheel', function (e) {
    if (e.ctrlKey || body.classList.contains('menu-open')) return;
    var max = root.scrollHeight - innerHeight;
    if ((scrollY <= 0 && e.deltaY < 0) || (scrollY >= max - 1 && e.deltaY > 0)) e.preventDefault();
  }, { passive: false });

  // home cover: the enso grows past the edges and turns; the page turns forest; the subline arrives
  if (iris) {
    var ens = $('#ens'), stage = $('#irisStick'), hh = $('#heroH'), sub = $('#heroSub'), cue = $('#cue');
    if (cue) cue.addEventListener('click', function () { scrollTo({ top: iris.offsetHeight - innerHeight, behavior: RM ? 'auto' : 'smooth' }); });
    hooks.push(function () {
      var r = iris.getBoundingClientRect(), p = clamp(-r.top / (r.height - innerHeight));
      if (RM) p = p > .4 ? 1 : 0;
      ens.style.setProperty('--s', (1 + Math.pow(p, 1.5) * 4.6).toFixed(3)); ens.style.setProperty('--r', (p * 140) + 'deg');
      stage.classList.toggle('dk', p > .36);
      hh.style.transform = 'scale(' + (1 - p * .16) + ')';
      if (cue) { cue.style.opacity = 1 - clamp(p * 7); cue.style.pointerEvents = p > .1 ? 'none' : ''; }
      var so = clamp((p - .46) / .2); sub.style.opacity = so; sub.style.transform = 'translateY(' + ((1 - so) * 16) + 'px)';
    });
  }
  // Why: the beliefs ink in early, so faint text never has to be read
  var fills = $$('.inkfill');
  if (fills.length) hooks.push(function () {
    var h = innerHeight;
    fills.forEach(function (el) { var b = el.getBoundingClientRect(); el.style.setProperty('--p', RM ? 1 : clamp((h * .96 - b.top) / (h * .26)).toFixed(3)); });
  });
  // articles: the small enso completes as you read; click it to go back to the top
  var ring = $('#ring'), ringImg = $('#ringImg'), prose = $('.prose');
  if (ring && prose) {
    hooks.push(function () { var b = prose.getBoundingClientRect(), p = clamp((innerHeight * .6 - b.top) / b.height); ring.classList.toggle('on', p > .02); ringImg.style.setProperty('--a', (p * 360) + 'deg'); });
    ring.addEventListener('click', function () { scrollTo({ top: 0, behavior: RM ? 'auto' : 'smooth' }); });
  }
  onScroll();
  addEventListener('load', onScroll);

  /* ---------- Companies: the tile glow follows the cursor */
  $$('.card, .prow').forEach(function (el) {
    el.addEventListener('pointermove', function (e) {
      var b = el.getBoundingClientRect(); el.style.setProperty('--mx', (e.clientX - b.left) + 'px');
      var t = el.querySelector('.tile');
      if (t) { var tb = t.getBoundingClientRect(); t.style.setProperty('--mx', (e.clientX - tb.left) + 'px'); t.style.setProperty('--my', (e.clientY - tb.top) + 'px'); }
    });
  });

  /* ---------- share: the phone share sheet where there is one, otherwise copy the link */
  var TOUCH = matchMedia('(hover: none)').matches;
  d.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-share]'); if (!b) return;
    e.preventDefault();
    var url = b.getAttribute('data-share'), title = b.getAttribute('data-title') || d.title;
    var done = function () { var t = b.textContent; b.textContent = 'Link copied!'; setTimeout(function () { b.textContent = t; }, 1600); };
    if (navigator.share && TOUCH) { navigator.share({ title: title, url: url }).catch(function () {}); return; }
    var legacy = function () {
      var ta = d.createElement('textarea'); ta.value = url; ta.setAttribute('readonly', ''); ta.style.cssText = 'position:fixed;left:-9999px;top:0;opacity:0';
      body.appendChild(ta); ta.select(); var ok = false; try { ok = d.execCommand('copy'); } catch (er) {} body.removeChild(ta);
      if (ok) done(); else prompt('Copy this link:', url);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(done, legacy);
    else legacy();
  });
})();


/* v16 — home: the founder's-note card opens the whole note in place, like a drop-down */
(function () {
  'use strict';
  var d = document, card = d.querySelector('a.note-card'), full = d.getElementById('note-full');
  if (!card || !full) return;
  card.setAttribute('role', 'button');
  card.setAttribute('aria-controls', 'note-full');
  var set = function (open) {
    card.setAttribute('aria-expanded', open ? 'true' : 'false');
    full.classList.toggle('open', open);
    if (open) full.removeAttribute('inert'); else full.setAttribute('inert', '');
  };
  set(false);
  card.addEventListener('click', function (e) {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) return;   // a modified click still opens the note's own page
    e.preventDefault();
    set(card.getAttribute('aria-expanded') !== 'true');
  });
  card.addEventListener('keydown', function (e) { if (e.key === ' ') { e.preventDefault(); card.click(); } });
  // old links to /#founder-note open the note here instead of leaving the page
  var h = ''; try { h = decodeURIComponent(location.hash.slice(1)); } catch (e) {}
  if (h === 'founder-note') { set(true); card.scrollIntoView({ block: 'start' }); }
})();
