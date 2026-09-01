/* The LAB intake form, made comfortable.
 *
 * Two jobs, both progressive: without this file the form still submits and
 * still reaches the coach, it is just longer than it needs to be.
 *
 *  1. Age. The LAB accepts exactly one of age range, birth year or date of
 *     birth, chosen by `age_type`. All three are rendered so a JS-off visitor
 *     can use any of them; here we show only the one selected.
 * "Add another player" is deliberately NOT here: it is a real submit button
 * the view handles, so it works with JavaScript off and the new block is built
 * from the coach's own configuration rather than cloned from a stale copy.
 */
(function () {
  "use strict";

  var form = document.querySelector("[data-lab-intake]");
  if (!form) return;

  function wireAge(select) {
    var block = select.closest("[data-athlete-block]") || form;
    var byKind = {
      range: block.querySelector("[data-age='range']"),
      year: block.querySelector("[data-age='year']"),
      birthday: block.querySelector("[data-age='birthday']")
    };

    function apply() {
      Object.keys(byKind).forEach(function (kind) {
        var el = byKind[kind];
        if (!el) return;
        var show = kind === select.value;
        el.hidden = !show;
        // A hidden-but-present field would still post an empty value, which
        // is harmless, but clearing it keeps the payload honest about which
        // representation the visitor actually chose.
        if (!show) {
          var input = el.querySelector("input, select");
          if (input) input.value = "";
        }
      });
    }

    select.addEventListener("change", apply);
    apply();
  }

  form.querySelectorAll("[data-age-type]").forEach(wireAge);

})();
