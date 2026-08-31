/* =========================================================================
   Seamless navigation.

   Moving between rooms must not reload the page: the movement in the
   background keeps running, the chrome stays put, and the world's colour
   morphs rather than cuts. Only <main> is swapped.

   Progressive: with JS off, or on a cross-origin/modified click, the browser
   does an ordinary navigation and everything still works.
   ========================================================================= */

(function () {
  "use strict";

  var main = document.querySelector("[data-main]");
  if (!main || !window.history || !window.fetch) return;

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var SWAP_MS = reduce ? 0 : 220;
  var inFlight = null;
  var cache = Object.create(null);
  var SELF_CONTAINED = ["/flash/"];

  function sameOrigin(url) {
    return url.origin === window.location.origin;
  }

  function isPageLink(a, event) {
    if (!a || a.target === "_blank" || a.hasAttribute("download")) return false;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return false;
    if (event.button !== 0) return false;
    var url;
    try { url = new URL(a.href, window.location.href); } catch (e) { return false; }
    if (!sameOrigin(url)) return false;
    if (url.pathname.indexOf("/admin") === 0) return false;
    if (url.pathname.indexOf("/api/") !== -1) return false;
    // Pages that load their own scripts cannot be swapped in — only main is
    // replaced, so a page-specific <script> would never run.
    if (SELF_CONTAINED.indexOf(url.pathname) !== -1) return false;
    if (a.getAttribute("href").charAt(0) === "#") return false;
    // Same page, different hash: let the browser scroll.
    if (url.pathname === window.location.pathname &&
        url.search === window.location.search && url.hash) return false;
    return true;
  }

  function parse(html) {
    var doc = new DOMParser().parseFromString(html, "text/html");
    var incoming = doc.querySelector("[data-main]");
    if (!incoming) return null;
    return {
      html: incoming.innerHTML,
      title: doc.title,
      world: doc.documentElement.getAttribute("data-world") || "house",
      urlName: incoming.getAttribute("data-url-name") || "",
    };
  }

  function fetchPage(url) {
    if (cache[url]) return Promise.resolve(cache[url]);
    return fetch(url, { headers: { "X-Requested-With": "route" }, credentials: "same-origin" })
      .then(function (res) {
        if (!res.ok) throw new Error("bad status " + res.status);
        return res.text();
      })
      .then(function (html) {
        var page = parse(html);
        if (!page) throw new Error("no main");
        // Forms carry CSRF tokens tied to this session; caching a page with a
        // form would serve a stale token, so only cache pages without one.
        if (html.indexOf("csrfmiddlewaretoken") === -1) cache[url] = page;
        return page;
      });
  }

  function markChrome(world, urlName) {
    document.documentElement.setAttribute("data-world", world);

    Array.prototype.forEach.call(document.querySelectorAll(".tab"), function (tab) {
      var isHere = tab.classList.contains("tab--" + world);
      if (isHere) tab.setAttribute("aria-current", "page");
      else tab.removeAttribute("aria-current");
    });
    Array.prototype.forEach.call(document.querySelectorAll(".subnav a"), function (a) {
      var here = a.getAttribute("href");
      if (here && here.replace(/\/$/, "") === window.location.pathname.replace(/\/$/, "")) {
        a.setAttribute("aria-current", "page");
      } else {
        a.removeAttribute("aria-current");
      }
    });
  }

  function apply(page, url, opts) {
    opts = opts || {};
    main.innerHTML = page.html;
    document.title = page.title;
    markChrome(page.world, page.urlName);

    if (!opts.pop) {
      window.history.pushState({ pf: true }, "", url);
    }

    var hash = window.location.hash;
    if (hash) {
      var anchor = document.querySelector(hash);
      if (anchor) anchor.scrollIntoView({ behavior: reduce ? "auto" : "smooth" });
    } else if (!opts.pop) {
      window.scrollTo({ top: 0, behavior: "auto" });
    }

    main.classList.remove("is-leaving");
    if (window.PF && window.PF.mountPage) window.PF.mountPage();
    document.dispatchEvent(new CustomEvent("pf:navigated", { detail: { world: page.world } }));
  }

  function go(url, opts) {
    opts = opts || {};
    if (inFlight === url) return;
    inFlight = url;
    document.documentElement.classList.add("is-routing");
    if (SWAP_MS) main.classList.add("is-leaving");

    var settled = Promise.all([
      fetchPage(url),
      SWAP_MS ? new Promise(function (r) { window.setTimeout(r, SWAP_MS); }) : null,
    ]);

    settled.then(function (results) {
      inFlight = null;
      document.documentElement.classList.remove("is-routing");
      apply(results[0], url, opts);
    }).catch(function () {
      // Anything unexpected: hand it back to the browser rather than trap the
      // visitor on a half-swapped page.
      window.location.href = url;
    });
  }

  document.addEventListener("click", function (event) {
    var a = event.target.closest ? event.target.closest("a") : null;
    if (!isPageLink(a, event)) return;
    event.preventDefault();
    var url = new URL(a.href, window.location.href);
    if (url.href === window.location.href) return;
    go(url.pathname + url.search + url.hash);
  });

  window.addEventListener("popstate", function () {
    go(window.location.pathname + window.location.search, { pop: true });
  });

  // Warm the cache on intent. By the time the click lands the page is usually
  // already in memory, which is what makes a room change feel instant.
  var warmed = Object.create(null);
  function warm(event) {
    var a = event.target.closest ? event.target.closest("a") : null;
    if (!a) return;
    var url;
    try { url = new URL(a.href, window.location.href); } catch (e) { return; }
    if (!sameOrigin(url) || url.pathname.indexOf("/admin") === 0) return;
    var key = url.pathname + url.search;
    if (warmed[key]) return;
    warmed[key] = true;
    fetchPage(key).catch(function () { /* nothing to do */ });
  }
  document.addEventListener("mouseover", warm, { passive: true });
  document.addEventListener("touchstart", warm, { passive: true });

  /* ---------------------------------------------------------- swipe
     On a touch screen the three rooms sit side by side: swipe left or right
     to move between them, the same order as the tabs. */

  var ORDER = ["create", "build", "train"];
  var HREF = {};
  Array.prototype.forEach.call(document.querySelectorAll(".tab"), function (tab) {
    ORDER.forEach(function (slug) {
      if (tab.classList.contains("tab--" + slug)) HREF[slug] = tab.getAttribute("href");
    });
  });

  var sx = 0, sy = 0, tracking = false;
  document.addEventListener("touchstart", function (e) {
    if (e.touches.length !== 1) { tracking = false; return; }
    sx = e.touches[0].clientX;
    sy = e.touches[0].clientY;
    tracking = true;
  }, { passive: true });

  document.addEventListener("touchend", function (e) {
    if (!tracking) return;
    tracking = false;
    var t = e.changedTouches[0];
    var dx = t.clientX - sx;
    var dy = t.clientY - sy;
    // Horizontal, decisive, and not a scroll.
    if (Math.abs(dx) < 70 || Math.abs(dx) < Math.abs(dy) * 2) return;
    var world = document.documentElement.getAttribute("data-world");
    var i = ORDER.indexOf(world);
    if (i === -1) i = dx < 0 ? -1 : ORDER.length;
    var next = ORDER[i + (dx < 0 ? 1 : -1)];
    if (next && HREF[next]) go(HREF[next]);
  }, { passive: true });
})();
