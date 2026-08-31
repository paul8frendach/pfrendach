/* House motion. Small on purpose — the page must work with this file missing. */
(function () {
  "use strict";

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var risers = document.querySelectorAll(".rise");

  if (reduced || !("IntersectionObserver" in window)) {
    risers.forEach(function (el) { el.classList.add("is-in"); });
    return;
  }

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      // Stagger siblings so a grid seats row by row rather than all at once.
      var delay = Number(entry.target.dataset.riseDelay || 0);
      setTimeout(function () { entry.target.classList.add("is-in"); }, delay);
      observer.unobserve(entry.target);
    });
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });

  risers.forEach(function (el, i) {
    if (!el.dataset.riseDelay) el.dataset.riseDelay = String((i % 6) * 70);
    observer.observe(el);
  });
})();
