// Home page code animation — with syntax highlighting
document.addEventListener('DOMContentLoaded', function () {
    const codeElement = document.getElementById('codeAnimation');
    if (!codeElement) return;

    // Prevent duplicate animation on bfcache restore
    if (window.__homeAnimInitialised) return;
    window.__homeAnimInitialised = true;

    // Reset flag when page is restored from bfcache
    window.addEventListener('pageshow', function (e) {
        if (e.persisted) window.__homeAnimInitialised = false;
    });

    // ── Code to animate ───────────────────────────────────────────
    const code = `# Import the necessary libraries
from sklearn.datasets import load_wine
import pandas as pd

# Load the wine dataset from scikit-learn
wine = load_wine()

# Create a DataFrame from the dataset's data and feature names
df_wine = pd.DataFrame(data=wine.data, columns=wine.feature_names)

# Add the target column (the wine cultivar) to the DataFrame
df_wine['target'] = wine.target

# Display the first 5 rows of the DataFrame
print(df_wine.head())`;

    // ── Syntax highlighting token engine ─────────────────────────
    // Matches tokens in order: comment > string > keyword > builtin > number > punctuation > plain
    const TOKENS = [
        { type: 'comment', re: /^#[^\n]*/ },
        { type: 'string', re: /^(['"])(?:\\.|(?!\1)[^\\])*\1/ },
        { type: 'keyword', re: /^(?:from|import|def|class|return|if|elif|else|for|while|in|not|and|or|True|False|None|with|as|try|except|finally|raise|lambda|yield|pass|break|continue)\b/ },
        { type: 'builtin', re: /^(?:print|len|range|list|dict|tuple|set|int|str|float|bool|type|open|zip|map|filter|enumerate|sorted|reversed|sum|min|max|abs|round|input)\b/ },
        { type: 'number', re: /^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b/ },
        { type: 'attr', re: /^\.[a-zA-Z_]\w*/ },
        { type: 'punct', re: /^[=\[\](){}:,.<>+\-*/%!&|^~@]/ },
        { type: 'word', re: /^[a-zA-Z_]\w*/ },
        { type: 'space', re: /^\s+/ },
    ];

    const COLORS = {
        comment: '#6d8a9e',    // steel blue-grey
        string: '#98c379',    // green
        keyword: '#c678dd',    // purple
        builtin: '#56b6c2',    // teal
        number: '#d19a66',    // orange
        attr: '#61afef',    // light blue
        punct: '#abb2bf',    // grey
        word: '#ffffff',    // white (was gold #e5c07b)
        space: null,
    };

    /** Tokenise a plain-text snippet, return HTML string */
    function highlight(text) {
        let html = '';
        let pos = 0;
        const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

        while (pos < text.length) {
            let matched = false;
            for (const token of TOKENS) {
                const m = token.re.exec(text.slice(pos));
                if (!m) continue;
                const raw = m[0];
                const color = COLORS[token.type];
                if (color) {
                    html += `<span style="color:${color}">${esc(raw)}</span>`;
                } else {
                    html += esc(raw);
                }
                pos += raw.length;
                matched = true;
                break;
            }
            if (!matched) {
                // fallback: emit one char
                html += esc(text[pos]);
                pos++;
            }
        }
        return html;
    }

    // ── Typing state ─────────────────────────────────────────────
    let currentCharIndex = 0;
    let isDeleting = false;
    const typingSpeed = 28;
    const deletingSpeed = 12;
    const pauseTime = 2400;

    function typeCode() {
        const codeLine = codeElement.querySelector('.code-line');
        if (!codeLine) return;

        if (!isDeleting && currentCharIndex < code.length) {
            currentCharIndex++;
            const slice = code.substring(0, currentCharIndex);
            codeLine.innerHTML = highlight(slice) + '<span class="cursor">|</span>';
            setTimeout(typeCode, typingSpeed);

        } else if (isDeleting && currentCharIndex > 0) {
            currentCharIndex--;
            const slice = code.substring(0, currentCharIndex);
            codeLine.innerHTML = highlight(slice) + '<span class="cursor">|</span>';
            setTimeout(typeCode, deletingSpeed);

        } else if (!isDeleting && currentCharIndex === code.length) {
            // Pause at end, then start deleting
            codeLine.innerHTML = highlight(code); // no cursor at rest
            isDeleting = true;
            setTimeout(typeCode, pauseTime);

        } else if (isDeleting && currentCharIndex === 0) {
            // Restart
            isDeleting = false;
            codeLine.innerHTML = '<span class="cursor">|</span>';
            setTimeout(typeCode, 500);
        }
    }

    typeCode();
});
