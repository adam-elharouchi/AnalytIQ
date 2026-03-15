/**
 * offline-detector.js — connection banner (Task 37)
 *
 * Shows a persistent red banner at the bottom of the page when the browser
 * goes offline.  Hides automatically when the connection is restored.
 * No dependencies — plain JS, works before any framework loads.
 */
(function () {
    'use strict';

    var banner = null;

    function getBanner() {
        if (banner) return banner;
        banner = document.createElement('div');
        banner.id = 'offline-banner';
        banner.setAttribute('role', 'alert');
        banner.setAttribute('aria-live', 'assertive');
        banner.style.cssText = [
            'position:fixed',
            'bottom:0',
            'left:0',
            'right:0',
            'z-index:9998',
            'background:#dc2626',
            'color:#fff',
            'padding:0.75rem 1.5rem',
            'text-align:center',
            'font-family:system-ui,-apple-system,sans-serif',
            'font-size:0.875rem',
            'font-weight:500',
            'box-shadow:0 -2px 8px rgba(0,0,0,0.2)',
            'display:none',
        ].join(';');
        banner.textContent = '\u26A0 You appear to be offline. Some features may not work until your connection is restored.';
        document.body.appendChild(banner);
        return banner;
    }

    function showBanner() {
        if (document.body) {
            getBanner().style.display = 'block';
        } else {
            document.addEventListener('DOMContentLoaded', function () {
                getBanner().style.display = 'block';
            });
        }
    }

    function hideBanner() {
        if (banner) banner.style.display = 'none';
    }

    window.addEventListener('online', hideBanner);
    window.addEventListener('offline', showBanner);

    // Check state on initial load
    if (!navigator.onLine) {
        showBanner();
    }
}());
