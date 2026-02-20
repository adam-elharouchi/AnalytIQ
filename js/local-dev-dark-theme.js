/* ════════════════════════════════════════════════════════════════
   LOCAL DEV ONLY — Neon Hover Glow
   Adds neon blue box-shadow on hover for all interactive elements.
   DO NOT deploy this file. Remove this <script> tag and this file
   before any production build / git push.
   ════════════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    // Respect reduced-motion preference
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) return;

    const NEON_SHADOW = [
        '0 0 0 1px rgba(37,105,244,0.9)',
        '0 0 12px 3px rgba(37,105,244,0.55)',
        '0 0 32px 8px rgba(37,105,244,0.22)',
    ].join(', ');

    const NEON_SHADOW_SUBTLE = [
        '0 0 0 1px rgba(37,105,244,0.6)',
        '0 0 8px 2px rgba(37,105,244,0.35)',
        '0 0 20px 4px rgba(37,105,244,0.15)',
    ].join(', ');

    const TRANSITION = 'box-shadow 0.22s ease, border-color 0.22s ease, transform 0.22s ease';

    // Selectors that get the FULL neon glow
    const CARD_SELECTORS = [
        '.page-nav-card',
        '.dashboard-card',
        '.module-card',
        '.practice-card',
        '.resource-card',
        '.class-card',
        '.stat-card',
        '.info-card',
        '.chapter-card',
        '.exercise-card',
        '.leaderboard-card',
        '.upload-card',
        '.section-card',
        '.contact-card',
        '.resource-item',
        '.chapter-item',
        '.exercise-item',
        '.class-item',
    ].join(', ');

    // Selectors that get the SUBTLE glow (buttons, tabs)
    const BTN_SELECTORS = [
        '.btn',
        '.tab-button',
        '.login-tab',
        '.sub-tab-button',
        '.user-menu-toggle',
        '.user-menu-item',
        '.modal-close',
    ].join(', ');

    function applyNeon(el, shadow, lift) {
        const origShadow = el.dataset.origShadow ?? el.style.boxShadow;
        const origBorder = el.dataset.origBorder ?? el.style.borderColor;
        const origTrans = el.dataset.origTrans ?? el.style.transition;
        const origTransform = el.dataset.origTransform ?? el.style.transform;

        // Store originals once
        if (!el.dataset.neonReady) {
            el.dataset.origShadow = origShadow;
            el.dataset.origBorder = origBorder;
            el.dataset.origTrans = origTrans;
            el.dataset.origTransform = origTransform;
            el.dataset.neonReady = '1';
        }

        el.style.transition = TRANSITION;
        el.style.boxShadow = shadow;
        el.style.borderColor = 'rgba(37,105,244,0.85)';
        if (lift) el.style.transform = 'translateY(-3px)';
    }

    function removeNeon(el) {
        el.style.boxShadow = el.dataset.origShadow || '';
        el.style.borderColor = el.dataset.origBorder || '';
        el.style.transform = el.dataset.origTransform || '';
        // keep transition for the smooth out
    }

    function attachListeners(root) {
        root.querySelectorAll(CARD_SELECTORS).forEach(el => {
            if (el.dataset.neonAttached) return;
            el.dataset.neonAttached = '1';
            el.addEventListener('mouseenter', () => applyNeon(el, NEON_SHADOW, true));
            el.addEventListener('mouseleave', () => removeNeon(el));
        });

        root.querySelectorAll(BTN_SELECTORS).forEach(el => {
            if (el.dataset.neonAttached) return;
            el.dataset.neonAttached = '1';
            el.addEventListener('mouseenter', () => applyNeon(el, NEON_SHADOW_SUBTLE, false));
            el.addEventListener('mouseleave', () => removeNeon(el));
        });
    }

    // Initial attach after DOM ready
    function init() {
        attachListeners(document);

        // Re-attach for dynamically injected content (navigation cards, etc.)
        const observer = new MutationObserver(mutations => {
            mutations.forEach(m => {
                m.addedNodes.forEach(node => {
                    if (node.nodeType === 1) {
                        attachListeners(node);
                        // Also check the node itself
                        const test = [CARD_SELECTORS, BTN_SELECTORS].join(', ');
                        if (node.matches && node.matches(test)) {
                            attachListeners(node.parentElement || document);
                        }
                    }
                });
            });
        });

        observer.observe(document.body, { childList: true, subtree: true });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
