"""
BasePage — shared page shell for all Quill pages.

Handles global CSS, Prism.js, status strip JS, and all SEO in one
place. Subclasses override PAGE_* constants and get_json_ld() for
per-page customisation.
"""
from duck.shortcuts import resolve, static
from duck.utils.urlcrack import URL
from duck.html.components.page import Page
from duck.html.components.style import Style
from duck.html.components.script import Script
from duck.html.components import to_component


DUCK_HOMEPAGE = "https://duckframework.com"
DONATE_URL = f"{DUCK_HOMEPAGE}/contribute"
SITE_NAME = "Quill"
SITE_AUTHOR = "Duck Framework"
SITE_URL = "https://quill.duckframework.com"
GITHUB_URL = "https://github.com/duckframework/quill"


GLOBAL_STYLES = """
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
    background: #08080f;
    color: #fff;
    font-family: 'Syne', -apple-system, BlinkMacSystemFont, sans-serif;
    min-height: 100vh;
    overflow: hidden;
}

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.12); border-radius: 3px; }

input[type=range] { height: 4px; }
input[type=range]::-webkit-slider-thumb {
    width: 14px; height: 14px; border-radius: 50%;
    background: #6366f1; cursor: pointer;
}

textarea:focus, select:focus {
    border-color: rgba(99,102,241,0.5) !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.12);
}
textarea::placeholder { color: rgba(255,255,255,0.2); }

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.5; }
}

a { color: rgb(99, 102, 241);}

button:not(:disabled):hover { filter: brightness(1.1); }
button:disabled { opacity: 0.5; cursor: not-allowed !important; }

@media (max-width: 768px) {
    body { overflow: auto; }

    #quill-layout {
        flex-direction: column !important;
        height: auto !important;
        overflow: visible !important;
    }

    #quill-sidebar {
        width: 100% !important;
        border-right: none !important;
        border-bottom: 1px solid rgba(255,255,255,0.06) !important;
        padding: 24px 20px !important;
        overflow-y: visible !important;
        flex-shrink: 0 !important;
    }

    #quill-right {
        padding: 16px 20px !important;
        gap: 14px !important;
        overflow: visible !important;
        min-height: 60vh;
    }

    .quill-resize-row {
        flex-direction: column !important;
        gap: 10px !important;
    }

    #quill-download-btn {
        width: 100% !important;
        text-align: center !important;
    }
}

.github-cta {
    display: inline-block;
    padding: 10px 16px;
    background: var(--accent, rgba(99, 102, 241));
    color: white;
    border-radius: 8px;
    text-decoration: none;
    font-weight: 500;
    margin-top: 20px;
}

.github-cta:hover {
    opacity: 0.9;
}
"""

# Status strip JS — generating indicator and error feedback above the button
STATUS_SCRIPT = """
function quillSetGenerating() {
    var strip = document.getElementById('quill-status-strip');
    var icon  = document.getElementById('quill-status-icon');
    var text  = document.getElementById('quill-status-text');
    if (!strip) return;
    strip.style.display    = 'flex';
    strip.style.background = 'rgba(99,102,241,0.1)';
    strip.style.border     = '1px solid rgba(99,102,241,0.25)';
    strip.style.color      = '#a5b4fc';
    icon.innerHTML         = '&#9711;';
    icon.style.animation   = 'pulse 1s ease-in-out infinite';
    text.innerText         = 'Generating your design...';
}

function quillSetStatusError(message) {
    var strip = document.getElementById('quill-status-strip');
    var icon  = document.getElementById('quill-status-icon');
    var text  = document.getElementById('quill-status-text');
    if (!strip) return;
    strip.style.display    = 'flex';
    strip.style.background = 'rgba(248,113,113,0.08)';
    strip.style.border     = '1px solid rgba(248,113,113,0.25)';
    strip.style.color      = '#fca5a5';
    icon.innerHTML         = '&#9888;';
    icon.style.animation   = '';
    text.innerText         = message;
}

function quillClearStatus() {
    var strip = document.getElementById('quill-status-strip');
    if (strip) strip.style.display = 'none';
}
"""


class BasePage(Page):
    """
    Base page for all Quill pages.

    Injects global styles, Prism.js, status strip JS, and configures
    all SEO using Duck's built-in methods. Subclasses override PAGE_*
    constants and get_json_ld() for per-page customisation.
    """

    # Override in subclasses for per-page SEO
    PAGE_TITLE       = "Quill — AI Design Generator"
    PAGE_DESCRIPTION = (
        "Describe any design in plain English. Quill uses AI to generate "
        "a pixel-perfect HTML design you can download as a PNG instantly."
    )
    PAGE_TYPE = "website"
    PAGE_IMAGE = static("images/opengraph/og-image.png")
    PAGE_KEYWORDS    = [
        "AI design generator", "HTML design generator", "AI poster maker",
        "AI certificate generator", "AI social card generator",
        "duck framework", "python web app", "no javascript",
        "quill ai", "generate HTML design", "AI code card",
    ]

    def on_create(self):
        super().on_create()

        # Resolve canonical URL from request path
        self._path = getattr(self.request, "path", "/")
        self._home_url = resolve("home", absolute=True)
        self._page_url = URL(self._home_url).join(self._path).to_str()

        self.inject_styles()
        self.inject_prism()
        self.inject_status_script()
        self.inject_seo()

    def inject_styles(self):
        """
        Injects the global CSS shared across all pages.
        """
        self.add_to_head(Style(inner_html=GLOBAL_STYLES))

    def inject_prism(self):
        """
        Loads Prism.js for syntax highlighting in the HTML code editor.
        Loads core, markup, CSS, JS, and the markup-templating plugin
        so embedded CSS/JS inside <style>/<script> blocks are highlighted.
        """
        # Prism Tomorrow theme
        prism_css = to_component("", "link", no_closing_tag=True)
        prism_css.props.update({
            "rel": "stylesheet",
            "href": "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css",
        })
        self.add_to_head(prism_css)

        # Core engine
        prism_core = to_component("", "script", no_closing_tag=False)
        prism_core.props["src"] = "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-core.min.js"
        self.add_to_head(prism_core)

        # Language grammars — order matters
        for src in [
            "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-markup.min.js",
            "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-css.min.js",
            "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-javascript.min.js",
        ]:
            s = to_component("", "script", no_closing_tag=False)
            s.props["src"] = src
            self.add_to_head(s)

        # Autoloader for any additional grammars
        autoload = to_component("", "script", no_closing_tag=False)
        autoload.props.update({
            "src": "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/autoloader/prism-autoloader.min.js",
            "data-manual": "true",
        })
        self.add_to_head(autoload)

    def inject_status_script(self):
        """
        Injects the status strip helpers used by the prompt form handler.
        """
        self.add_to_body(Script(inner_html=STATUS_SCRIPT))

    def inject_seo(self):
        """
        Configures all SEO metadata using Duck's built-in SEO methods.
        """
        # Core meta
        self.set_lang("en")
        self.set_title(self.PAGE_TITLE)
        self.set_description(self.PAGE_DESCRIPTION)
        self.set_author(SITE_AUTHOR)
        self.set_robots("index, follow")
        self.set_keywords(self.PAGE_KEYWORDS)

        # Canonical
        self.set_canonical(self._page_url)

        # Open Graph
        self.set_opengraph(
            title=self.PAGE_TITLE,
            description=self.PAGE_DESCRIPTION,
            url=self._page_url,
            image=self.PAGE_IMAGE,
            type=self.PAGE_TYPE,
            site_name=SITE_NAME,
        )

        # Twitter Card
        self.set_twitter_card(
            card="summary_large_image",
            title=self.PAGE_TITLE,
            description=self.PAGE_DESCRIPTION,
            image=self.PAGE_IMAGE,
        )

        # JSON-LD structured data
        self.set_json_ld(self.get_json_ld())
        
        # Set favicons
        self.set_favicons([
             {
                "rel": "icon",
                "type": "image/png",
                "href": static("images/favicon_512.png"),
                "sizes": "512x512",
            },
            {
                "rel": "apple-touch-icon",
                "href": static("images/apple_touch.png"),
                "sizes": "180x180",
            },
            {
                "rel": "shortcut icon",
                "href": static("images/favicon.ico"),
            },
        ])

    def get_json_ld(self) -> dict:
        """
        Returns JSON-LD structured data for this page.
        Override in subclasses for page-specific schemas.
        """
        return {
            "@context": "https://schema.org",
            "@type": "WebApplication",
            "name": SITE_NAME,
            "url": self._page_url,
            "image": self.PAGE_IMAGE,
            "description": self.PAGE_DESCRIPTION,
            "applicationCategory": "DesignApplication",
            "operatingSystem": "All",
            "offers": {
                "@type": "Offer",
                "price": "0",
                "priceCurrency": "USD",
            },
            "author": {
                "@type": "Organization",
                "name": "Duck Framework",
                "url": DUCK_HOMEPAGE,
            },
        }
