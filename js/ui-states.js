/**
 * ui-states.js — consistent loading / empty / error / content states (Task 24)
 *
 * Usage:
 *   uiStates.showLoading(el, 3);                          // 3 skeleton cards
 *   uiStates.showEmpty(el, 'No classes yet', 'Create one', 'Create your first class', '#');
 *   uiStates.showError(el, 'Failed to load', () => loadData());
 *   uiStates.showContent(el, '<div>...</div>');
 *   uiStates.showConfirmModal('Delete this?', () => doDelete());
 */
(function () {
    'use strict';

    let _stylesInjected = false;
    let _modalStylesInjected = false;

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

    function _injectModalStyles() {
        if (_modalStylesInjected) return;
        _modalStylesInjected = true;
        const style = document.createElement('style');
        style.textContent = [
            '.ui-confirm-backdrop { position: fixed; inset: 0; z-index: 9000; background: rgba(0,0,0,0.45); display: flex; align-items: center; justify-content: center; animation: ui-fade-in 0.15s ease; }',
            '@keyframes ui-fade-in { from { opacity: 0; } to { opacity: 1; } }',
            '.ui-confirm-card { background: #fff; border-radius: var(--radius-lg, 12px); padding: 24px 36px; box-shadow: 0 20px 60px rgba(0,0,0,0.2); max-width: 420px; width: 90%; text-align: center; animation: ui-slide-up 0.18s ease; }',
            '@keyframes ui-slide-up { from { transform: translateY(16px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }',
            '.ui-confirm-message { font-size: 0.95rem; color: var(--color-dark, #1e293b); line-height: 1.55; margin: 0 0 24px; }',
            '.ui-confirm-actions { display: flex; gap: 12px; justify-content: center; }',
            '.ui-confirm-btn { padding: 9px 22px; border: none; border-radius: 6px; font-size: 0.9rem; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }',
            '.ui-confirm-btn:hover { opacity: 0.85; }',
            '.ui-confirm-btn-danger { background: var(--color-error, #ef4444); color: #fff; }',
            '.ui-confirm-btn-cancel { background: #e5e7eb; color: var(--color-dark, #1e293b); }',
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

        showConfirmModal: function (message, onConfirm, onCancel) {
            _injectModalStyles();
            var msgId = 'ui-confirm-msg-' + Math.random().toString(36).slice(2);

            var backdrop = document.createElement('div');
            backdrop.className = 'ui-confirm-backdrop';
            backdrop.setAttribute('aria-hidden', 'true');

            var card = document.createElement('div');
            card.className = 'ui-confirm-card';
            card.setAttribute('role', 'dialog');
            card.setAttribute('aria-modal', 'true');
            card.setAttribute('aria-labelledby', msgId);

            var msg = document.createElement('p');
            msg.className = 'ui-confirm-message';
            msg.id = msgId;
            msg.textContent = message || 'Are you sure?';

            var actions = document.createElement('div');
            actions.className = 'ui-confirm-actions';

            var cancelBtn = document.createElement('button');
            cancelBtn.className = 'ui-confirm-btn ui-confirm-btn-cancel';
            cancelBtn.textContent = 'Cancel';

            var confirmBtn = document.createElement('button');
            confirmBtn.className = 'ui-confirm-btn ui-confirm-btn-danger';
            confirmBtn.textContent = 'Confirm';

            actions.appendChild(cancelBtn);
            actions.appendChild(confirmBtn);
            card.appendChild(msg);
            card.appendChild(actions);
            backdrop.appendChild(card);
            document.body.appendChild(backdrop);

            // Move focus into modal on open
            cancelBtn.focus();

            function _close() {
                if (backdrop.parentNode) backdrop.parentNode.removeChild(backdrop);
                document.removeEventListener('keydown', _onKeydown);
            }
            function _onKeydown(e) {
                if (e.key === 'Escape') { _close(); if (typeof onCancel === 'function') onCancel(); return; }
                // Focus trap: keep Tab cycling between cancel and confirm
                if (e.key === 'Tab') {
                    e.preventDefault();
                    if (document.activeElement === cancelBtn) {
                        confirmBtn.focus();
                    } else {
                        cancelBtn.focus();
                    }
                }
            }

            confirmBtn.addEventListener('click', function () {
                _close();
                if (typeof onConfirm === 'function') onConfirm();
            });
            cancelBtn.addEventListener('click', function () {
                _close();
                if (typeof onCancel === 'function') onCancel();
            });
            backdrop.addEventListener('click', function (e) {
                if (e.target === backdrop) { _close(); if (typeof onCancel === 'function') onCancel(); }
            });
            document.addEventListener('keydown', _onKeydown);

            return backdrop;
        },
    };
}());
