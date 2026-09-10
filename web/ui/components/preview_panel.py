"""
PreviewPanel component — right panel of Quill.

Contains a tab bar (Preview / HTML Code), an iframe that renders
the generated design, an editable code panel, resize sliders,
and a download button.
"""
from duck.shortcuts import static
from duck.html.components.container import FlexContainer, Container
from duck.html.components.label import Label
from duck.html.components.paragraph import Paragraph
from duck.html.components import to_component
from duck.html.components.script import Script


# Local path to the bundled html2canvas script
HTML_2_CANVAS_SCRIPT_URL = static("js/html2canvas-pro.min.js")

# All JS injected once — sanitizer, tab switching, preview helpers,
# code editor, download, and streaming lifecycle functions
PANEL_SCRIPT = """
// HTML sanitizer
// Do nothing for now.

function quillSanitizeHtml(html) {
    return html;
}

// Tab switching

function quillSwitchTab(tab) {
    var previewTab  = document.getElementById('quill-tab-preview');
    var codeTab     = document.getElementById('quill-tab-code');
    var previewPane = document.getElementById('quill-pane-preview');
    var codePane    = document.getElementById('quill-pane-code');

    if (tab === 'preview') {
        previewTab.classList.add('active');
        codeTab.classList.remove('active');
        previewPane.style.display = 'flex';
        codePane.style.display    = 'none';
    } else {
        codeTab.classList.add('active');
        previewTab.classList.remove('active');
        codePane.style.display    = 'flex';
        previewPane.style.display = 'none';
    }
}

// Preview helpers

function quillSetPreview(html) {
    html = quillSanitizeHtml(html);
    var frame = document.getElementById('quill-preview-frame');
    var codeEditor = document.getElementById('quill-code-editor');
    
    if (!frame) return;
    
    // Set the HTML
    frame.srcdoc = html;
    
    // Switch to code tab (if not)
    quillSwitchTab('code');
    
    // Start scroll logic; scroll to visible latest content
    codeEditor.scrollTo(0, codeEditor.scrollHeight);
      
    // Sync code editor and highlighting
    var editor = document.getElementById('quill-code-editor');
    
    if (editor) {
        editor.value = html;
        quillSyncHighlight();
    }

    // Hide spinner now that content is arriving
    var spinner = document.getElementById('quill-spinner-overlay');
    if (spinner) spinner.style.display = 'none';

    // Reveal preview wrap — height from slider which is always up to date
    var wrap = document.getElementById('quill-preview-wrap');
    
    if (wrap) {
        var h = document.getElementById('quill-h-slider').value;
        wrap.style.display = 'block';
        wrap.style.height  = h + 'px';
    }

    document.getElementById('quill-placeholder').style.display = 'none';
}

function quillResizePreview(w, h) {
    var frame = document.getElementById('quill-preview-frame');
    var wrap  = document.getElementById('quill-preview-wrap');
    if (!frame) return;

    // Resize the iframe to the exact design dimensions
    frame.style.width  = w + 'px';
    frame.style.height = h + 'px';

    // Match wrap height so the scroll container covers the full design
    if (wrap) wrap.style.height = h + 'px';
}

function quillUpdateWidth(val) {
    // Slider moved — sync the number input and resize
    var n = parseInt(val);
    var input = document.getElementById('quill-w-input');
    if (input && parseInt(input.value) !== n) input.value = n;
    var h = parseInt(document.getElementById('quill-h-slider').value);
    quillResizePreview(n, h);
}

function quillUpdateHeight(val) {
    // Slider moved — sync the number input and resize
    var n = parseInt(val);
    var input = document.getElementById('quill-h-input');
    if (input && parseInt(input.value) !== n) input.value = n;
    var w = parseInt(document.getElementById('quill-w-slider').value);
    quillResizePreview(w, n);
}

function quillInputWidth(val) {
    // Number input changed — clamp, sync slider, and resize
    var slider = document.getElementById('quill-w-slider');
    if (!slider) return;
    var n = Math.min(parseInt(slider.max), Math.max(parseInt(slider.min), parseInt(val) || parseInt(slider.min)));
    slider.value = n;
    var h = parseInt(document.getElementById('quill-h-slider').value);
    quillResizePreview(n, h);
}

function quillInputHeight(val) {
    // Number input changed — clamp, sync slider, and resize
    var slider = document.getElementById('quill-h-slider');
    if (!slider) return;
    var n = Math.min(parseInt(slider.max), Math.max(parseInt(slider.min), parseInt(val) || parseInt(slider.min)));
    slider.value = n;
    var w = parseInt(document.getElementById('quill-w-slider').value);
    quillResizePreview(w, n);
}

// Code editor — apply changes to preview

function quillApplyCode() {
    var textarea = document.getElementById('quill-code-editor');
    
    if (!textarea) return;
    
    var html = textarea.value;
    window._quillBuffer = html;
    quillSyncHighlight();
    quillSetPreview(html);
    quillSwitchTab('preview');

    // Show download button
    document.getElementById('quill-download-btn').style.display = 'inline-block';
}

// Download via html2canvas

function quillDownload() {
    var frame = document.getElementById('quill-preview-frame');
    if (!frame || !frame.srcdoc) {
        alert('Generate a design first.');
        return;
    }
    var btn = document.getElementById('quill-download-btn');
    btn.innerText = 'Capturing…';
    btn.disabled  = true;

    // Read the intended design dimensions from the sliders, not the
    // rendered iframe size — this ensures full quality on any device
    var designW = parseInt(document.getElementById('quill-w-input') ? document.getElementById('quill-w-input').value : document.getElementById('quill-w-slider').value) || 800;
    var designH = parseInt(document.getElementById('quill-h-input') ? document.getElementById('quill-h-input').value : document.getElementById('quill-h-slider').value) || 600;

    // Snapshot current iframe size so we can restore it after capture
    var prevWidth  = frame.style.width;
    var prevHeight = frame.style.height;

    // Temporarily set iframe to the exact design dimensions so
    // html2canvas captures the full design, not the mobile viewport
    frame.style.width = designW + 'px';
    frame.style.height = designH + 'px';
    frame.style.overflow = 'hidden';
    
    // Make sure we are in preview tab.
    quillSwitchTab('preview');

    // Inject html2canvas into the iframe and capture at full resolution
    var doc = frame.contentDocument || frame.contentWindow.document;
    var script = doc.createElement('script');
    script.src = '""" + HTML_2_CANVAS_SCRIPT_URL + r"""';
    script.onload = function() {
        frame.contentWindow.html2canvas(doc.body, {
            useCORS: true,
            allowTaint: true,
            scale:      2,        // 2x for retina quality
            width:      designW,
            height:     designH,
            windowWidth:  designW,
            windowHeight: designH,
            scrollX: 0,
            scrollY: 0,
        }).then(function(canvas) {
            // Download the PNG
           
            // Resize down to exact design dimensions
            var out = document.createElement('canvas');
            out.width  = designW;
            out.height = designH;
            out.getContext('2d').drawImage(canvas, 0, 0, designW, designH);
        
            var link = document.createElement('a');
            link.download = 'quill-design-' + Date.now().toString(36) + '.png';
            link.href = out.toDataURL('image/png');
            link.click();

            // Restore iframe to its previous display size
            frame.style.width    = prevWidth;
            frame.style.height   = prevHeight;
            frame.style.overflow = '';

            btn.innerText = '⬇ Download PNG';
            btn.disabled  = false;
        }).catch(function() {
            // Restore on error too
            frame.style.width    = prevWidth;
            frame.style.height   = prevHeight;
            frame.style.overflow = '';

            btn.innerText = '⬇ Download PNG';
            btn.disabled  = false;
            alert('Capture failed. Please try again.');
        });
    };
    doc.head.appendChild(script);
}

// Device-adaptive initial dimensions
// Sets the iframe and sliders to fit the device screen on first load.
// Width = available panel width, height = 75% of viewport height.
// Both are clamped to the slider's min/max range.

function quillInitDimensions() {
    var wSlider = document.getElementById('quill-w-slider');
    var hSlider = document.getElementById('quill-h-slider');
    var wInput  = document.getElementById('quill-w-input');
    var hInput  = document.getElementById('quill-h-input');
    var frame   = document.getElementById('quill-preview-frame');
    if (!wSlider || !hSlider || !frame) return;

    // Use the right panel's available width as the design width,
    // falling back to the window width minus a sidebar estimate
    var rightPanel = document.getElementById('quill-right');
    var availW = rightPanel
        ? rightPanel.clientWidth - 56   // subtract padding on both sides
        : window.innerWidth;

    // Clamp to slider range
    var minW = parseInt(wSlider.min);
    var maxW = parseInt(wSlider.max);
    var minH = parseInt(hSlider.min);
    var maxH = parseInt(hSlider.max);

    var initW = Math.min(maxW, Math.max(minW, availW));
    var initH = Math.min(maxH, Math.max(minH, Math.round(window.innerHeight * 0.75)));

    // Apply to sliders, labels, and iframe
    wSlider.value    = initW;
    hSlider.value    = initH;
    if (wInput) wInput.value = initW;
    if (hInput) hInput.value = initH;
    frame.setAttribute('style', 'width:' + initW + 'px;height:' + initH + 'px;border:none;background:#fff;display:block;');

    // Sync wrap height
    var wrap = document.getElementById('quill-preview-wrap');
    if (wrap) wrap.style.height = initH + 'px';
}

// Run after DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', quillInitDimensions);
} else {
    quillInitDimensions();
}

// Optimal sizes per design type.
// These are fixed pixel sizes that match the natural format of each type.
// On small devices they're scaled down proportionally to fit the screen.
var DESIGN_SIZES = {
    // AI design types
    poster:           { w: 600,  h: 900  },
    code:             { w: 800,  h: 500  },
    social:           { w: 600,  h: 600  },
    certificate:      { w: 900,  h: 640  },
    opengraph:        { w: 1200, h: 630  },
    custom:           { w: 800,  h: 600  },
    // Import mode — UA-based viewport sizes
    desktop_chrome:   { w: 1280, h: 800  },
    desktop_firefox:  { w: 1280, h: 800  },
    desktop_safari:   { w: 1280, h: 900  },
    iphone:           { w: 390,  h: 844  },
    android:          { w: 412,  h: 915  },
    googlebot:        { w: 1280, h: 800  },
    ua_custom:        { w: 1280, h: 800  },
};

// Hint messages shown after generation so the user knows they can resize
var DESIGN_HINTS = {
    // AI design types
    poster:           '↔ Poster set to 600×900. Drag the sliders to resize.',
    code:             '↔ Code card set to 800×500. Widen for longer lines.',
    social:           '↔ Social card set to 600×600. Resize to match your platform.',
    certificate:      '↔ Certificate set to 900×640. Scale up for print quality.',
    opengraph:        '↔ OG image set to 1200×630 — standard social share size.',
    custom:           '↔ Design ready. Use the sliders to adjust width and height.',
    // Import mode UA hints
    desktop_chrome:   '↔ Set to 1280×800 — standard desktop Chrome viewport.',
    desktop_firefox:  '↔ Set to 1280×800 — standard desktop Firefox viewport.',
    desktop_safari:   '↔ Set to 1280×900 — standard desktop Safari viewport.',
    iphone:           '↔ Set to 390×844 — iPhone 14 viewport. Scroll to see full page.',
    android:          '↔ Set to 412×915 — Pixel 8 viewport. Scroll to see full page.',
    googlebot:        '↔ Set to 1280×800 — Googlebot desktop viewport.',
    ua_custom:        '↔ Custom UA — default 1280×800. Adjust as needed.',
};

function quillApplyDesignDimensions(designType) {
    var size    = DESIGN_SIZES[designType] || DESIGN_SIZES['custom'];
    var wSlider = document.getElementById('quill-w-slider');
    var hSlider = document.getElementById('quill-h-slider');
    var wInput  = document.getElementById('quill-w-input');
    var hInput  = document.getElementById('quill-h-input');
    var frame   = document.getElementById('quill-preview-frame');
    if (!wSlider || !hSlider || !frame) return;

    var w = size.w;
    var h = size.h;

    // Apply everywhere
    wSlider.value      = w;
    hSlider.value      = h;
    if (wInput) wInput.value = w;
    if (hInput) hInput.value = h;
    frame.setAttribute('style', 'width:' + w + 'px;height:' + h + 'px;border:none;background:#fff;display:block;');

    var wrap = document.getElementById('quill-preview-wrap');
    if (wrap) wrap.style.height = h + 'px';
}

// Syntax highlighting via Prism.js (loaded from CDN in home.py head).
// Prism registers HTML as 'markup' — not 'html'. Also check the grammar
// is loaded before calling highlight (autoloader is async).

function quillSyncHighlight() {
    var textarea = document.getElementById('quill-code-editor');
    var display  = document.getElementById('quill-code-display');
    if (!textarea || !display) return;

    var code = textarea.value;

    // Use Prism if available and the markup grammar is ready
    if (window.Prism && Prism.languages.markup) {
        display.innerHTML = Prism.highlight(code, Prism.languages.markup, 'markup') + '\n';
    } else {
        // Plain escaped fallback until Prism loads
        display.innerHTML = code
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;') + '\n';
    }

    // Keep scroll positions in sync
    display.scrollTop  = textarea.scrollTop;
    display.scrollLeft = textarea.scrollLeft;
}

function quillSyncScroll() {
    var textarea = document.getElementById('quill-code-editor');
    var display  = document.getElementById('quill-code-display');
    if (!textarea || !display) return;
    display.scrollTop  = textarea.scrollTop;
    display.scrollLeft = textarea.scrollLeft;
}

// Error box — visible message inside the preview pane when something goes wrong

function quillShowError(title, message) {
    // Hide spinner and generating badge
    var spinner = document.getElementById('quill-spinner-overlay');
    var badge   = document.getElementById('quill-generating-badge');
    if (spinner) spinner.style.display = 'none';
    if (badge)   badge.style.display   = 'none';

    // Hide previous content and placeholder
    var placeholder = document.getElementById('quill-placeholder');
    var previewWrap = document.getElementById('quill-preview-wrap');
    if (placeholder) placeholder.style.display = 'none';
    if (previewWrap) previewWrap.style.display  = 'none';

    // Populate and show the error box
    var box = document.getElementById('quill-error-box');
    if (!box) return;
    document.getElementById('quill-error-title').innerHTML = title;
    document.getElementById('quill-error-message').innerHTML = message;
    box.style.display = 'flex';
}

function quillHideError() {
    var box = document.getElementById('quill-error-box');
    if (box) box.style.display = 'none';
}

function quillShowHint(designType) {
    var hint = document.getElementById('quill-resize-hint');
    var hintWrap = document.getElementById('quill-resize-hint-wrap');
    if (!hint || !hintWrap) return;
    hint.innerText = DESIGN_HINTS[designType] || DESIGN_HINTS['custom'];
    hintWrap.style.display = 'flex';
}

// Streaming lifecycle

window._quillBuffer = '';

function quillFinalise(html) {
    html = quillSanitizeHtml(html);
    window._quillBuffer = html;
    quillSetPreview(html);
    
    // Show download button
    document.getElementById('quill-download-btn').style.display = 'inline-block';

    // Hide generating badge
    document.getElementById('quill-generating-badge').style.display = 'none';

    // Hide spinner overlay
    var spinner = document.getElementById('quill-spinner-overlay');
    if (spinner) spinner.style.display = 'none';

    // Show resize hint so the user knows they can adjust dimensions
    quillShowHint(window._quillDesignType || 'custom');

    // Restore button styles
    var btn = document.getElementById('quill-submit-btn');
    if (btn) {
        btn.style.background = '';
        btn.style.animation  = '';
    }
}

function quillStartStream(designType) {
    window._quillBuffer  = '';
    window._quillDesignType = designType || 'custom';

    // Set design-type dimensions before the stream begins
    quillApplyDesignDimensions(designType || 'custom');

    // Hide download button, show generating badge
    document.getElementById('quill-download-btn').style.display = 'none';
    document.getElementById('quill-generating-badge').style.display = 'inline-block';

    // Hide hint from any previous generation
    var hint = document.getElementById('quill-resize-hint-wrap');
    if (hint) hint.style.display = 'none';

    // Hide error box from any previous error
    quillHideError();

    // Switch to Code tab to show code being written.
    quillSwitchTab('preview');

    // Hide placeholder and previous preview, show spinner
    var placeholder = document.getElementById('quill-placeholder');
    var previewWrap = document.getElementById('quill-preview-wrap');
    var spinner     = document.getElementById('quill-spinner-overlay');
    if (placeholder) placeholder.style.display = 'none';
    if (previewWrap) previewWrap.style.display  = 'none';
    if (spinner)     spinner.style.display      = 'flex';

    // Clear iframe and code editor
    var frame   = document.getElementById('quill-preview-frame');
    var editor  = document.getElementById('quill-code-editor');
    var display = document.getElementById('quill-code-display');
    if (frame)   frame.srcdoc    = '';
    if (editor)  editor.value    = '';
    if (display) display.innerHTML = '';

    // Animate generate button
    var btn = document.getElementById('quill-submit-btn');
    if (btn) {
        btn.style.background = 'linear-gradient(135deg, #4f46e5, #6366f1)';
        btn.style.animation  = 'quillBtnPulse 1.2s ease-in-out infinite';
    }
}
"""

# Tab and spinner styles injected once into the page
TAB_STYLES = """
<style>
.quill-tab-btn {
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: rgba(255,255,255,0.35);
    font-family: inherit;
    font-size: 0.82rem;
    font-weight: 600;
    padding: 8px 16px;
    cursor: pointer;
    letter-spacing: 0.04em;
    transition: color 0.15s, border-color 0.15s;
    flex-shrink: 0;
}
.quill-tab-btn.active {
    color: #fff;
    border-bottom: 2px solid #6366f1;
}
.quill-tab-btn:hover:not(.active) {
    color: rgba(255,255,255,0.65);
}

/* Editor container — stacks the highlight display and textarea on top of each other */
#quill-editor-wrap {
    position: relative;
    flex: 1;
    overflow: hidden;
    background: #0d1117;
}

/* Shared styles for both the display div and the textarea */
#quill-code-display,
#quill-code-editor {
    position: absolute;
    top: 0; left: 0;
    width: 100%;
    height: 100%;
    margin: 0;
    padding: 16px;
    border: none;
    outline: none;
    font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
    font-size: 0.78rem;
    line-height: 1.65;
    tab-size: 2;
    white-space: pre;
    overflow: auto;
    box-sizing: border-box;
    word-wrap: normal;
}

/* Highlighted display layer — sits below, not interactive */
#quill-code-display {
    background: #0d1117;
    color: #e6edf3;
    pointer-events: none;
    z-index: 1;
}

/* Textarea — sits on top, transparent so the highlight shows through */
#quill-code-editor {
    background: transparent;
    color: transparent;
    caret-color: #e6edf3;
    resize: none;
    z-index: 2;
    spellcheck: false;
}

#quill-code-editor::selection {
    background: rgba(99,102,241,0.35);
    color: transparent;
}

/* Syntax highlight token colours — overridden by Prism theme via CDN */
/* Prism uses .token.* classes; these are kept as fallback only */
.hl-doctype  { color: #8b949e; }
.hl-comment  { color: #8b949e; font-style: italic; }
.hl-tag      { color: #7ee787; }
.hl-tagname  { color: #7ee787; font-weight: 600; }
.hl-attr     { color: #79c0ff; }
.hl-str      { color: #a5d6ff; }
.hl-prop     { color: #d2a8ff; }

/* Spinner overlay */
#quill-spinner-overlay {
    position: absolute;
    top: 0; left: 0;
    width: 100%;
    height: 100%;
    min-height: 380px;
    display: none;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 16px;
    background: #0d0d14;
    border-radius: 14px;
    z-index: 10;
}
.quill-spinner {
    width: 36px;
    height: 36px;
    border: 3px solid rgba(99,102,241,0.2);
    border-top-color: #6366f1;
    border-radius: 50%;
    animation: quillSpin 0.75s linear infinite;
}
.quill-spinner-label {
    font-size: 0.8rem;
    color: rgba(255,255,255,0.3);
    letter-spacing: 0.06em;
    animation: pulse 1.5s ease-in-out infinite;
}

/* Button loading pulse */
@keyframes quillBtnPulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.65; }
}
@keyframes quillSpin {
    to { transform: rotate(360deg); }
}
</style>
"""


class PreviewPanel(FlexContainer):
    """
    Right panel of Quill.

    Builds a tab bar (Preview / HTML Code), iframe preview pane,
    editable code pane, resize sliders, and download button.
    """
    def on_create(self):
        super().on_create()
        self.style.update({
            "flex-direction": "column",
            "flex": "1",
            "gap": "16px",
            "min-width": "0",
        })
        self.inject_tab_styles()
        self.build_tab_bar()
        self.build_preview_pane()
        self.build_code_pane()
        self.build_resize_controls()
        self.build_download_bar()
        self.inject_script()

    # Tab styles
    def inject_tab_styles(self):
        """
        Injects the CSS for tab buttons, code editor, and spinner.
        """
        self.add_child(to_component(TAB_STYLES, "div"))

    # Tab bar
    def build_tab_bar(self):
        """
        Builds the Preview / HTML Code tab bar.
        """
        self.tab_bar = FlexContainer(
            style={
                "flex-direction": "row",
                "border-bottom": "1px solid rgba(255,255,255,0.07)",
                "gap": "0",
                "flex-shrink": "0",
            },
        )

        # Preview tab (active by default)
        preview_tab = to_component("⬜  Preview", "button")
        preview_tab.id = "quill-tab-preview"
        preview_tab.props.update({
            "type": "button",
            "onclick": "quillSwitchTab('preview')",
            "class": "quill-tab-btn active",
        })

        # HTML Code tab
        code_tab = to_component("&lt;/&gt;  HTML Code", "button")
        code_tab.id = "quill-tab-code"
        code_tab.props.update({
            "type": "button",
            "onclick": "quillSwitchTab('code')",
            "class": "quill-tab-btn",
        })

        self.tab_bar.add_children([preview_tab, code_tab])
        self.add_child(self.tab_bar)

    # Preview pane
    def build_preview_pane(self):
        """
        Builds the preview pane: outer box, placeholder, iframe, and spinner overlay.
        """
        info_div = FlexContainer(
            children=[
                Paragraph(
                    text="If the preview is not being displayed correctly. Switch to code tab and try clicking 'Apply' button again!",
                    style={"padding": "10px", "color": "rgba(255,255,255,0.2)", "font-size": ".9rem"},
                ),
                    
            ],
        )
        
        self.preview_pane = FlexContainer(
            id="quill-pane-preview",
            style={
                "flex-direction": "column",
                "flex": "1",
                "min-height": "380px",
                "position": "relative",
            },
        )

        # Outer container
        self.preview_outer = Container(
            style={
                "position": "relative",
                "width": "100%",
                "flex": "1",
                "border-radius": "14px",
                "overflow": "visible",  # must not clip the scrollable preview wrap
                "border": "1px solid rgba(255,255,255,0.07)",
                "background": "#0d0d14",
                "min-height": "380px",
            },
        )

        # Placeholder shown before any generation
        self.placeholder = FlexContainer(
            id="quill-placeholder",
            style={
                "flex-direction": "column",
                "align-items": "center",
                "justify-content": "center",
                "width": "100%",
                "min-height": "380px",
                "gap": "12px",
            },
        )

        icon = to_component("✦", "div")
        icon.style.update({"font-size": "2.5rem", "color": "rgba(99,102,241,0.4)"})

        placeholder_text = Paragraph(
            inner_html="Your design will appear here",
            style={"color": "rgba(255,255,255,0.2)", "font-size": "0.85rem", "margin": "0"},
        )
        self.placeholder.add_children([icon, placeholder_text])

        # Preview wrap — scrollable container that always matches the design size.
        # overflow:auto enables scrolling when the design is bigger than the viewport.
        self.preview_wrap = Container(
            id="quill-preview-wrap",
            style={
                "display": "none",
                "overflow": "auto",
                "width": "100%",
                "min-height": "380px",
                "background": "#0d0d14",
                "border-radius": "14px",
            },
        )

        # iframe — sandboxed so generated HTML runs safely.
        # Initial size is overridden by quillInitDimensions on page load.
        # No border-radius or box-shadow so nothing clips the design during capture.
        self.iframe = to_component("", "iframe", no_closing_tag=False)
        self.iframe.id = "quill-preview-frame"
        self.iframe.props.update({
            "id": "quill-preview-frame",
            "sandbox": "allow-same-origin allow-scripts",
            "style": (
                "width:800px;height:600px;border:none;"
                "background:#fff;display:block;"
            ),
        })
        self.preview_wrap.add_child(self.iframe)

        # Spinner overlay — absolutely positioned over the preview pane
        spinner_overlay = FlexContainer(
            id="quill-spinner-overlay",
            style={
                "position": "absolute",
                "top": "0",
                "left": "0",
                "width": "100%",
                "height": "100%",
                "min-height": "380px",
                "display": "none",
                "flex-direction": "column",
                "align-items": "center",
                "justify-content": "center",
                "gap": "16px",
                "background": "#0d0d14",
                "border-radius": "14px",
                "z-index": "10",
            },
        )

        spinner_ring = to_component("", "div")
        spinner_ring.klass = "quill-spinner"

        spinner_label = to_component("Generating…", "span")
        spinner_label.klass = "quill-spinner-label"

        spinner_overlay.add_children([spinner_ring, spinner_label])

        # Error box — shown in place of the preview when generation fails
        error_box = FlexContainer(
            id="quill-error-box",
            style={
                "display": "none",
                "flex-direction": "column",
                "align-items": "center",
                "justify-content": "center",
                "width": "100%",
                "min-height": "380px",
                "gap": "12px",
                "padding": "32px",
                "text-align": "center",
            },
        )

        error_icon = to_component("&#9888;", "div")
        error_icon.style.update({
            "font-size": "2rem",
            "color": "#f87171",
        })

        error_title = to_component("", "div")
        error_title.id = "quill-error-title"
        error_title.style.update({
            "font-size": "0.95rem",
            "font-weight": "700",
            "color": "#fff",
        })

        error_message = to_component("", "div")
        error_message.id = "quill-error-message"
        error_message.style.update({
            "font-size": "0.82rem",
            "color": "rgba(255,255,255,0.45)",
            "max-width": "360px",
            "line-height": "1.6",
        })

        error_box.add_children([error_icon, error_title, error_message])

        # Outer holds placeholder, preview wrap, and error box
        self.preview_outer.add_children([
            self.placeholder,
            self.preview_wrap,
            error_box,
        ])

        # Spinner sits at pane level so it covers the full pane area
        self.preview_pane.add_children([info_div, self.preview_outer, spinner_overlay])
        self.add_child(self.preview_pane)

    # Code pane
    def build_code_pane(self):
        """
        Builds the HTML code editor pane with a toolbar and Apply button.
        """
        self.code_pane = FlexContainer(
            id="quill-pane-code",
            style={
                "flex-direction": "column",
                "flex": "1",
                "display": "none",
                "border-radius": "14px",
                "overflow": "hidden",
                "border": "1px solid rgba(255,255,255,0.07)",
                "background": "#0d1117",
                "min-height": "380px",
                "gap": "0",
            },
        )

        # Toolbar
        toolbar = FlexContainer(
            style={
                "flex-direction": "row",
                "align-items": "center",
                "justify-content": "space-between",
                "padding": "10px 16px",
                "background": "#161b22",
                "border-bottom": "1px solid rgba(255,255,255,0.06)",
                "flex-shrink": "0",
            },
        )

        toolbar_label = Label(
            text="Edit HTML — changes apply to the preview",
            style={
                "font-size": "0.72rem",
                "color": "rgba(255,255,255,0.35)",
                "letter-spacing": "0.04em",
            },
        )

        apply_btn = to_component("▶  Apply", "button")
        apply_btn.props.update({"type": "button", "onclick": "quillApplyCode()"})
        apply_btn.style.update({
            "background": "#6366f1",
            "color": "#fff",
            "border": "none",
            "border-radius": "7px",
            "padding": "6px 14px",
            "font-size": "0.78rem",
            "font-weight": "700",
            "cursor": "pointer",
            "font-family": "inherit",
            "letter-spacing": "0.03em",
        })

        toolbar.add_children([toolbar_label, apply_btn])

        # Overlay editor — a highlighted display div with a transparent
        # textarea on top. The textarea captures all input and fires
        # quillSyncHighlight on every keystroke to keep the display in sync.
        editor_wrap = to_component("", "div", no_closing_tag=False)
        editor_wrap.id = "quill-editor-wrap"

        # Highlight display layer (read-only, pointer-events none)
        display = to_component("", "div", no_closing_tag=False)
        display.id = "quill-code-display"
        display.props.update({"aria-hidden": "true"})

        # Transparent textarea on top — captures all editing
        editor = to_component("", "textarea", no_closing_tag=False)
        editor.id = "quill-code-editor"
        editor.props.update({
            "id": "quill-code-editor",
            "spellcheck": "false",
            "autocomplete": "off",
            "autocorrect": "off",
            "autocapitalize": "off",
            "oninput": "quillSyncHighlight()",
            "onscroll": "quillSyncScroll()",
            "onkeydown": "setTimeout(quillSyncHighlight, 0)",
            "placeholder": "Generated HTML will appear here.\nYou can edit it and click Apply to update the preview.",
        })

        editor_wrap.add_children([display, editor])
        self.code_pane.add_children([toolbar, editor_wrap])
        self.add_child(self.code_pane)

    # Resize controls
    def build_resize_controls(self):
        """
        Builds the hint message, width/height sliders, and generating badge.
        """
        # Hint message — hidden until a design is generated
        self.resize_hint = FlexContainer(
            id="quill-resize-hint-wrap",
            style={
                "display": "none",
                "flex-direction": "row",
                "align-items": "center",
                "gap": "8px",
                "background": "rgba(99,102,241,0.07)",
                "border": "1px solid rgba(99,102,241,0.18)",
                "border-radius": "8px",
                "padding": "9px 14px",
            },
        )

        hint_icon = to_component("↔", "span")
        hint_icon.style.update({
            "font-size": "0.85rem",
            "color": "#818cf8",
            "flex-shrink": "0",
        })

        hint_text = to_component("", "span")
        hint_text.id = "quill-resize-hint"
        hint_text.style.update({
            "font-size": "0.75rem",
            "color": "rgba(255,255,255,0.45)",
            "line-height": "1.4",
        })

        self.resize_hint.add_children([hint_icon, hint_text])
        self.add_child(self.resize_hint)

        # Sliders row
        self.resize_row = FlexContainer()
        self.resize_row.klass = "quill-resize-row"
        self.resize_row.style.update({
            "flex-direction": "row",
            "gap": "20px",
            "align-items": "center",
            "flex-wrap": "wrap",
        })

        # Width slider — initial value overridden by quillInitDimensions on load
        self.resize_row.add_child(self.build_slider_group(
            label="Width",
            slider_id="quill-w-slider",
            input_id="quill-w-input",
            default=800, min_val=5, max_val=1920,
            on_slider="quillUpdateWidth(this.value)",
            on_input="quillInputWidth(this.value)",
        ))

        # Height slider — initial value overridden by quillInitDimensions on load
        self.resize_row.add_child(self.build_slider_group(
            label="Height",
            slider_id="quill-h-slider",
            input_id="quill-h-input",
            default=600, min_val=5, max_val=1920,
            on_slider="quillUpdateHeight(this.value)",
            on_input="quillInputHeight(this.value)",
        ))

        # Generating badge
        self.generating_badge = to_component("⏳ Generating…", "span")
        self.generating_badge.id = "quill-generating-badge"
        self.generating_badge.style.update({
            "font-size": "0.75rem",
            "color": "#818cf8",
            "background": "rgba(99,102,241,0.1)",
            "border": "1px solid rgba(99,102,241,0.25)",
            "padding": "4px 12px",
            "border-radius": "99px",
            "display": "none",
            "animation": "pulse 1.5s ease-in-out infinite",
        })
        self.resize_row.add_child(self.generating_badge)

        self.add_child(self.resize_row)

    def build_slider_group(
        self,
        label,
        slider_id,
        input_id,
        default,
        min_val,
        max_val,
        on_slider,
        on_input,
    ) -> FlexContainer:
        """
        Builds a labelled range slider with a synced number input.

        The slider and number input are two-way synced — moving the slider
        updates the input, and typing in the input updates the slider.

        Args:
            label:     Display label (e.g. "Width").
            slider_id: HTML id for the range input.
            input_id:  HTML id for the number input.
            default:   Initial value.
            min_val:   Minimum range value.
            max_val:   Maximum range value.
            on_slider: JS called when the slider changes.
            on_input:  JS called when the number input changes.

        Returns:
            A FlexContainer containing the label, slider, and number input.
        """
        group = FlexContainer(
            style={
                "flex-direction": "row",
                "align-items": "center",
                "gap": "10px",
                "flex": "1",
                "min-width": "180px",
            },
        )

        # Label
        lbl = Label(
            text=label,
            style={
                "font-size": "0.75rem",
                "color": "rgba(255,255,255,0.4)",
                "min-width": "40px",
                "text-transform": "uppercase",
                "letter-spacing": "0.08em",
            },
        )

        # Range slider — drag for coarse adjustment
        slider = to_component("", "input", no_closing_tag=True)
        slider.id = slider_id
        slider.props.update({
            "type": "range",
            "min": str(min_val),
            "max": str(max_val),
            "value": str(default),
            "oninput": on_slider,
            "style": "flex:1;accent-color:#6366f1;cursor:pointer;",
        })

        # Number input — type exact value for precise adjustment
        num = to_component("", "input", no_closing_tag=True)
        num.id = input_id
        num.props.update({
            "type": "number",
            "min": str(min_val),
            "max": str(max_val),
            "value": str(default),
            "oninput": on_input,
            "onblur": on_input.replace("this.value", "this.value"),
        })
        num.style.update({
            "width": "62px",
            "padding": "4px 6px",
            "background": "rgba(255,255,255,0.05)",
            "border": "1px solid rgba(255,255,255,0.1)",
            "border-radius": "6px",
            "color": "#fff",
            "font-size": "0.75rem",
            "font-family": "monospace",
            "text-align": "center",
            "outline": "none",
        })

        group.add_children([lbl, slider, num])
        return group

    # Download bar
    def build_download_bar(self):
        """
        Builds the Download PNG button, hidden until a design is generated.
        """
        self.download_btn = to_component("⬇ Download PNG", "button")
        self.download_btn.id = "quill-download-btn"
        self.download_btn.props.update({
            "type": "button",
            "onclick": "quillDownload()",
        })
        self.download_btn.style.update({
            "display": "none",
            "padding": "12px 28px",
            "background": "linear-gradient(135deg, #6366f1, #4f46e5)",
            "color": "#fff",
            "border": "none",
            "border-radius": "10px",
            "font-size": "0.9rem",
            "font-weight": "700",
            "cursor": "pointer",
            "align-self": "flex-start",
            "font-family": "inherit",
            "letter-spacing": "0.02em",
        })
        self.add_child(self.download_btn)

    # Script
    def inject_script(self):
        """
        Injects the panel JavaScript into the page.
        """
        self.add_child(Script(inner_html=PANEL_SCRIPT))
