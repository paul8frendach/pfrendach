/* House behaviour. Small on purpose — every page must work with this missing. */
(function () {
  "use strict";

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // The first-paint settle is a one-off. Drop the gate as soon as it has run,
  // so its fill can never outrank the router's own swap transition.
  window.setTimeout(function () {
    document.documentElement.classList.remove("is-fresh");
  }, 700);

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

    // The condensation resizes the tab rail; tell the marker to re-seat after.
    chrome.addEventListener("transitionend", function (event) {
      if (event.target === chrome.querySelector(".chrome__inner")) {
        document.dispatchEvent(new CustomEvent("pf:chrome-settled"));
      }
    });
  }

  /* ---------------------------------------------------------- tab marker
     One lit jewel that slides between the three worlds. It rests under the
     active room and follows the pointer, then returns. This is the whole
     reason the bar reads as a mechanism instead of three links. */

  var tabsBar = document.querySelector("[data-tabs]");
  if (tabsBar) {
    var marker = tabsBar.querySelector("[data-tab-marker]");
    var tabEls = tabsBar.querySelectorAll(".tab");
    var settled = false;

    var ACCENT = {
      create: "var(--glow)",
      build: "var(--steel)",
      train: "var(--gold)",
    };

    function worldOf(tab) {
      if (tab.classList.contains("tab--create")) return "create";
      if (tab.classList.contains("tab--build")) return "build";
      if (tab.classList.contains("tab--train")) return "train";
      return null;
    }

    function moveTo(tab, instant) {
      if (!tab) {
        marker.classList.remove("is-on");
        return;
      }
      // The rail is the offset parent, so tab.offsetLeft is already relative.
      if (instant) marker.classList.add("is-instant");
      marker.style.setProperty("--marker-accent", ACCENT[worldOf(tab)] || "var(--gold)");
      marker.style.width = tab.offsetWidth + "px";
      marker.style.transform = "translateX(" + tab.offsetLeft + "px)";
      marker.classList.add("is-on");
      if (instant) {
        // Let the instant frame land before re-enabling the slide.
        window.requestAnimationFrame(function () {
          window.requestAnimationFrame(function () {
            marker.classList.remove("is-instant");
          });
        });
      }
    }

    function activeTab() {
      return tabsBar.querySelector('.tab[aria-current="page"]');
    }

    function rest(instant) {
      moveTo(activeTab(), instant);
    }

    Array.prototype.forEach.call(tabEls, function (tab) {
      tab.addEventListener("mouseenter", function () { moveTo(tab, false); });
      tab.addEventListener("focus", function () { moveTo(tab, false); });
    });
    tabsBar.addEventListener("mouseleave", function () { rest(false); });
    tabsBar.addEventListener("focusout", function () { rest(false); });

    window.addEventListener("resize", function () { rest(true); }, { passive: true });
    document.addEventListener("pf:navigated", function () { rest(false); });
    document.addEventListener("pf:chrome-settled", function () { rest(false); });

    // The rail resizes as the chrome condenses; re-seat once that has settled.
    tabsBar.addEventListener("transitionend", function (event) {
      if (event.propertyName === "padding-left" || event.propertyName === "font-size") rest(false);
    });

    function seat() {
      if (settled) return;
      settled = true;
      rest(true);
    }
    if (document.fonts && document.fonts.ready) {
      // Type metrics decide the tab widths, so wait for the real font — but
      // never wait forever on a slow or blocked font host.
      Promise.race([
        document.fonts.ready,
        new Promise(function (r) { window.setTimeout(r, 1200); }),
      ]).then(seat, seat);
    } else {
      seat();
    }
    rest(true);
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

  /* Panels: the house answer to a long page. A block of content that would
     otherwise be five screens of scrolling becomes one screen you step
     through. Used by the Build rack and the Train doctrine. */
  function mountPanels() {
    Array.prototype.forEach.call(document.querySelectorAll("[data-panels]"), function (rack) {
      if (rack.dataset.panelsReady === "1") return;
      rack.dataset.panelsReady = "1";
      var tabs = rack.querySelectorAll("[data-panel-tab]");
      var panels = rack.querySelectorAll("[data-panel]");
      if (!tabs.length || tabs.length !== panels.length) return;

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
    mountPanels();

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
