/* =========================================================================
   The curtain — the opening page.

   The locked sting, drawn live in HTML/CSS instead of played from a video
   file. Same choreography as the studio component (REST -> HOLD), run at
   2.4x so a visitor waits ~4s, not 10. At HOLD the lockup flies into the
   header signature and the curtain lifts: one continuous move, no cut.

   Plays once per session. Skippable by click, key or scroll. Reduced motion
   snaps straight to HOLD and lifts.
   ========================================================================= */

(function () {
  "use strict";

  var root = document.querySelector("[data-curtain]");
  if (!root || !window.PF || !window.PF.clockwork) return;

  var SPEED = 2.4;          // studio timeline is 10s; this plays it in ~4.2s
  var INTRO_LEN = 10;
  var HANDOFF_MS = 780;
  var KEY = "pf-curtain-seen";

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var seen = false;
  try { seen = sessionStorage.getItem(KEY) === "1"; } catch (e) { /* private mode */ }

  var standalone = root.hasAttribute("data-standalone");
  var page = standalone ? null : document.querySelector("[data-page]");
  var sig = standalone ? null : document.querySelector(".chrome .sig");

  function release() {
    if (standalone) return;   // the demo page keeps its sting on screen
    root.remove();
    document.documentElement.classList.remove("is-curtained");
    if (page) page.classList.add("is-revealed");
    if (sig) sig.style.opacity = "";
    try { sessionStorage.setItem(KEY, "1"); } catch (e) { /* ignore */ }
  }

  if (seen && !standalone) { release(); return; }

  if (!standalone) document.documentElement.classList.add("is-curtained");
  root.hidden = false;
  if (sig) sig.style.opacity = "0";

  // ------------------------------------------------------------ easing

  function clamp01(x) { return Math.min(1, Math.max(0, x)); }
  function smooth(a, b, t) {
    var x = clamp01((t - a) / Math.max(0.0001, b - a));
    return x * x * (3 - 2 * x);
  }

  var G0 = { op: 0, x: 0, y: -0.7, rot: 12, scale: 0.94 };
  var G1 = { op: 1, x: 0, y: 0, rot: 0, scale: 1 };

  function gearPose(dir, amp) {
    return { op: 0, x: 0, y: -0.62 * dir * amp, rot: 14 * dir * amp, scale: 0.94 };
  }

  /* Damped second-order seating — the letter arrives like a part being set,
     not like a fade. z=0.74, wn=13.5. */
  function gearIn(t, t0, dir, amp) {
    var start = gearPose(dir, amp);
    var tau = t - t0;
    if (tau < 0) return start;
    var z = 0.74, wn = 13.5;
    var wd = wn * Math.sqrt(Math.max(0.08, 1 - z * z));
    var env = Math.exp(-z * wn * tau);
    var k = env * (Math.cos(wd * tau) + (z / Math.sqrt(1 - z * z)) * Math.sin(wd * tau));
    return {
      op: clamp01(tau / 0.07),
      x: start.x * k,
      y: start.y * k,
      rot: start.rot * k,
      scale: 0.96 + 0.04 * (1 - Math.min(1, Math.abs(k))),
    };
  }

  function seat(t, t0, dir, amp) {
    return t >= t0 + 0.5 ? G1 : gearIn(t, t0, dir, amp);
  }

  function gearOut(t, t0, dir, amp) {
    if (t < t0) return G1;
    var u = clamp01((t - t0) / 0.48);
    var s = u * u * (3 - 2 * u);
    var start = gearPose(dir, amp);
    return { op: 1 - s, x: start.x * s, y: start.y * s, rot: start.rot * s, scale: 1 - 0.06 * s };
  }

  function mul(a, b) {
    return {
      op: a.op * b.op, x: a.x + b.x, y: a.y + b.y,
      rot: a.rot + b.rot, scale: a.scale * b.scale,
    };
  }

  function setHand(el, g, extra) {
    if (!el) return;
    el.style.opacity = String(g.op);
    el.style.transform =
      (extra ? extra + " " : "") +
      "translate(" + g.x.toFixed(4) + "em, " + g.y.toFixed(4) + "em) rotate(" +
      g.rot.toFixed(3) + "deg) scale(" + g.scale.toFixed(3) + ")";
  }

  // ------------------------------------------------------------ timeline

  function sampleIntro(u) {
    var crank = 0;
    if (u >= 3.35 && u < 5.2) crank = Math.PI * ((u - 3.35) / 1.85);
    else if (u >= 5.2) crank = Math.PI;
    var travel = window.PF.clockwork.sliderCrank(crank).travel;

    return {
      pY: u < 3.35 ? 0 : travel * 180,      // the P throws, crank-driven
      subOp: smooth(7.0, 7.8, u),
      glow: 18 * smooth(5.7, 6.5, u),
      crank: crank,
      aulSpan: 1 - smooth(3.05, 3.55, u),   // AUL leaves as a group
      markSpan: smooth(5.25, 5.85, u),      // the FRENDACH slot opens
      pGlyph: seat(u, 0.38, 1, 0.42),
      aulGlyphs: [
        mul(gearIn(u, 0.50, 1, 0.4), gearOut(u, 2.88, -1, 0.32)),
        mul(gearIn(u, 0.57, 1, 0.4), gearOut(u, 2.94, -1, 0.32)),
        mul(gearIn(u, 0.64, 1, 0.4), gearOut(u, 3.00, -1, 0.32)),
      ],
      markGlyphs: [
        gearIn(u, 5.92, -1, 0.10),          // F seats into the mirrored P
        gearIn(u, 6.04, -1, 0.16),
        gearIn(u, 6.11, -1, 0.16),
        gearIn(u, 6.18, -1, 0.16),
        gearIn(u, 6.25, -1, 0.16),
        gearIn(u, 6.32, -1, 0.16),
        gearIn(u, 6.39, -1, 0.16),
        gearIn(u, 6.46, -1, 0.16),
      ],
    };
  }

  var HOLD = {
    pY: 180, subOp: 1, glow: 18, crank: Math.PI, aulSpan: 0, markSpan: 1,
    pGlyph: G1, aulGlyphs: [G0, G0, G0],
    markGlyphs: [G1, G1, G1, G1, G1, G1, G1, G1],
  };

  // ------------------------------------------------------------ wiring

  var word = root.querySelector("[data-word]");
  var pEl = root.querySelector("[data-p]");
  var aulEls = Array.prototype.slice.call(root.querySelectorAll("[data-aul] span"));
  var markEls = Array.prototype.slice.call(root.querySelectorAll("[data-mark] span"));
  var subEl = root.querySelector("[data-sub]");
  var movement = window.PF.clockwork.mount(root.querySelector("[data-clock]"), {});

  function apply(s, elapsed) {
    movement.drive(elapsed, s.crank);
    setHand(pEl, s.pGlyph, "rotateY(" + s.pY + "deg)");
    s.aulGlyphs.forEach(function (g, i) { setHand(aulEls[i], g); });
    s.markGlyphs.forEach(function (g, i) { setHand(markEls[i], g); });
    word.style.setProperty("--aul", s.aulSpan.toFixed(4));
    word.style.setProperty("--mark", s.markSpan.toFixed(4));
    word.style.filter = s.glow > 1
      ? "drop-shadow(0 0 " + s.glow + "px rgb(232 195 106 / 0.32))"
      : "none";
    subEl.style.opacity = String(s.subOp);
  }

  // ------------------------------------------------------------ handoff
  // The lockup flies to the header signature's seat, matched on font size and
  // on the left/baseline corner, then the ground fades. No cut, no reload flash.

  var handedOff = false;

  function handoff() {
    if (handedOff) return;
    handedOff = true;
    // On /flash/ the sting simply holds, movement still running.
    if (standalone) return;
    movement.stop();

    var target = sig && sig.getBoundingClientRect();
    if (target && target.width > 0) {
      var from = word.getBoundingClientRect();
      var scale = parseFloat(getComputedStyle(sig).fontSize) /
                  parseFloat(getComputedStyle(word).fontSize);
      word.style.transformOrigin = "0 100%";
      word.style.transition =
        "transform " + HANDOFF_MS + "ms cubic-bezier(0.72,0,0.16,1), filter 400ms linear";
      word.style.transform =
        "translate(" + (target.left - from.left).toFixed(1) + "px," +
        (target.bottom - from.bottom).toFixed(1) + "px) scale(" + scale.toFixed(4) + ")";
      word.style.filter = "none";
    }

    root.classList.add("is-lifting");
    if (page) page.classList.add("is-revealed");
    window.setTimeout(function () {
      if (sig) {
        sig.style.transition = "opacity 220ms linear";
        sig.style.opacity = "1";
      }
    }, HANDOFF_MS - 200);
    window.setTimeout(release, HANDOFF_MS + 260);
  }

  // ------------------------------------------------------------ run

  if (reduce) {
    apply(HOLD, 0);
    window.setTimeout(handoff, 900);
  } else {
    var t0 = 0;
    var raf = 0;

    function frame(now) {
      var elapsed = ((now - t0) / 1000) * SPEED;
      if (elapsed >= INTRO_LEN - 0.05) {
        apply(HOLD, elapsed);
        handoff();
        return;
      }
      apply(sampleIntro(Math.max(0, elapsed)), elapsed);
      raf = requestAnimationFrame(frame);
    }

    apply(sampleIntro(0), 0);
    var begin = function () {
      root.setAttribute("data-on", "1");
      t0 = performance.now();
      raf = requestAnimationFrame(frame);
    };
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(begin, begin);
    } else {
      begin();
    }

    var skip = function () {
      cancelAnimationFrame(raf);
      apply(HOLD, INTRO_LEN);
      handoff();
    };
    root.addEventListener("click", skip);
    window.addEventListener("keydown", skip, { once: true });
    window.addEventListener("wheel", skip, { once: true, passive: true });
    window.addEventListener("touchstart", skip, { once: true, passive: true });
  }
})();
