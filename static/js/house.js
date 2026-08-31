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
    var pending = false;
    var lastCond = -1;
    var crest = chrome.querySelector(".chrome__crest");
    var CONDENSE_OVER = 90;   // px of scroll to go from full crest to slim rail

    /* One continuous value, not a class toggle. Every dimension in the chrome
       is expressed in terms of it, so the bar tightens with the scroll instead
       of snapping between two layouts. */
    function syncChrome() {
      pending = false;
      var y = window.scrollY || document.documentElement.scrollTop;
      var cond = Math.min(1, Math.max(0, y / CONDENSE_OVER));
      // Quantise to 3dp: enough for a smooth ramp, few enough style writes
      // that we are not thrashing the compositor on every scroll frame.
      cond = Math.round(cond * 1000) / 1000;
      if (cond === lastCond) return;
      lastCond = cond;
      document.documentElement.style.setProperty("--cond", String(cond));
      chrome.classList.toggle("is-condensed", cond > 0.6);
      document.dispatchEvent(new CustomEvent("pf:cond"));

      /* How far through the page you are, in the room's own colour. The one
         piece of chrome that answers "where am I" rather than "where can I go". */
      var doc = document.documentElement;
      var travel = doc.scrollHeight - window.innerHeight;
      doc.style.setProperty(
        "--scrollp", travel > 40 ? Math.min(1, y / travel).toFixed(4) : "0"
      );
    }

    /* The crest's natural height decides how far it has to collapse, and the
       expanded chrome height decides how tall a room's opening screen can be.
       Both are measured, never hard-coded, so they cannot drift. */
    function measure() {
      var held = document.documentElement.style.getPropertyValue("--cond");
      document.documentElement.style.setProperty("--cond", "0");
      if (crest) {
        crest.style.height = "auto";
        document.documentElement.style.setProperty(
          "--crest-h", crest.offsetHeight + "px"
        );
        crest.style.height = "";
      }
      // Rounded up: a fractional spacer height leaves a hairline of content
      // showing above the bar on some device pixel ratios.
      document.documentElement.style.setProperty(
        "--chrome-tall", Math.ceil(chrome.getBoundingClientRect().height) + "px"
      );
      document.documentElement.style.setProperty("--cond", held || "0");
    }
    measure();
    window.addEventListener("resize", function () {
      measure();
      syncChrome();
    }, { passive: true });
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(measure, measure);
    }

    window.addEventListener("scroll", function () {
      if (pending) return;
      pending = true;
      window.requestAnimationFrame(syncChrome);
    }, { passive: true });
    syncChrome();


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


    /* Tab widths shrink continuously as the chrome tightens, so the marker has
       to track that ramp rather than wait for a transition that never fires. */
    document.addEventListener("pf:cond", function () { rest(true); });

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

  /* ---------------------------------------------------------- presence
     The page should feel like it knows someone is there — the way a painted
     portrait follows you across a room — without ever chasing the cursor in a
     way you would notice as an effect.

     Two variables, published once per frame:
       --px / --py   pointer position across the viewport, 0 to 1
       --pdx / --pdy the same as a signed offset from centre, -1 to 1

     Everything reactive reads those. No element gets its own listener, and a
     device without a pointer simply leaves them at centre. */

  if (!reduced && window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
    var px = 0.5, py = 0.5;
    var tx = 0.5, ty = 0.5;
    var presenceRaf = 0;

    function presenceFrame() {
      // Ease toward the pointer rather than snapping to it: the lag is what
      // separates "the room is aware of you" from "the page is twitching".
      px += (tx - px) * 0.075;
      py += (ty - py) * 0.075;
      var root = document.documentElement.style;
      root.setProperty("--px", px.toFixed(4));
      root.setProperty("--py", py.toFixed(4));
      root.setProperty("--pdx", ((px - 0.5) * 2).toFixed(4));
      root.setProperty("--pdy", ((py - 0.5) * 2).toFixed(4));

      if (Math.abs(tx - px) > 0.0005 || Math.abs(ty - py) > 0.0005) {
        presenceRaf = requestAnimationFrame(presenceFrame);
      } else {
        presenceRaf = 0;
      }
    }

    window.addEventListener("pointermove", function (event) {
      tx = event.clientX / window.innerWidth;
      ty = event.clientY / window.innerHeight;
      if (!presenceRaf) presenceRaf = requestAnimationFrame(presenceFrame);
    }, { passive: true });

    /* A spotlight that follows the cursor across whatever it is over. One
       delegated listener for the whole page, positions written as element
       variables so the CSS decides what, if anything, to do with them. */
    document.addEventListener("pointermove", function (event) {
      var lit = event.target.closest ? event.target.closest("[data-lit], .tile, .card, .door, .rack__tab") : null;
      if (!lit) return;
      var box = lit.getBoundingClientRect();
      lit.style.setProperty("--mx", (((event.clientX - box.left) / box.width) * 100).toFixed(1) + "%");
      lit.style.setProperty("--my", (((event.clientY - box.top) / box.height) * 100).toFixed(1) + "%");
    }, { passive: true });
  }

  /* A room change sweeps the new world's light across the ground. It is the
     only motion on the site that happens without the visitor causing it —
     and they did cause it, by opening the door. */
  document.addEventListener("pf:navigated", function () {
    var ground = document.querySelector("[data-ground]");
    if (!ground || reduced) return;
    ground.classList.remove("is-sweeping");
    void ground.offsetWidth;          // restart the animation
    ground.classList.add("is-sweeping");
  });

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
