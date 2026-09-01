/* =========================================================================
   Core bridge.

   Core is a local-first content engine — its whole premise is that a
   business's footage never leaves their machine. There is therefore no server
   this page could ask about it. What it can do is ask the visitor's own
   browser whether Core is running on *their* machine, and show the library if
   it is.

   So the panel is live for the person sitting at the machine and honestly
   inert for everyone else. It never blocks, never retries in a loop, and a
   failure is the expected case rather than an error.
   ========================================================================= */

(function () {
  "use strict";

  function mountCore() {
    var panel = document.querySelector("[data-core-panel]");
    if (!panel || panel.dataset.coreReady === "1") return;
    panel.dataset.coreReady = "1";

    var base = panel.dataset.coreUrl;
    var state = panel.querySelector("[data-core-state]");
    var stats = panel.querySelector("[data-core-stats]");
    var note = panel.querySelector("[data-core-note]");
    var open = panel.querySelector("[data-core-open]");

    // A machine without Core should cost nothing: one request, short fuse.
    var controller = new AbortController();
    var timer = window.setTimeout(function () { controller.abort(); }, 1200);

    fetch(base + "/api/status/", { signal: controller.signal, mode: "cors" })
      .then(function (res) {
        if (!res.ok) throw new Error("core said " + res.status);
        return res.json();
      })
      .then(function (data) {
        window.clearTimeout(timer);
        panel.classList.add("is-live");
        state.textContent = "Core is running on this machine";

        var map = {
          "[data-core-assets]": data.assets,
          "[data-core-moments]": data.moments,
          "[data-core-workspaces]": data.workspaces,
          "[data-core-videos]": data.video_projects,
          "[data-core-graphics]": data.graphic_projects,
        };
        Object.keys(map).forEach(function (sel) {
          var el = panel.querySelector(sel);
          if (el) el.textContent = String(map[sel]);
        });

        stats.removeAttribute("hidden");
        open.removeAttribute("hidden");
        note.textContent =
          "These are the real counts from the library on this machine. " +
          "Nothing here was uploaded to see them.";
      })
      .catch(function () {
        window.clearTimeout(timer);
        // Not an error. Core simply is not running here, which is the norm.
        panel.classList.add("is-idle");
        state.textContent = "Core is not running on this machine";
      });
  }

  window.PF = window.PF || {};
  window.PF.mountCore = mountCore;
  mountCore();
})();
