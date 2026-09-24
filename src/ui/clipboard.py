"""Clipboard controls for Markdown and JSON artifacts.

Must not: assign `data.html` to the live page via `innerHTML` -- `data.html`
is derived from the source document's own content by src/markdown.py's
`parse_to_html`, so it's treated as text to copy, not as safe markup. It's
parsed with `DOMParser` in a detached document. Only serialized strings
are passed to the clipboard; parsed nodes are never inserted into the live DOM.

Next: src/ui/app.py's Markdown preview tab, the only caller.
"""

import streamlit as st


copy_buttons = st.components.v2.component(
    "ade_copy_buttons",
    html="""
    <button type="button" id="rendered">Copy rendered</button>
    <button type="button" id="raw">Copy Markdown</button>
    <button type="button" id="text">Copy</button>
    <span role="status" aria-live="polite"></span>
    """,
    css="""
    button {
        font: inherit; color: var(--st-text-color);
        background: var(--st-background-color);
        border: 1px solid var(--st-border-color);
        border-radius: var(--st-button-radius);
        padding: 0.5rem 0.75rem; cursor: pointer;
    }
    button:focus-visible { outline: 2px solid var(--st-primary-color); }
    """,
    js="""
    export default function ({data, parentElement}) {
        const status = parentElement.querySelector('[role="status"]');
        const textButton = parentElement.querySelector('#text');
        const markdownButtons = [parentElement.querySelector('#rendered'), parentElement.querySelector('#raw')];
        if (data.text !== undefined) {
            markdownButtons.forEach(button => button.hidden = true);
            textButton.textContent = data.label || 'Copy';
            textButton.onclick = async () => {
                try {
                    await navigator.clipboard.writeText(data.text);
                    status.textContent = ' Copied.';
                } catch {
                    status.textContent = ' Copy unavailable. Allow clipboard access and open this app on localhost or HTTPS.';
                }
            };
            return;
        }
        textButton.hidden = true;
        const parsed = new DOMParser().parseFromString(data.html, 'text/html');
        const renderedHtml = parsed.body.innerHTML;
        const renderedText = parsed.body.textContent;

        for (const mode of ['raw', 'rendered']) {
            parentElement.querySelector('#' + mode).onclick = async () => {
                try {
                    if (mode === 'raw') {
                        await navigator.clipboard.writeText(data.markdown);
                    } else {
                        await navigator.clipboard.write([new ClipboardItem({
                            'text/html': new Blob([renderedHtml], {type: 'text/html'}),
                            'text/plain': new Blob([renderedText], {type: 'text/plain'})
                        })]);
                    }
                    status.textContent = mode === 'raw' ? ' Markdown copied.' : ' Formatted content copied.';
                } catch {
                    status.textContent = ' Copy unavailable. Allow clipboard access and open this app on localhost or HTTPS.';
                }
            };
        }
    }
    """,
)
