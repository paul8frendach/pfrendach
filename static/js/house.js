/* House behaviour. Small on purpose — every page must work with this missing. */
(function () {
  "use strict";

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------------------------------------------------------- chrome
     Full stacked nameplate at the top of a page, slim centred bar once you
     move. Hysteresis (8px on, 2px off) so a trackpad twitch cannot flutter it. */

  var chrome = document.querySelector("[data-chrome]");
  if (chrome) {
    var condensed = false;
    var pending = false;

    function syncChrome() {
      pending = false;
      var y = window.scrollY || document.documentElement.scrollTop;
      if (!condensed && y > 8) {
        condensed = true;
        chrome.classList.add("is-condensed");
      } else if (condensed && y <= 2) {
        condensed = false;
        chrome.classList.remove("is-condensed");
      }
    }

    // Publish the expanded chrome height so the hero can size itself to
    // exactly one screen without hard-coding a number that will drift.
    function measure() {
      if (chrome.classList.contains("is-condensed")) return;
      document.documentElement.style.setProperty(
        "--chrome-tall", chrome.offsetHeight + "px"
      );
    }
    measure();
    window.addEventListener("resize", measure, { passive: true });

    window.addEventListener("scroll", function () {
      if (pending) return;
      pending = true;
      window.requestAnimationFrame(syncChrome);
    }, { passive: true });
    syncChrome();
  }

  /* ---------------------------------------------------------- dials
     A live movement behind a hero. Same escapement as the curtain, running
     free. It is the reason a page feels awake rather than printed. */

  if (!reduced && window.PF && window.PF.clockwork) {
    Array.prototype.forEach.call(document.querySelectorAll("[data-dial]"), function (el) {
      window.PF.clockwork.mount(el, { autorun: true });
    });
  }

  /* ---------------------------------------------------------- reveals */

  var risers = document.querySelectorAll(".rise");

  if (reduced || !("IntersectionObserver" in window)) {
    Array.prototype.forEach.call(risers, function (el) { el.classList.add("is-in"); });
    return;
  }

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      // Stagger siblings so a row seats tooth by tooth, not all at once.
      var delay = Number(entry.target.dataset.riseDelay || 0);
      window.setTimeout(function () { entry.target.classList.add("is-in"); }, delay);
      observer.unobserve(entry.target);
    });
  }, { rootMargin: "0px 0px -6% 0px", threshold: 0.06 });

  Array.prototype.forEach.call(risers, function (el, i) {
    if (!el.dataset.riseDelay) el.dataset.riseDelay = String((i % 5) * 60);
    observer.observe(el);
  });
})();
