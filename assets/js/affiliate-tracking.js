// Fires a GA4 "amazon_click" event when an active Affiliate CTA is clicked.
// Only loaded when GA4 is configured (see _includes/ga4.html), so this file assumes
// `gtag` may or may not exist by the time a click happens and guards accordingly.
//
// Role split vs. GA4 Enhanced Measurement's built-in "click" (outbound) event:
// if Enhanced Measurement is on for the GA4 property (its default), GA4's own base
// script already auto-fires a generic click/outbound event for ANY external-domain
// link on the site, with no code here involved. That event is a generic engagement
// signal (link_url/link_domain, no business context). This file's "amazon_click" is
// a separate, deliberately narrower event: only for elements the CTA component marks
// data-affiliate-active="true", carrying the product/position/article identifiers
// needed for affiliate-specific analysis. Seeing both events fire for one click is
// expected, not a duplicate bug; Enhanced Measurement is a GA4-property dashboard
// setting, not something this repo configures.
//
// No personal data is sent: only the product/position/article identifiers already
// present as data-affiliate-* attributes on the CTA markup.
//
// This never calls preventDefault() and never throws past its own try/catch, so the
// affiliate link itself always navigates normally even if gtag is blocked, missing,
// or errors (ad blockers, network issues, etc).
(function () {
  document.addEventListener("click", function (event) {
    try {
      var target = event.target.closest('[data-affiliate-active="true"]');
      if (!target) return;
      if (typeof gtag !== "function") return;

      gtag("event", "amazon_click", {
        product: target.getAttribute("data-affiliate-product") || "",
        position: target.getAttribute("data-affiliate-position") || "",
        article: target.getAttribute("data-affiliate-article") || ""
      });
    } catch (err) {
      // Tracking must never interfere with the affiliate link itself.
    }
  });
})();
