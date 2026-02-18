/**
 * ui-states.js — consistent loading / empty / error / content states (Task 24)
 *
 * Usage:
 *   uiStates.showLoading(el, 3);                          // 3 skeleton cards
 *   uiStates.showEmpty(el, 'No classes yet', 'Create one', 'Create your first class', '#');
 *   uiStates.showError(el, 'Failed to load', () => loadData());
 *   uiStates.showContent(el, '<div>...</div>');
 */
(function () {
    'use strict';

    let _stylesInjected = false;

    function _injectStyles() {
        if (_stylesInjected) return;
        _stylesInjected = true;
        const style = document.createElement('style');
        style.textContent = [
            '.ui-skeleton { background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);',
            '  background-size: 200% 100%; animation: ui-shimmer 1.5s infinite; border-radius: 8px; }',
            '@keyframes ui-shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }',
            '.ui-skeleton-card { padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 12px; }',
            '.ui-skeleton-line { height: 14px; margin-bottom: 8px; border-radius: 4px; }',
            '.ui-skeleton-line.wide  { width: 75%; }',
            '.ui-skeleton-line.narrow { width: 40%; }',
            '.ui-empty-state { text-align: center; padding: 48px 24px; color: #64748b; }',
            '.ui-empty-state h3 { font-size: 1.1rem; font-weight: 600; color: #374151; margin: 0 0 8px; }',
            '.ui-empty-state p { margin: 0 0 20px; font-size: 0.9rem; }',
            '.ui-error-state { text-align: center; padding: 32px 24px; color: #ef4444; }',
            '.ui-error-state p { margin: 0 0 16px; font-size: 0.9rem; }',
        ].join('\n');
        document.head.appendChild(style);
    }

    function _skeletonCard() {
        return '<div class="ui-skeleton-card">' +
               '<div class="ui-skeleton ui-skeleton-line wide"></div>' +
               '<div class="ui-skeleton ui-skeleton-line narrow"></div>' +
               '<div class="ui-skeleton ui-skeleton-line" style="width:60%"></div>' +
               '</div>';
    }

    window.uiStates = {
        showLoading: function (container, count) {
            _injectStyles();
            count = count || 3;
            let html = '';
            for (let i = 0; i < count; i++) html += _skeletonCard();
            container.innerHTML = html;
        },

        showEmpty: function (container, title, subtitle, ctaText, ctaHref) {
            _injectStyles();
            const cta = ctaText
                ? '<a href="' + (ctaHref || '#') + '" class="btn btn-primary" style="display:inline-block;padding:10px 20px;border-radius:6px;text-decoration:none;font-size:0.9rem;">' + ctaText + '</a>'
                : '';
            container.innerHTML =
                '<div class="ui-empty-state">' +
                '<h3>' + (title || 'Nothing here yet') + '</h3>' +
                (subtitle ? '<p>' + subtitle + '</p>' : '') +
                cta +
                '</div>';
        },

        showError: function (container, message, onRetry) {
            _injectStyles();
            const id = 'ui-retry-' + Math.random().toString(36).slice(2);
            container.innerHTML =
                '<div class="ui-error-state">' +
                '<p>' + (message || 'Something went wrong.') + '</p>' +
                (onRetry ? '<button id="' + id + '" class="btn btn-secondary" style="padding:8px 16px;border-radius:6px;cursor:pointer;">Try again</button>' : '') +
                '</div>';
            if (onRetry) {
                const btn = document.getElementById(id);
                if (btn) btn.addEventListener('click', onRetry);
            }
        },

        showContent: function (container, html) {
            container.innerHTML = html;
        },
    };
}());
