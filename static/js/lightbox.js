/* Oasis Media Visions — one global lightbox for photos and video.
   Delegated on the document, so it works on every page regardless of the
   router swapping content. Keeps the viewer ON the page (no navigating to a
   raw image), watermarks the enlarged view, and cycles the page's items. */
(function () {
  "use strict";
  var box, img, vid, cap, items = [], index = -1;

  function build() {
    box = document.createElement("div");
    box.className = "lb";
    box.setAttribute("hidden", "");
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.innerHTML =
      '<button class="lb__x" type="button" aria-label="Close">×</button>' +
      '<button class="lb__nav lb__prev" type="button" aria-label="Previous">‹</button>' +
      '<button class="lb__nav lb__next" type="button" aria-label="Next">›</button>' +
      '<figure class="lb__stage">' +
        '<img class="lb__img" alt="">' +
        '<video class="lb__vid" controls playsinline hidden></video>' +
        '<span class="lb__mark" aria-hidden="true">Oasis Media Visions</span>' +
        '<figcaption class="lb__cap"></figcaption>' +
      '</figure>';
    document.body.appendChild(box);
    img = box.querySelector(".lb__img");
    vid = box.querySelector(".lb__vid");
    cap = box.querySelector(".lb__cap");
    box.querySelector(".lb__x").addEventListener("click", close);
    box.querySelector(".lb__prev").addEventListener("click", function (e) { e.stopPropagation(); step(-1); });
    box.querySelector(".lb__next").addEventListener("click", function (e) { e.stopPropagation(); step(1); });
    box.addEventListener("click", function (e) {
      if (e.target === box || e.target.classList.contains("lb__stage") || e.target.tagName === "FIGURE") close();
    });
  }

  function render() {
    var el = items[index];
    if (!el) return;
    var videoSrc = el.getAttribute("data-video");
    var caption = el.getAttribute("data-caption") || el.getAttribute("aria-label") || "";
    if (videoSrc) {
      img.hidden = true;
      vid.hidden = false;
      vid.src = videoSrc;
      vid.play().catch(function () {});
    } else {
      vid.pause();
      vid.hidden = true;
      vid.removeAttribute("src");
      img.hidden = false;
      img.src = el.getAttribute("href") || el.getAttribute("data-src") || "";
    }
    cap.textContent = caption;
    box.classList.toggle("lb--multi", items.length > 1);
    box.classList.toggle("lb--video", !!videoSrc);
  }

  function open(trigger) {
    if (!box) build();
    items = Array.prototype.slice.call(document.querySelectorAll("[data-lightbox]"));
    index = items.indexOf(trigger);
    if (index < 0) return;
    render();
    box.hidden = false;
    requestAnimationFrame(function () { box.classList.add("is-in"); });
    document.documentElement.classList.add("lb-open");
  }
  function close() {
    if (!box || box.hidden) return;
    box.classList.remove("is-in");
    vid.pause();
    setTimeout(function () { box.hidden = true; img.src = ""; vid.removeAttribute("src"); }, 320);
    document.documentElement.classList.remove("lb-open");
  }
  function step(d) {
    if (index < 0) return;
    index = (index + d + items.length) % items.length;
    render();
  }

  // Capture phase, so this runs BEFORE router.js's own document click handler.
  // router.js treats every same-origin link as a page to swap in — including a
  // link straight to a /static/*.jpg — and, finding no [data-main] in an image,
  // falls back to location.href and navigates the whole tab to the raw file.
  // Stopping the event here keeps the viewer on the page every time.
  document.addEventListener("click", function (e) {
    var t = e.target.closest ? e.target.closest("[data-lightbox]") : null;
    if (!t) return;
    if (e.target.closest("[data-like-form], button, .review-heart")) return;
    e.preventDefault();
    e.stopPropagation();
    open(t);
  }, true);
  document.addEventListener("keydown", function (e) {
    // Open from a focused non-link trigger (e.g. a reel tile) via Enter/Space.
    if (box && !box.hidden) {
      if (e.key === "Escape") close();
      else if (e.key === "ArrowLeft") step(-1);
      else if (e.key === "ArrowRight") step(1);
      return;
    }
    if (e.key !== "Enter" && e.key !== " ") return;
    var el = document.activeElement;
    if (!el || !el.matches || !el.matches("[data-lightbox]") || el.tagName === "A") return;
    e.preventDefault();
    open(el);
  });
})();
