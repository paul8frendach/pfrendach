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

  /* ---------------------------------------------------------- the ground
     One movement, mounted once, behind every page. It is never re-mounted on
     navigation — that persistence is what makes a room change feel like a
     door rather than a page load. Runs slow: one beat every few seconds. */

  var ground = document.querySelector("[data-ground]");
  if (ground && !reduced && window.PF && window.PF.clockwork && !ground.dataset.mounted) {
    ground.dataset.mounted = "1";
    window.PF.clockwork.mount(ground, { autorun: true, rate: 0.16, noGlow: true });
  }

  /* ---------------------------------------------------------- reveals
     Re-run after every swap, since the router replaces main's contents. */

  var observer = null;

  /* The Build room's rack: pick an app, see its features. Tabs rather than a
     scroll, so the whole room stays on one screen. */
  function mountRacks() {
    Array.prototype.forEach.call(document.querySelectorAll("[data-rack]"), function (rack) {
      var tabs = rack.querySelectorAll(".rack__tab");
      var panels = rack.querySelectorAll(".rack__panel");

      function show(index) {
        Array.prototype.forEach.call(tabs, function (tab, i) {
          tab.setAttribute("aria-selected", i === index ? "true" : "false");
        });
        Array.prototype.forEach.call(panels, function (panel, i) {
          if (i === index) panel.removeAttribute("hidden");
          else panel.setAttribute("hidden", "");
        });
      }

      Array.prototype.forEach.call(tabs, function (tab, i) {
        tab.addEventListener("click", function () { show(i); });
        tab.addEventListener("keydown", function (event) {
          var next = null;
          if (event.key === "ArrowDown" || event.key === "ArrowRight") next = i + 1;
          if (event.key === "ArrowUp" || event.key === "ArrowLeft") next = i - 1;
          if (next === null) return;
          event.preventDefault();
          next = (next + tabs.length) % tabs.length;
          show(next);
          tabs[next].focus();
        });
      });
    });
  }

  function mountPage() {
    mountRacks();

    var risers = document.querySelectorAll(".rise:not(.is-in)");

    if (reduced || !("IntersectionObserver" in window)) {
      Array.prototype.forEach.call(risers, function (el) { el.classList.add("is-in"); });
      return;
    }

    if (!observer) {
      observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          // Stagger siblings so a row seats tooth by tooth, not all at once.
          var delay = Number(entry.target.dataset.riseDelay || 0);
          window.setTimeout(function () { entry.target.classList.add("is-in"); }, delay);
          observer.unobserve(entry.target);
        });
      }, { rootMargin: "0px 0px -6% 0px", threshold: 0.06 });
    }

    Array.prototype.forEach.call(risers, function (el, i) {
      if (!el.dataset.riseDelay) el.dataset.riseDelay = String((i % 5) * 60);
      observer.observe(el);
    });
  }

  window.PF = window.PF || {};
  window.PF.mountPage = mountPage;
  mountPage();
})();
