/*
 * UGC attribution for waitlist sign-ups.
 *
 * - A creator's link (crm…/r/<code>/<page>) lands here with ?ref=<code>.
 *   The ref is remembered for 30 days in this browser.
 * - Waitlist forms get an optional "code" field (a creator's code = first month free).
 * - Every POST to /api/waitlist gets `ref` and `code` added, so the server can
 *   pass the sign-up on to the sales CRM with the right creator.
 */
(function () {
  var KEY = "ubz-ref";
  var DAYS = 30;
  var CODE_RE = /^[a-z0-9]{2,20}$/i;

  function store(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function load(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }

  // 1. Remember ?ref= from the URL.
  try {
    var params = new URLSearchParams(location.search);
    var ref = (params.get("ref") || "").trim();
    if (CODE_RE.test(ref)) store(KEY, JSON.stringify({ ref: ref.toLowerCase(), at: Date.now() }));
  } catch (e) {}

  function currentRef() {
    try {
      var v = JSON.parse(load(KEY) || "null");
      if (v && v.ref && Date.now() - v.at < DAYS * 86400000) return v.ref;
    } catch (e) {}
    return null;
  }

  function sl() {
    var l = (document.documentElement.lang || "").toLowerCase();
    return l.indexOf("en") !== 0;
  }

  // 2. Add an optional code field to waitlist forms (main form and pop-up).
  function addField(form) {
    if (!form || form.querySelector("[name=ubz_code]") || !form.querySelector("input[type=email], input[name=email]")) return;
    var btn = form.querySelector("button[type=submit], button:not([type])");
    if (!btn) return;
    var isPopup = form.classList.contains("ubp-f");
    var wrap = document.createElement("div");
    wrap.className = isPopup ? "ubz-code" : "field ubz-code";
    wrap.style.cssText = isPopup ? "margin:0 0 12px 0;text-align:left;" : "";
    var id = "ubz-code-" + Math.random().toString(36).slice(2, 7);
    var label = sl() ? "Koda ustvarjalca" : "Creator code";
    var opt = sl() ? "(neobvezno · 1. mesec brezplačno)" : "(optional · 1st month free)";
    wrap.innerHTML =
      '<label for="' + id + '"' + (isPopup ? ' style="display:block;font-size:13px;margin-bottom:4px;opacity:.8"' : "") + ">" +
      label + ' <span class="opt">' + opt + "</span></label>" +
      '<input id="' + id + '" name="ubz_code" type="text" autocomplete="off" autocapitalize="characters" maxlength="20" placeholder="' +
      (sl() ? "npr. ANA" : "e.g. ANA") + '"' +
      (isPopup ? ' style="width:100%;box-sizing:border-box;padding:10px 12px;border:1px solid rgba(0,0,0,.18);border-radius:10px;font:inherit"' : "") +
      ">";
    var anchor = btn;
    // In the main form the button may sit inside a wrapper; insert before that wrapper.
    while (anchor.parentElement && anchor.parentElement !== form && !isPopup) anchor = anchor.parentElement;
    anchor.parentElement.insertBefore(wrap, anchor);
  }

  function scan(root) {
    (root.querySelectorAll ? root.querySelectorAll("form") : []).forEach(addField);
  }

  function typedCode() {
    var inputs = document.querySelectorAll("input[name=ubz_code]");
    for (var i = 0; i < inputs.length; i++) {
      var v = (inputs[i].value || "").replace(/[^a-z0-9]/gi, "");
      if (CODE_RE.test(v)) return v.toUpperCase();
    }
    return null;
  }

  // 3. Add ref + code to waitlist requests.
  var origFetch = window.fetch;
  if (origFetch) {
    window.fetch = function (input, init) {
      try {
        var url = typeof input === "string" ? input : (input && input.url) || "";
        if (/\/api\/waitlist(\?|$)/.test(url) && init && typeof init.body === "string") {
          var data = JSON.parse(init.body);
          if (data && typeof data === "object") {
            var r = currentRef();
            var c = typedCode();
            if (r && !data.ref) data.ref = r;
            if (c && !data.code) data.code = c;
            init = Object.assign({}, init, { body: JSON.stringify(data) });
          }
        }
      } catch (e) {}
      return origFetch.call(this, input, init);
    };
  }

  function start() {
    scan(document);
    if (window.MutationObserver) {
      new MutationObserver(function (muts) {
        muts.forEach(function (m) {
          m.addedNodes.forEach(function (n) {
            if (n.nodeType === 1) {
              if (n.tagName === "FORM") addField(n);
              else scan(n);
            }
          });
        });
      }).observe(document.body, { childList: true, subtree: true });
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
