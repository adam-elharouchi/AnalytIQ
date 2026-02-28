/**
 * ╔══════════════════════════════════════════════════════════════╗
 * ║  LOCAL DEV ONLY — Hero Animated Background                  ║
 * ║  This file is experimental and NOT intended for production. ║
 * ║  Remove <script src="js/hero-bg-animation.js"> from         ║
 * ║  index.html before any production deploy.                   ║
 * ╚══════════════════════════════════════════════════════════════╝
 */

(function () {
    'use strict';

    // ── Prevent duplicate initialisation (bfcache / repeated navigations) ──
    if (window.__heroBgInitialised) return;
    window.__heroBgInitialised = true;

    // ── Reduced-motion guard ──────────────────────────────────────
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // ── Only run on the home page ─────────────────────────────────
    const scene = document.getElementById('heroBgScene');
    if (!scene) return;

    // ── Helper: clear any previously-appended children (safety net) ──
    function clearLayer(el) {
        if (el) el.innerHTML = '';
    }

    if (prefersReduced) {
        // Static fallback: just show the dark tinted scene, no animation
        scene.classList.add('hero-bg-reduced');
        return;
    }

    // ══════════════════════════════════════════════════════════════
    // FAR LAYER — intentionally left empty (drifting columns removed)
    // ══════════════════════════════════════════════════════════════
    const farLayer = document.getElementById('heroBgFar');
    if (farLayer) clearLayer(farLayer);

    // ══════════════════════════════════════════════════════════════
    // MID LAYER — intentionally left empty (ghost code blocks removed)
    // ══════════════════════════════════════════════════════════════
    const midLayer = document.getElementById('heroBgMid');
    clearLayer(midLayer);

    // ══════════════════════════════════════════════════════════════
    // FOREGROUND LAYER — floating IDE windows with live typing
    // ══════════════════════════════════════════════════════════════
    const fgLayer = document.getElementById('heroBgFg');
    clearLayer(fgLayer);

    const windowConfigs = [
        {
            filename: 'analysis.py',
            floatClass: 'hero-bg-float-a',
            snippet: `import pandas as pd
import numpy as np

# Load and inspect dataset
df = pd.read_csv('analytics_data.csv')
print(df.describe())

# Clean missing values
df.dropna(subset=['target'], inplace=True)
df['date'] = pd.to_datetime(df['date'])

# Feature engineering
df['month'] = df['date'].dt.month
df['quarter'] = df['date'].dt.quarter
print(f"Dataset: {df.shape[0]} rows, {df.shape[1]} cols")`,
        },
        {
            filename: 'model.py',
            floatClass: 'hero-bg-float-b',
            snippet: `from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# Prepare features
X = df.drop('target', axis=1)
y = df['target']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Train model
model = RandomForestClassifier(n_estimators=100)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))`,
        },
        {
            filename: 'visualize.py',
            floatClass: 'hero-bg-float-c',
            snippet: `import matplotlib.pyplot as plt
import seaborn as sns

# Plot feature importance
importances = model.feature_importances_
feat_df = pd.DataFrame({
    'feature': X.columns,
    'importance': importances
}).sort_values('importance', ascending=False)

plt.figure(figsize=(10, 6))
sns.barplot(data=feat_df, x='importance', y='feature',
            palette='Blues_r')
plt.title('Feature Importance')
plt.tight_layout()
plt.savefig('feature_importance.png', dpi=150)
plt.show()`,
        },
        {
            filename: 'pipeline.py',
            floatClass: 'hero-bg-float-d',
            snippet: `from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

pipe = Pipeline([
    ('scaler', StandardScaler()),
    ('pca', PCA(n_components=0.95)),
    ('clf', RandomForestClassifier(
        n_estimators=200,
        max_depth=8
    ))
])

pipe.fit(X_train, y_train)
score = pipe.score(X_test, y_test)
print(f'Pipeline score: {score:.3f}')`,
        },
        {
            filename: 'explore.py',
            floatClass: 'hero-bg-float-e',
            snippet: `import pandas as pd

df = pd.read_csv('dataset.csv')

# Summary statistics
summary = df.describe()
print(summary)

# Detect outliers via IQR
Q1 = df.quantile(0.25)
Q3 = df.quantile(0.75)
IQR = Q3 - Q1
outliers = df[
    ((df < Q1 - 1.5 * IQR) |
     (df > Q3 + 1.5 * IQR)).any(axis=1)
]
print(f'Outliers found: {len(outliers)}')`,
        },
    ];

    // Typing engine for each window
    function createTypingEngine(bodyEl, snippet) {
        let charIndex = 0;
        let isDeleting = false;
        let isPaused = false;

        // Syntax-highlight a plain text snippet into safe HTML.
        // Uses a token-based approach: scan left-to-right, emit complete spans.
        function highlight(text) {
            function esc(s) {
                return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            }

            const KEYWORDS = new Set([
                'import', 'from', 'as', 'def', 'class', 'return', 'if', 'else', 'elif',
                'for', 'in', 'while', 'with', 'print', 'True', 'False', 'None', 'not',
                'and', 'or', 'lambda', 'yield', 'raise', 'try', 'except', 'finally',
                'pass', 'break', 'continue'
            ]);

            let out = '';
            let i = 0;

            while (i < text.length) {
                const ch = text[i];

                // Comment: # to end of line
                if (ch === '#') {
                    let end = text.indexOf('\n', i);
                    if (end === -1) end = text.length;
                    out += `<span class="hero-kw-comment">${esc(text.slice(i, end))}</span>`;
                    i = end;
                    continue;
                }

                // String: single or double quoted
                if (ch === "'" || ch === '"') {
                    let j = i + 1;
                    while (j < text.length && text[j] !== ch) j++;
                    if (j < text.length) j++; // include closing quote
                    out += `<span class="hero-kw-string">${esc(text.slice(i, j))}</span>`;
                    i = j;
                    continue;
                }

                // Identifier: keyword, function call, or plain name
                if (/[a-zA-Z_]/.test(ch)) {
                    let j = i + 1;
                    while (j < text.length && /\w/.test(text[j])) j++;
                    const word = text.slice(i, j);
                    // Look ahead for '(' to detect function call
                    let k = j;
                    while (k < text.length && text[k] === ' ') k++;
                    if (text[k] === '(') {
                        out += `<span class="hero-kw-function">${esc(word)}</span>`;
                    } else if (KEYWORDS.has(word)) {
                        out += `<span class="hero-kw-keyword">${esc(word)}</span>`;
                    } else {
                        out += esc(word);
                    }
                    i = j;
                    continue;
                }

                // Number
                if (/\d/.test(ch)) {
                    let j = i + 1;
                    while (j < text.length && /[\d.]/.test(text[j])) j++;
                    out += `<span class="hero-kw-number">${esc(text.slice(i, j))}</span>`;
                    i = j;
                    continue;
                }

                // Everything else: plain character
                out += esc(ch);
                i++;
            }

            return out;
        }


        function tick() {
            if (isPaused) return;

            if (!isDeleting && charIndex < snippet.length) {
                charIndex++;
                // Organic speed: slower at line starts, faster mid-line
                const ch = snippet[charIndex - 1];
                const delay = ch === '\n' ? (80 + Math.random() * 200) :
                    (20 + Math.random() * 40);
                bodyEl.innerHTML = highlight(snippet.substring(0, charIndex)) +
                    '<span class="hero-bg-typed-cursor">▋</span>';
                setTimeout(tick, delay);

            } else if (!isDeleting && charIndex === snippet.length) {
                // Pause at end
                isPaused = true;
                bodyEl.innerHTML = highlight(snippet);
                setTimeout(() => {
                    isPaused = false;
                    isDeleting = true;
                    tick();
                }, 3500 + Math.random() * 1500);

            } else if (isDeleting && charIndex > 0) {
                charIndex -= 2; // delete faster
                if (charIndex < 0) charIndex = 0;
                bodyEl.innerHTML = highlight(snippet.substring(0, charIndex)) +
                    '<span class="hero-bg-typed-cursor">▋</span>';
                setTimeout(tick, 12 + Math.random() * 8);

            } else if (isDeleting && charIndex === 0) {
                isDeleting = false;
                bodyEl.innerHTML = '<span class="hero-bg-typed-cursor">▋</span>';
                setTimeout(tick, 600);
            }
        }

        return tick;
    }

    if (fgLayer) {
        windowConfigs.forEach((cfg, idx) => {
            const win = document.createElement('div');
            win.className = `hero-bg-window ${cfg.floatClass}`;

            // Title bar
            const titlebar = document.createElement('div');
            titlebar.className = 'hero-bg-window-titlebar';
            titlebar.innerHTML = `
        <span class="hero-bg-window-dot dot-red"></span>
        <span class="hero-bg-window-dot dot-yellow"></span>
        <span class="hero-bg-window-dot dot-green"></span>
        <span class="hero-bg-window-filename">${cfg.filename}</span>
      `;

            // Code body
            const body = document.createElement('pre');
            body.className = 'hero-bg-window-body';
            body.innerHTML = '<span class="hero-bg-typed-cursor">▋</span>';

            win.appendChild(titlebar);
            win.appendChild(body);
            fgLayer.appendChild(win);

            // Start typing with staggered delay
            const startDelay = idx * 1800 + Math.random() * 800;
            setTimeout(createTypingEngine(body, cfg.snippet), startDelay);
        });
    }

    // ── Handle bfcache: reset flag so we re-init cleanly on back-nav ──
    window.addEventListener('pageshow', function (e) {
        if (e.persisted) {
            // Page was restored from bfcache — reset flag and re-run
            window.__heroBgInitialised = false;
        }
    });

})();
