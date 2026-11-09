(function () {
  "use strict";

  /* ---------- Typography: no lonely last word, no line starting with a separator ---------- */

  // Glue the last two words of each text block with a non-breaking space so a
  // single word never ends up alone on the last line, at any viewport width.
  var WIDOW_SELECTOR = "p, li, h1, h2, h3, h4, .pf-metric, .role-line, .role-official, .skill-list, .pub-venue, .lang-level";

  // Whitespace-only text between block-level siblings is source formatting, not a gap between words.
  function isBlockGap(node) {
    if (/\S/.test(node.nodeValue)) return false;
    var sibs = [node.previousSibling, node.nextSibling];
    for (var s = 0; s < sibs.length; s++) {
      var sib = sibs[s];
      if (sib && sib.nodeType === 1 && window.getComputedStyle(sib).display.indexOf("inline") !== 0) return true;
    }
    return false;
  }

  function preventWidow(el) {
    var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    var nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    var seenWord = false;
    for (var i = nodes.length - 1; i >= 0; i--) {
      var text = nodes[i].nodeValue;
      if (seenWord && isBlockGap(nodes[i])) return; // never glue across a block boundary
      for (var j = text.length - 1; j >= 0; j--) {
        var c = text[j];
        if (c === "\u00A0") {
          if (seenWord) return; // already glued
        } else if (/\s/.test(c)) {
          if (!seenWord) continue; // trailing whitespace
          var k = j;
          while (k > 0 && /\s/.test(text[k - 1]) && text[k - 1] !== "\u00A0") k--;
          nodes[i].nodeValue = text.slice(0, k) + "\u00A0" + text.slice(j + 1);
          return;
        } else {
          seenWord = true;
        }
      }
    }
  }

  // Keep separators and punctuation attached to the preceding word, so a line never
  // starts with an em dash, a middle dot, an arrow, ":" (French spacing) or a closing quote.
  function glueSeparators(el) {
    var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      var node = walker.currentNode;
      var fixed = node.nodeValue
        .replace(/ (?=[—·:;?!»→])/g, "\u00A0")
        .replace(/« /g, "«\u00A0")
        .replace(/([^\s\u2060])(?=— )/g, "$1\u2060");
      if (fixed !== node.nodeValue) node.nodeValue = fixed;
    }
  }

  var blocks = document.querySelectorAll(WIDOW_SELECTOR);
  Array.prototype.forEach.call(blocks, glueSeparators);
  Array.prototype.forEach.call(blocks, preventWidow);

  /* ---------- Mobile navigation ---------- */

  var nav = document.querySelector(".nav");
  var toggle = document.querySelector(".nav-toggle");
  var links = document.getElementById("navLinks");
  if (!nav || !toggle || !links) return;

  function setMenu(open) {
    links.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", String(open));
  }

  toggle.addEventListener("click", function () {
    var open = !links.classList.contains("is-open");
    setMenu(open);
    (open ? links.querySelector("a") : toggle).focus(); // the next Tab walks the menu
  });
  links.addEventListener("click", function (e) {
    if (e.target.closest("a")) setMenu(false);
  });
  document.addEventListener("click", function (e) {
    if (!e.target.closest(".nav")) setMenu(false);
  });
  document.addEventListener("focusin", function (e) {
    if (links.classList.contains("is-open") && !e.target.closest(".nav")) setMenu(false);
  });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape" || !links.classList.contains("is-open")) return;
    var inMenu = links.contains(document.activeElement);
    setMenu(false);
    if (inMenu) toggle.focus();
  });

  // Leave the mobile layout (CSS breakpoint 70em follows the user's default font size) -> close the menu.
  var desktop = window.matchMedia("(min-width: 70em)");
  var closeOnDesktop = function (e) { if (e.matches) setMenu(false); };
  if (desktop.addEventListener) desktop.addEventListener("change", closeOnDesktop);
  else desktop.addListener(closeOnDesktop);
})();
