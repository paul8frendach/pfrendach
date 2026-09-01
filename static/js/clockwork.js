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

  /* ======================================================================
     Three faces, one mechanism.

     The clock is the wardrobe: every room has one, and no two rooms measure
     time the same way. Create counts frames on a rotary shutter. Build reads
     the escapement itself. Train runs a match clock. All three are driven from
     the same elapsed seconds, so they never drift apart.
     ====================================================================== */

  /* ---- CREATE: a rotary shutter. Time in frames, at 24fps. ---- */

  function shutterMarkup() {
    var uid = "sh" + Math.floor(Math.random() * 1e6);
    var GLOW = "var(--glow)";
    var marks = "";
    for (var i = 0; i < 24; i++) {
      var a = (i / 24) * Math.PI * 2 - Math.PI / 2;
      var major = i % 6 === 0;
      var inner = major ? 300 : 316;
      marks +=
        '<line data-frame="' + i + '"' +
        ' x1="' + (400 + inner * Math.cos(a)).toFixed(2) + '" y1="' + (400 + inner * Math.sin(a)).toFixed(2) + '"' +
        ' x2="' + (400 + 330 * Math.cos(a)).toFixed(2) + '" y2="' + (400 + 330 * Math.sin(a)).toFixed(2) + '"' +
        ' stroke="' + GLOW + '" stroke-opacity="' + (major ? 0.4 : 0.13) + '"' +
        ' stroke-width="' + (major ? 2 : 1) + '"/>';
    }
    // registration marks, the way a frame is punched
    var reg = "";
    [[110, 110], [690, 110], [110, 690], [690, 690]].forEach(function (pt) {
      reg +=
        '<path d="M ' + (pt[0] - 16) + ' ' + pt[1] + ' H ' + (pt[0] + 16) +
        ' M ' + pt[0] + ' ' + (pt[1] - 16) + ' V ' + (pt[1] + 16) + '"' +
        ' stroke="' + GLOW + '" stroke-opacity="0.22" stroke-width="1"/>' +
        '<circle cx="' + pt[0] + '" cy="' + pt[1] + '" r="7" stroke="' + GLOW + '" stroke-opacity="0.16"/>';
    });

    return (
      '<svg class="cw cw--shutter" viewBox="0 0 800 800" aria-hidden="true" fill="none">' +
      '<defs><radialGradient id="' + uid + '" cx="50%" cy="46%" r="52%">' +
      '<stop offset="0%" stop-color="' + GLOW + '" stop-opacity="0.10"/>' +
      '<stop offset="100%" stop-color="var(--ink)" stop-opacity="0"/>' +
      "</radialGradient></defs>" +
      '<circle cx="400" cy="400" r="330" fill="url(#' + uid + ')"/>' +
      '<circle cx="400" cy="400" r="332" stroke="' + GLOW + '" stroke-opacity="0.16"/>' +
      '<circle cx="400" cy="400" r="246" stroke="' + GLOW + '" stroke-opacity="0.09" stroke-dasharray="3 7"/>' +
      marks + reg +

      // the shutter itself: two opposed blades sweeping the gate
      '<g data-shutter>' +
      '<path d="M 400 400 L 400 108 A 292 292 0 0 1 653 546 Z" fill="' + GLOW + '" fill-opacity="0.045"/>' +
      '<path d="M 400 400 L 400 692 A 292 292 0 0 1 147 254 Z" fill="' + GLOW + '" fill-opacity="0.045"/>' +
      '<circle cx="400" cy="400" r="292" stroke="' + GLOW + '" stroke-opacity="0.1"/>' +
      "</g>" +

      // the gate: what the lens actually sees, 2.39:1
      '<rect x="214" y="322" width="372" height="156" stroke="' + GLOW + '" stroke-opacity="0.3" stroke-width="1.5"/>' +
      '<rect x="214" y="322" width="372" height="156" stroke="' + GLOW + '" stroke-opacity="0.08" stroke-width="14"/>' +
      '<circle data-shutter-pin cx="400" cy="108" r="5" fill="' + GLOW + '" fill-opacity="0.55"/>' +
      "</svg>"
    );
  }

  /* ---- TRAIN: a match clock. Time in minutes played, out of 90. ---- */

  function matchMarkup() {
    var GOLD = "var(--gold)";
    var ticks = "";
    for (var i = 0; i < 60; i++) {
      var a = (i / 60) * Math.PI * 2 - Math.PI / 2;
      var major = i % 5 === 0;
      var inner = major ? 296 : 314;
      ticks +=
        '<line x1="' + (400 + inner * Math.cos(a)).toFixed(2) + '" y1="' + (400 + inner * Math.sin(a)).toFixed(2) + '"' +
        ' x2="' + (400 + 328 * Math.cos(a)).toFixed(2) + '" y2="' + (400 + 328 * Math.sin(a)).toFixed(2) + '"' +
        ' stroke="' + GOLD + '" stroke-opacity="' + (major ? 0.42 : 0.13) + '"' +
        ' stroke-width="' + (major ? 3 : 1.2) + '"/>';
    }
    // the quarters of a match, stencilled
    var nums = "";
    [[0, "90"], [15, "15"], [30, "30"], [45, "45"], [60, "60"], [75, "75"]].forEach(function (pair) {
      var a = (pair[0] / 90) * Math.PI * 2 - Math.PI / 2;
      nums +=
        '<text x="' + (400 + 252 * Math.cos(a)).toFixed(1) + '" y="' + (400 + 252 * Math.sin(a) + 13).toFixed(1) + '"' +
        ' text-anchor="middle" fill="' + GOLD + '" fill-opacity="0.3"' +
        ' font-family="Oswald, sans-serif" font-size="34" font-weight="600">' + pair[1] + "</text>";
    });

    return (
      '<svg class="cw cw--match" viewBox="0 0 800 800" aria-hidden="true" fill="none">' +
      // the full-time arc, filling as the match runs
      '<circle cx="400" cy="400" r="332" stroke="' + GOLD + '" stroke-opacity="0.12" stroke-width="2"/>' +
      '<circle data-match-arc cx="400" cy="400" r="332" stroke="' + GOLD + '" stroke-opacity="0.5"' +
      ' stroke-width="4" stroke-linecap="round" transform="rotate(-90 400 400)"' +
      ' stroke-dasharray="2086" stroke-dashoffset="2086"/>' +
      ticks + nums +
      // centre spot and halfway line, because this is a pitch as much as a dial
      '<line x1="68" y1="400" x2="732" y2="400" stroke="' + GOLD + '" stroke-opacity="0.08" stroke-width="2"/>' +
      '<circle cx="400" cy="400" r="92" stroke="' + GOLD + '" stroke-opacity="0.1" stroke-width="2"/>' +
      '<g data-match-hand>' +
      '<line x1="400" y1="430" x2="400" y2="118" stroke="' + GOLD + '" stroke-opacity="0.75" stroke-width="3" stroke-linecap="round"/>' +
      "</g>" +
      '<circle cx="400" cy="400" r="9" fill="' + GOLD + '" fill-opacity="0.75"/>' +
      '<circle cx="400" cy="400" r="20" stroke="' + GOLD + '" stroke-opacity="0.3" stroke-width="2"/>' +
      "</svg>"
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

    // `rate` slows the whole movement down for ambient use. The escapement
    // still snaps tooth to tooth; it just does it every few seconds instead of
    // twice a second, so the page breathes rather than fidgets.
    var rate = typeof opts.rate === "number" ? opts.rate : 1;

    function loop(now) {
      if (stopped) return;
      drive((now / 1000) * rate, 0);
      raf = requestAnimationFrame(loop);
    }

    if (opts.autorun) raf = requestAnimationFrame(loop);

    return {
      svg: svg,
      drive: drive,
      stop: function () { stopped = true; cancelAnimationFrame(raf); },
    };
  }

  /**
   * Mount all three faces into one element and run them from a single clock.
   * They are never unmounted — the CSS decides which room's face is visible,
   * so changing worlds cross-fades between them and nothing ever restarts.
   * That continuity is the point: it is the same mechanism behind every door.
   */
  function mountFaces(el, opts) {
    opts = opts || {};
    var rate = typeof opts.rate === "number" ? opts.rate : 1;

    el.insertAdjacentHTML("afterbegin", shutterMarkup());
    el.insertAdjacentHTML("afterbegin", matchMarkup());
    var movement = mount(el, { rate: rate, noGlow: opts.noGlow });

    var shutter = el.querySelector("[data-shutter]");
    var shutterPin = el.querySelector("[data-shutter-pin]");
    var frames = el.querySelectorAll("[data-frame]");
    var hand = el.querySelector("[data-match-hand]");
    var arc = el.querySelector("[data-match-arc]");
    var ARC_LEN = 2086;

    var lastFrame = -1;
    var raf = 0;
    var stopped = false;

    // What each room means by "now". Same seconds in, three different readings.
    var reading = { frame: 0, tick: 0, minute: 0, second: 0 };

    function drive(elapsed) {
      movement.drive(elapsed, 0);

      /* Create: 24 frames a second, but slowed to the ambient rate so the
         shutter reads as a lazy sweep rather than a strobe. */
      var frame = Math.floor(elapsed * 24);
      shutter.setAttribute("transform", "rotate(" + (elapsed * 82).toFixed(2) + " 400 400)");
      if (shutterPin) {
        var a = (elapsed * 82 - 90) * Math.PI / 180;
        shutterPin.setAttribute("cx", (400 + 292 * Math.cos(a)).toFixed(1));
        shutterPin.setAttribute("cy", (400 + 292 * Math.sin(a)).toFixed(1));
      }
      if (frame !== lastFrame) {
        lastFrame = frame;
        var lit = frames[frame % 24];
        if (lit) {
          lit.style.strokeOpacity = "0.85";
          window.setTimeout(function () { lit.style.strokeOpacity = ""; }, 110);
        }
      }

      /* Train: a match clock. 90 minutes, running at a minute every two
         seconds, so a visitor sees it move without waiting for a half. */
      var played = (elapsed * 0.5) % 90;
      hand.setAttribute("transform", "rotate(" + ((played / 90) * 360).toFixed(2) + " 400 400)");
      arc.setAttribute("stroke-dashoffset", (ARC_LEN * (1 - played / 90)).toFixed(1));

      reading.frame = frame % 24;
      reading.tick = Math.floor(elapsed * BALANCE_HZ * 2);
      reading.minute = Math.floor(played);
      reading.second = Math.floor((played % 1) * 60);
      return reading;
    }

    function loop(now) {
      if (stopped) return;
      var r = drive((now / 1000) * rate);
      if (opts.onTick) opts.onTick(r);
      raf = requestAnimationFrame(loop);
    }
    if (opts.autorun) raf = requestAnimationFrame(loop);

    return {
      drive: drive,
      reading: reading,
      stop: function () { stopped = true; cancelAnimationFrame(raf); movement.stop(); },
    };
  }

  window.PF = window.PF || {};
  window.PF.clockwork = {
    mount: mount,
    mountFaces: mountFaces,
    sliderCrank: sliderCrank,
    markup: svgMarkup,
    BALANCE_HZ: BALANCE_HZ,
  };
})();
