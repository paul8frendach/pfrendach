/* =========================================================================
   Clockwork — the house movement.

   A direct port of the studio's logo-flash component to vanilla JS. The
   choreography, gear ratios and damped-spring seating are his, not re-derived:
   balance wheel 1 Hz, 15-tooth escape, 16/10 train, slider-crank r=26 rod=70.

   Two jobs:
     1. PF.clockwork.mount(el, opts)  — draw and run a movement in any element.
     2. The curtain (sting.js) uses it under the wordmark.
   ========================================================================= */

(function () {
  "use strict";

  var BALANCE_HZ = 1;
  var ESCAPE_TEETH = 15;
  var GEAR_A_TEETH = 16;
  var GEAR_B_TEETH = 10;
  var MODULE = 7;
  var CRANK_R = 26;
  var ROD_L = 70;
  var CRANK_CX = 108;
  var CRANK_CY = 108;
  var GEAR_A = { x: 128, y: 702, n: GEAR_A_TEETH };
  var GEAR_B = { x: 128 + (MODULE * (GEAR_A_TEETH + GEAR_B_TEETH)) / 2, y: 702, n: GEAR_B_TEETH };

  function pitchRadius(teeth) { return (MODULE * teeth) / 2; }

  function gearPath(cx, cy, teeth) {
    var rPitch = pitchRadius(teeth);
    var rOut = rPitch * 1.14;
    var rIn = rPitch * 0.82;
    var step = (Math.PI * 2) / teeth;
    var half = step * 0.28;
    var out = [];
    function p(r, ang) {
      return (cx + r * Math.cos(ang)).toFixed(1) + " " + (cy + r * Math.sin(ang)).toFixed(1);
    }
    for (var i = 0; i < teeth; i++) {
      var a = i * step - Math.PI / 2;
      out.push(
        (i === 0 ? "M" : "L") + " " + p(rIn, a - half) +
        " L " + p(rOut, a - half) + " L " + p(rOut, a + half) + " L " + p(rIn, a + half) +
        " A " + rIn + " " + rIn + " 0 0 1 " + p(rIn, a + step - half)
      );
    }
    out.push("Z");
    return out.join(" ");
  }

  function ratchetPath(cx, cy, teeth, rOut, rIn) {
    var step = (Math.PI * 2) / teeth;
    var out = [];
    function p(r, ang) {
      return (cx + r * Math.cos(ang)).toFixed(1) + " " + (cy + r * Math.sin(ang)).toFixed(1);
    }
    for (var i = 0; i < teeth; i++) {
      var a = i * step - Math.PI / 2;
      out.push((i === 0 ? "M" : "L") + " " + p(rIn, a) + " L " + p(rOut, a + step * 0.12) + " L " + p(rIn, a + step));
    }
    out.push("Z");
    return out.join(" ");
  }

  function sliderCrank(theta) {
    var pinX = CRANK_CX + CRANK_R * Math.cos(theta);
    var pinY = CRANK_CY + CRANK_R * Math.sin(theta);
    var s = CRANK_R * Math.sin(theta);
    var pistonX = CRANK_CX + CRANK_R * Math.cos(theta) + Math.sqrt(Math.max(4, ROD_L * ROD_L - s * s));
    var x0 = CRANK_CX + CRANK_R + ROD_L;
    var x1 = CRANK_CX - CRANK_R + ROD_L;
    var travel = (x0 - pistonX) / (x0 - x1);
    return { pinX: pinX, pinY: pinY, pistonX: pistonX, pistonY: CRANK_CY, travel: Math.min(1, Math.max(0, travel)) };
  }

  function easeImpulse(frac, tau) { return 1 - Math.exp(-frac / (tau || 0.09)); }

  var GOLD = "var(--gold)";

  function svgMarkup(opts) {
    var ticks = "";
    for (var i = 0; i < 60; i++) {
      var a = (i / 60) * Math.PI * 2 - Math.PI / 2;
      var inner = i % 5 === 0 ? 348 : 358;
      var major = i % 5 === 0;
      ticks +=
        '<line data-tick="' + i + '"' +
        ' x1="' + (400 + inner * Math.cos(a)).toFixed(2) + '" y1="' + (400 + inner * Math.sin(a)).toFixed(2) + '"' +
        ' x2="' + (400 + 366 * Math.cos(a)).toFixed(2) + '" y2="' + (400 + 366 * Math.sin(a)).toFixed(2) + '"' +
        ' stroke="' + GOLD + '" stroke-opacity="' + (major ? 0.28 : 0.1) + '"' +
        ' stroke-width="' + (major ? 1.3 : 0.6) + '"/>';
    }

    var rA = pitchRadius(GEAR_A.n);
    var rB = pitchRadius(GEAR_B.n);
    var uid = "cw" + Math.floor(Math.random() * 1e6);

    return (
      '<svg class="cw" viewBox="0 0 800 800" aria-hidden="true" fill="none">' +
      '<defs><radialGradient id="' + uid + '" cx="50%" cy="42%" r="48%">' +
      '<stop offset="0%" stop-color="' + GOLD + '" stop-opacity="0.12"/>' +
      '<stop offset="70%" stop-color="' + GOLD + '" stop-opacity="0.02"/>' +
      '<stop offset="100%" stop-color="var(--ink)" stop-opacity="0"/>' +
      "</radialGradient></defs>" +
      (opts && opts.noGlow ? "" : '<circle cx="400" cy="400" r="340" fill="url(#' + uid + ')"/>') +
      '<circle cx="400" cy="400" r="368" stroke="' + GOLD + '" stroke-opacity="0.12"/>' +
      ticks +

      '<g class="cw-train">' +
      '<circle cx="' + GEAR_A.x + '" cy="' + GEAR_A.y + '" r="' + rA + '" stroke="' + GOLD + '" stroke-opacity="0.12" stroke-dasharray="2 3"/>' +
      '<circle cx="' + GEAR_B.x + '" cy="' + GEAR_B.y + '" r="' + rB + '" stroke="' + GOLD + '" stroke-opacity="0.12" stroke-dasharray="2 3"/>' +
      '<g data-gear-a>' +
      '<path d="' + gearPath(GEAR_A.x, GEAR_A.y, GEAR_A.n) + '" stroke="' + GOLD + '" stroke-opacity="0.42" stroke-width="1.05"/>' +
      '<circle cx="' + GEAR_A.x + '" cy="' + GEAR_A.y + '" r="7" stroke="' + GOLD + '" stroke-opacity="0.5"/>' +
      '<circle cx="' + GEAR_A.x + '" cy="' + GEAR_A.y + '" r="2.2" fill="' + GOLD + '" fill-opacity="0.7"/></g>' +
      '<g data-gear-b>' +
      '<path d="' + gearPath(GEAR_B.x, GEAR_B.y, GEAR_B.n) + '" stroke="' + GOLD + '" stroke-opacity="0.38" stroke-width="1.05"/>' +
      '<circle cx="' + GEAR_B.x + '" cy="' + GEAR_B.y + '" r="5.5" stroke="' + GOLD + '" stroke-opacity="0.5"/></g>' +
      "</g>" +

      '<g class="cw-escape">' +
      '<g data-escape>' +
      '<path d="' + ratchetPath(686, 168, ESCAPE_TEETH, 28, 16) + '" stroke="' + GOLD + '" stroke-opacity="0.4" stroke-width="1"/>' +
      '<circle cx="686" cy="168" r="4" stroke="' + GOLD + '" stroke-opacity="0.5"/></g>' +
      '<g data-pallet><path d="M 668 118 L 704 118 L 698 128 L 674 128 Z" stroke="' + GOLD + '" stroke-opacity="0.45" stroke-width="1"/></g>' +
      '<g data-balance>' +
      '<circle cx="686" cy="108" r="32" stroke="' + GOLD + '" stroke-opacity="0.32"/>' +
      '<circle cx="686" cy="108" r="18" stroke="' + GOLD + '" stroke-opacity="0.2"/>' +
      '<line x1="686" y1="78" x2="686" y2="138" stroke="' + GOLD + '" stroke-opacity="0.4"/>' +
      '<circle cx="686" cy="108" r="3" fill="' + GOLD + '" fill-opacity="0.75"/></g>' +
      "</g>" +

      '<g class="cw-crank">' +
      '<line x1="' + (CRANK_CX + 20) + '" y1="' + CRANK_CY + '" x2="' + (CRANK_CX + CRANK_R + ROD_L + 16) + '" y2="' + CRANK_CY + '" stroke="' + GOLD + '" stroke-opacity="0.16" stroke-width="6" stroke-linecap="round"/>' +
      '<circle cx="' + CRANK_CX + '" cy="' + CRANK_CY + '" r="34" stroke="' + GOLD + '" stroke-opacity="0.2"/>' +
      '<circle cx="' + CRANK_CX + '" cy="' + CRANK_CY + '" r="22" stroke="' + GOLD + '" stroke-opacity="0.16"/>' +
      '<line data-rod x1="' + CRANK_CX + '" y1="' + CRANK_CY + '" x2="' + (CRANK_CX + CRANK_R + ROD_L) + '" y2="' + CRANK_CY + '" stroke="' + GOLD + '" stroke-opacity="0.7" stroke-width="1.6" stroke-linecap="round"/>' +
      '<circle data-pin cx="' + CRANK_CX + '" cy="' + (CRANK_CY - CRANK_R) + '" r="4" fill="' + GOLD + '" fill-opacity="0.8"/>' +
      '<rect data-piston x="' + (CRANK_CX + CRANK_R + ROD_L - 7) + '" y="' + (CRANK_CY - 7) + '" width="14" height="14" rx="2" stroke="' + GOLD + '" stroke-opacity="0.7"/>' +
      '<circle cx="' + CRANK_CX + '" cy="' + CRANK_CY + '" r="3.4" fill="' + GOLD + '" fill-opacity="0.85"/>' +
      "</g></svg>"
    );
  }

  /**
   * Draw a movement into `el` and run it. Returns a handle with
   * `.drive(elapsed, crankTheta)` for a caller that owns the clock, or it
   * free-runs when `opts.autorun` is set. `.stop()` releases the frame loop.
   */
  function mount(el, opts) {
    opts = opts || {};
    el.insertAdjacentHTML("afterbegin", svgMarkup(opts));
    var svg = el.querySelector(".cw");
    var parts = {
      gearA: svg.querySelector("[data-gear-a]"),
      gearB: svg.querySelector("[data-gear-b]"),
      escape: svg.querySelector("[data-escape]"),
      balance: svg.querySelector("[data-balance]"),
      pallet: svg.querySelector("[data-pallet]"),
      rod: svg.querySelector("[data-rod]"),
      pin: svg.querySelector("[data-pin]"),
      piston: svg.querySelector("[data-piston]"),
    };
    var lastTick = -1;
    var raf = 0;
    var stopped = false;

    function drive(elapsed, crank) {
      var sc = sliderCrank(crank || 0);
      var w = Math.PI * 2 * BALANCE_HZ;
      var balance = 17 * Math.sin(w * elapsed);
      var vel = Math.cos(w * elapsed);
      var pallet = 11 * Math.sign(vel || 1);
      var ticks = elapsed * BALANCE_HZ * 2;
      var n = Math.floor(ticks);
      var snapped = n + easeImpulse(ticks - n, 0.14);
      var escapeDeg = snapped * (360 / ESCAPE_TEETH);
      var gearADeg = -escapeDeg * (ESCAPE_TEETH / GEAR_A_TEETH);
      var gearBDeg = -gearADeg * (GEAR_A_TEETH / GEAR_B_TEETH) + 180 / GEAR_B_TEETH;

      parts.gearA.setAttribute("transform", "rotate(" + gearADeg + " " + GEAR_A.x + " " + GEAR_A.y + ")");
      parts.gearB.setAttribute("transform", "rotate(" + gearBDeg + " " + GEAR_B.x + " " + GEAR_B.y + ")");
      parts.escape.setAttribute("transform", "rotate(" + escapeDeg + " 686 168)");
      parts.balance.setAttribute("transform", "rotate(" + balance + " 686 108)");
      parts.pallet.setAttribute("transform", "rotate(" + pallet + " 686 118)");

      parts.rod.setAttribute("x1", sc.pinX.toFixed(2));
      parts.rod.setAttribute("y1", sc.pinY.toFixed(2));
      parts.rod.setAttribute("x2", sc.pistonX.toFixed(2));
      parts.rod.setAttribute("y2", sc.pistonY.toFixed(2));
      parts.pin.setAttribute("cx", sc.pinX.toFixed(2));
      parts.pin.setAttribute("cy", sc.pinY.toFixed(2));
      parts.piston.setAttribute("x", (sc.pistonX - 7).toFixed(2));

      // Pulse the chapter-ring tick that just passed. This is the heartbeat
      // the rest of the site borrows its rhythm from.
      if (n !== lastTick) {
        lastTick = n;
        var ring = svg.querySelector('[data-tick="' + (n % 60) + '"]');
        if (ring) {
          ring.style.strokeOpacity = "0.9";
          window.setTimeout(function () { ring.style.strokeOpacity = ""; }, 90);
        }
      }
      return sc;
    }

    function loop(now) {
      if (stopped) return;
      drive(now / 1000, 0);
      raf = requestAnimationFrame(loop);
    }

    if (opts.autorun) raf = requestAnimationFrame(loop);

    return {
      svg: svg,
      drive: drive,
      stop: function () { stopped = true; cancelAnimationFrame(raf); },
    };
  }

  window.PF = window.PF || {};
  window.PF.clockwork = {
    mount: mount,
    sliderCrank: sliderCrank,
    markup: svgMarkup,
    BALANCE_HZ: BALANCE_HZ,
  };
})();
