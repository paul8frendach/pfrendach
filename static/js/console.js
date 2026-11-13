/* =========================================================================
   The portfolio console.

   A horizontal run of work that advances on its own. Only the card in view
   plays — a rail of simultaneously decoding videos is what makes a page like
   this stutter, and one playing clip is what makes it read as a showreel
   rather than a wall.

   It yields immediately and permanently to the visitor: touch it, hover it,
   focus it, or drag it, and it stops advancing. It is a showreel, not a
   carousel that fights you.
   ========================================================================= */

(function () {
  "use strict";

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function mountConsoles() {
    Array.prototype.forEach.call(document.querySelectorAll("[data-console]"), function (root) {
      if (root.dataset.consoleReady === "1") return;
      root.dataset.consoleReady = "1";

      var track = root.querySelector("[data-console-track]");
      var items = Array.prototype.slice.call(root.querySelectorAll("[data-reel-item]"));
      var dotsWrap = root.querySelector("[data-console-dots]");
      var prev = root.querySelector("[data-console-prev]");
      var next = root.querySelector("[data-console-next]");
      if (!track || items.length === 0) return;

      var index = 0;
      var timer = 0;
      var surrendered = false;   // the visitor took over; never auto-advance again
      var HOLD = 6200;

      // ---- dots -------------------------------------------------------

      var dots = items.map(function (_, i) {
        var dot = document.createElement("button");
        dot.type = "button";
        dot.className = "console__dot";
        dot.setAttribute("aria-label", "Go to item " + (i + 1));
        dot.addEventListener("click", function () {
          surrender();
          go(i);
        });
        if (dotsWrap) dotsWrap.appendChild(dot);
        return dot;
      });

      // ---- playback ---------------------------------------------------

      function setActive(i) {
        index = i;
        items.forEach(function (item, n) {
          var on = n === i;
          item.classList.toggle("is-active", on);
          if (dots[n]) dots[n].classList.toggle("is-on", on);

          var video = item.querySelector("[data-reel-video]");
          if (!video) return;
          if (on) {
            // preload="none" until it is wanted, so opening the page costs one
            // poster per card and nothing else.
            if (video.preload !== "auto") video.preload = "auto";
            var playing = video.play();
            if (playing && playing.catch) playing.catch(function () { /* autoplay blocked */ });
          } else if (!video.paused) {
            video.pause();
            video.currentTime = 0;
          }
        });
        if (prev) prev.disabled = i === 0;
        if (next) next.disabled = i === items.length - 1;
      }

      function go(i, smooth) {
        var wrapped = (i + items.length) % items.length;
        var item = items[wrapped];
        track.scrollTo({
          left: item.offsetLeft - track.offsetLeft,
          behavior: smooth === false || reduced ? "auto" : "smooth",
        });
        setActive(wrapped);
      }

      // ---- auto-advance -----------------------------------------------

      function stop() { window.clearTimeout(timer); timer = 0; }

      function schedule() {
        stop();
        if (surrendered || reduced || items.length < 2) return;
        if (document.visibilityState === "hidden") return;
        timer = window.setTimeout(function () {
          go(index + 1);
          schedule();
        }, HOLD);
      }

      function surrender() {
        surrendered = true;
        stop();
        root.classList.add("is-manual");
      }

      // Any real intent from the visitor ends the automation for good.
      ["pointerdown", "wheel", "touchstart", "keydown"].forEach(function (evt) {
        root.addEventListener(evt, surrender, { passive: true, once: true });
      });
      root.addEventListener("mouseenter", stop);
      root.addEventListener("mouseleave", schedule);
      root.addEventListener("focusin", surrender);
      document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "hidden") stop();
        else schedule();
      });

      if (prev) prev.addEventListener("click", function () { surrender(); go(index - 1); });
      if (next) next.addEventListener("click", function () { surrender(); go(index + 1); });

      // ---- follow manual scrolling -------------------------------------

      if ("IntersectionObserver" in window) {
        var watcher = new IntersectionObserver(function (entries) {
          entries.forEach(function (entry) {
            if (!entry.isIntersecting || entry.intersectionRatio < 0.6) return;
            var i = items.indexOf(entry.target);
            if (i !== -1 && i !== index) setActive(i);
          });
        }, { root: track, threshold: [0.6] });
        items.forEach(function (item) { watcher.observe(item); });
      }

      // Only start once the console is actually on screen — a reel playing to
      // nobody above the fold is wasted bandwidth and battery.
      if ("IntersectionObserver" in window) {
        var starter = new IntersectionObserver(function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) { setActive(index); schedule(); }
            else stop();
          });
        }, { threshold: 0.25 });
        starter.observe(root);
      } else {
        setActive(0);
        schedule();
      }

      setActive(0);
    });
  }

  window.PF = window.PF || {};
  window.PF.mountConsoles = mountConsoles;
  mountConsoles();
})();
