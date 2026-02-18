/**
 * apiClient — unified fetch wrapper (Tasks 14, 25, 27)
 *
 * All methods return a structured result: { ok, data, error }
 *   ok    — true if HTTP 2xx
 *   data  — parsed JSON response body (or null)
 *   error — error message string (or null on success)
 *
 * Global 401 interceptor: redirects to auth.html?reason=session_expired
 * and clears auth tokens so the user gets a clear "session expired" message.
 *
 * Usage:
 *   const { ok, data, error } = await apiClient.get('/classes');
 *   const { ok, data, error } = await apiClient.post('/classes', { name: 'CS101' });
 */
(function () {
    'use strict';

    async function _request(method, path, body, opts) {
        opts = opts || {};
        const headers = {};

        const token = localStorage.getItem('authToken');
        if (token) headers['Authorization'] = 'Bearer ' + token;

        // Don't set Content-Type for FormData — browser sets it with boundary
        if (!(body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
        }

        // Allow callers to add extra headers
        Object.assign(headers, opts.headers || {});

        const fetchOpts = {
            method: method,
            headers: headers,
        };

        if (body !== null && body !== undefined) {
            fetchOpts.body = (body instanceof FormData) ? body : JSON.stringify(body);
        }

        try {
            const res = await fetch((window.API_BASE_URL || '/api') + path, fetchOpts);

            // 401 interceptor — session expired
            if (res.status === 401) {
                localStorage.removeItem('authToken');
                localStorage.removeItem('currentUser');
                const redirect = encodeURIComponent(window.location.href);
                window.location.href = 'auth.html?reason=session_expired&redirect=' + redirect;
                return { ok: false, data: null, error: 'Session expired' };
            }

            let data = null;
            const contentType = res.headers.get('content-type') || '';
            if (contentType.includes('application/json')) {
                try { data = await res.json(); } catch (_) {}
            }

            const error = res.ok ? null : ((data && data.error) || ('HTTP ' + res.status));
            return { ok: res.ok, data: data, error: error };

        } catch (err) {
            return { ok: false, data: null, error: err.message || 'Network error' };
        }
    }

    window.apiClient = {
        get:  function (path, opts)       { return _request('GET',    path, null, opts); },
        post: function (path, body, opts) { return _request('POST',   path, body, opts); },
        put:  function (path, body, opts) { return _request('PUT',    path, body, opts); },
        del:  function (path, opts)       { return _request('DELETE', path, null, opts); },
        /** Raw multipart POST — body must be a FormData instance */
        upload: function (path, formData, opts) { return _request('POST', path, formData, opts); },
    };
}());
