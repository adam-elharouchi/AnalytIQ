'use strict';

/**
 * ContentImporter — unified import UI for professor-class.html
 *
 * Supports five sources:
 *   url        — paste any public URL
 *   pypi       — PyPI package documentation
 *   openstax   — browse OpenStax textbook catalog
 *   libretexts — search LibreTexts by subject
 *   oer        — search OER Commons
 *
 * Usage (after class_id is known):
 *   window.contentImporter = new ContentImporter(classId);
 */
class ContentImporter {
  constructor(classId) {
    this.classId = classId;
    this.activeTab = 'url';
    this.previewData = null; // payload to send on import
    this._openstaxLoaded = false;
    this._ltLibsLoaded = false;

    // CSP: the import cards are rendered at runtime into several containers, so
    // one delegated listener replaces the inline onclick attributes they carried.
    document.addEventListener('click', (e) => {
      const el = e.target.closest('[data-imp-action]');
      if (!el) return;
      const action = el.dataset.impAction;
      if (action === 'openToc') this.openOpenstaxToc(el.dataset.slug, el.dataset.title);
      else if (action === 'backToBooks') this.backToOpenstaxBooks();
      else if (action === 'selectUrl') this.selectUrl(el.dataset.url, el.dataset.title);
    });
  }

  // -------------------------------------------------------------------------
  // Modal open / close
  // -------------------------------------------------------------------------

  show() {
    const modal = document.getElementById('importChapterModal');
    modal.style.display = 'flex';
    this._clearError();
    this._hidePreview();
    this.switchTab(this.activeTab);
    if (!this._openstaxLoaded) this._loadOpenstaxBooks();
    if (!this._ltLibsLoaded) this._loadLibretextsLibraries();
  }

  hide() {
    const modal = document.getElementById('importChapterModal');
    modal.style.display = 'none';
    this._hidePreview();
    this._clearError();
    this.previewData = null;
  }

  // -------------------------------------------------------------------------
  // Tab navigation
  // -------------------------------------------------------------------------

  switchTab(tab) {
    this.activeTab = tab;
    document.querySelectorAll('.imp-tab-btn').forEach(btn => {
      btn.classList.toggle('imp-tab-active', btn.dataset.tab === tab);
    });
    document.querySelectorAll('.imp-tab-content').forEach(el => {
      el.style.display = el.id === `impTab-${tab}` ? 'block' : 'none';
    });
    this._hidePreview();
    this._clearError();
    this.previewData = null;
  }

  // -------------------------------------------------------------------------
  // Preview (URL + PyPI only — OpenStax/LT/OER navigate to a URL first)
  // -------------------------------------------------------------------------

  async previewUrl() {
    const url = document.getElementById('impUrlInput').value.trim();
    if (!url) { this._showError('Please enter a URL'); return; }
    await this._doPreview({ source: 'url', url });
  }

  async previewPypi() {
    const pkg = document.getElementById('impPypiPackage').value.trim();
    if (!pkg) { this._showError('Please enter a package name'); return; }
    await this._doPreview({ source: 'pypi', package: pkg });
  }

  async _doPreview(payload) {
    this._setLoading('impPreviewLoading', true);
    this._clearError();
    try {
      const resp = await authFetch('/api/import/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Preview failed');
      this.previewData = payload;
      this._showPreview(data.title, data.description, data.content_preview);
    } catch (err) {
      this._showError(err.message);
    } finally {
      this._setLoading('impPreviewLoading', false);
    }
  }

  // -------------------------------------------------------------------------
  // Select a URL result from OpenStax / LibreTexts / OER
  // -------------------------------------------------------------------------

  selectUrl(url, title) {
    this.previewData = { source: this.activeTab, url };
    document.getElementById('impChapterTitle').value = title || '';
    document.getElementById('impChapterDesc').value = '';
    document.getElementById('impPreviewTitle').textContent = title || url;
    document.getElementById('impPreviewSnippet').textContent = url;
    document.getElementById('impPreviewSection').style.display = 'block';
    this._clearError();
  }

  // -------------------------------------------------------------------------
  // Import
  // -------------------------------------------------------------------------

  async importChapter() {
    if (!this.previewData) { this._showError('Preview content first'); return; }
    const title = document.getElementById('impChapterTitle').value.trim();
    const desc = document.getElementById('impChapterDesc').value.trim();
    const exerciseMode =
      document.querySelector('input[name="impExerciseMode"]:checked')?.value || 'auto';

    if (!title) { this._showError('Chapter title is required'); return; }

    const payload = { ...this.previewData, title, description: desc, exercise_mode: exerciseMode };
    this._setLoading('impImportLoading', true);
    this._clearError();

    try {
      const resp = await authFetch(`/api/classes/${this.classId}/chapters/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Import failed');

      this.hide();

      // Reload the chapters list in professor-class.js if available
      if (typeof loadChapters === 'function') loadChapters();
      if (typeof loadClassData === 'function') loadClassData(this.classId);

      const exMsg = data.exercises_generated
        ? ` ${data.exercises_generated} exercise(s) auto-generated.`
        : '';
      alert(`"${title}" imported successfully.${exMsg}`);
    } catch (err) {
      this._showError(err.message);
    } finally {
      this._setLoading('impImportLoading', false);
    }
  }

  // -------------------------------------------------------------------------
  // OpenStax browser
  // -------------------------------------------------------------------------

  async _loadOpenstaxBooks() {
    const container = document.getElementById('impOpenstaxBooks');
    container.innerHTML = '<p style="color:#64748b">Loading catalog…</p>';
    try {
      const resp = await authFetch('/api/import/openstax/books');
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error);
      this._openstaxLoaded = true;
      if (!data.books.length) {
        container.innerHTML = '<p>No books found.</p>';
        return;
      }
      container.innerHTML = data.books
        .map(
          b =>
            `<div class="imp-card" data-imp-action="openToc" data-slug="${this._escAttr(b.slug)}" data-title="${this._escAttr(b.title)}">
               <strong>${b.title}</strong>
               ${b.description ? `<p class="imp-card-desc">${b.description}</p>` : ''}
             </div>`
        )
        .join('');
    } catch (err) {
      container.innerHTML = `<p style="color:#ef4444">${err.message}</p>`;
    }
  }

  async openOpenstaxToc(slug, title) {
    const panel = document.getElementById('impOpenstaxToc');
    panel.innerHTML = `<p style="color:#64748b">Loading chapters for <strong>${title}</strong>…</p>`;
    panel.style.display = 'block';
    document.getElementById('impOpenstaxBooks').style.display = 'none';

    try {
      const resp = await authFetch(`/api/import/openstax/books/${slug}/toc`);
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error);
      const items = data.toc || [];
      panel.innerHTML =
        `<button class="btn btn-secondary" style="margin-bottom:1rem"
           data-imp-action="backToBooks">← Back to Books</button>
         <h4 style="margin:0 0 1rem">${title}</h4>` +
        (items.length
          ? items
              .map(
                p =>
                  `<div class="imp-card" data-imp-action="selectUrl" data-url="${this._escAttr(p.url)}" data-title="${this._escAttr(p.title)}">
                     ${p.title}
                   </div>`
              )
              .join('')
          : `<p>No chapters found. Use the <strong>URL</strong> tab to paste a direct page link.</p>`);
    } catch (err) {
      panel.innerHTML = `<p style="color:#ef4444">${err.message}</p>`;
    }
  }

  backToOpenstaxBooks() {
    document.getElementById('impOpenstaxToc').style.display = 'none';
    document.getElementById('impOpenstaxBooks').style.display = 'block';
  }

  // -------------------------------------------------------------------------
  // LibreTexts search
  // -------------------------------------------------------------------------

  async _loadLibretextsLibraries() {
    try {
      const resp = await authFetch('/api/import/libretexts/libraries');
      const data = await resp.json();
      if (!resp.ok) return;
      const sel = document.getElementById('impLtLibrary');
      data.libraries.forEach(lib => {
        const opt = document.createElement('option');
        opt.value = lib.id;
        opt.textContent = lib.name;
        sel.appendChild(opt);
      });
      this._ltLibsLoaded = true;
    } catch (_) {}
  }

  async searchLibretexts() {
    const query = document.getElementById('impLtQuery').value.trim();
    const library = document.getElementById('impLtLibrary').value;
    if (!query) { this._showError('Enter a search term'); return; }

    const resultsEl = document.getElementById('impLtResults');
    resultsEl.innerHTML = '<p style="color:#64748b">Searching…</p>';
    this._clearError();

    try {
      const params = new URLSearchParams({ q: query, library });
      const resp = await authFetch(`/api/import/libretexts/search?${params}`);
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error);

      if (data.results.length) {
        resultsEl.innerHTML = data.results
          .map(
            r =>
              `<div class="imp-card" data-imp-action="selectUrl" data-url="${this._escAttr(r.url)}" data-title="${this._escAttr(r.title)}">
                 <strong>${r.title || r.url}</strong>
               </div>`
          )
          .join('');
      } else {
        resultsEl.innerHTML =
          `<p>No results. <a href="${data.search_url}" target="_blank" rel="noreferrer">Search on LibreTexts →</a></p>`;
      }
    } catch (err) {
      resultsEl.innerHTML = `<p style="color:#ef4444">${err.message}</p>`;
    }
  }

  // -------------------------------------------------------------------------
  // OER Commons search
  // -------------------------------------------------------------------------

  async searchOer() {
    const query = document.getElementById('impOerQuery').value.trim();
    if (!query) { this._showError('Enter a search term'); return; }

    const resultsEl = document.getElementById('impOerResults');
    resultsEl.innerHTML = '<p style="color:#64748b">Searching…</p>';
    this._clearError();

    try {
      const resp = await authFetch(`/api/import/oer/search?q=${encodeURIComponent(query)}`);
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error);

      if (data.results.length) {
        resultsEl.innerHTML = data.results
          .map(
            r =>
              `<div class="imp-card" data-imp-action="selectUrl" data-url="${this._escAttr(r.url)}" data-title="${this._escAttr(r.title)}">
                 <strong>${r.title}</strong>
                 ${r.description ? `<p class="imp-card-desc">${r.description}</p>` : ''}
                 ${r.license ? `<span class="imp-badge">${r.license}</span>` : ''}
               </div>`
          )
          .join('');
      } else {
        const fallback = data.search_url
          ? `<a href="${data.search_url}" target="_blank" rel="noreferrer">Search on OER Commons →</a>`
          : '';
        resultsEl.innerHTML = `<p>No results found. ${fallback}</p>`;
      }
    } catch (err) {
      resultsEl.innerHTML = `<p style="color:#ef4444">${err.message}</p>`;
    }
  }

  // -------------------------------------------------------------------------
  // Private helpers
  // -------------------------------------------------------------------------

  _showPreview(title, description, snippet) {
    document.getElementById('impChapterTitle').value = title || '';
    document.getElementById('impChapterDesc').value = description || '';
    document.getElementById('impPreviewTitle').textContent = title || '(no title)';
    document.getElementById('impPreviewSnippet').textContent = snippet || '';
    document.getElementById('impPreviewSection').style.display = 'block';
  }

  _hidePreview() {
    const el = document.getElementById('impPreviewSection');
    if (el) el.style.display = 'none';
  }

  _showError(msg) {
    const el = document.getElementById('impError');
    if (el) { el.textContent = msg; el.style.display = 'block'; }
  }

  _clearError() {
    const el = document.getElementById('impError');
    if (el) { el.textContent = ''; el.style.display = 'none'; }
  }

  _setLoading(id, on) {
    const el = document.getElementById(id);
    if (el) el.style.display = on ? 'inline' : 'none';
  }

  /** Escape a value for safe embedding in an HTML attribute (data-* payloads). */
  _escAttr(str) {
    return (str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }
}
