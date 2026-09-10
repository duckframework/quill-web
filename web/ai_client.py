"""
Multi-provider async AI client for Quill.

Supports Anthropic, Google Gemini, Groq, and a built-in dummy
provider for testing without any API key.
"""
import re
import asyncio
import datetime

from typing import AsyncGenerator

from duck.settings import SETTINGS


# AI system prompt rules applied to every provider
BASE_RULES = """
CRITICAL RULES — follow every one without exception:
- Return ONLY a single complete HTML document. Nothing else. No explanation, no markdown, no code fences.
- The HTML must be fully self-contained — all CSS inside <style>, all JS inside <script>.
- Do NOT use external CDN links, image URLs, or any resource that requires a network request.
- Use only web-safe fonts OR embed a Google Fonts @import inside the <style> tag.
- The design must look stunning. Treat this as professional creative work.
- Every element must be visible and readable against its background.
- The root element should fill 100% of the viewport with no scrollbars.
- Make the designs look modern and attractive but don't do too much.
- Mix right colors in designs.
- I repeat, make the UI modern, slick and clean.
""".strip()

# System prompt per design type
SYSTEM_PROMPTS = {
    "poster": f"You are an expert graphic designer creating stunning posters and flyers as HTML. Use bold typography, rich gradients, dramatic layouts and strong visual hierarchy. Think concert posters, event flyers — vivid, eye-catching, professional.\n{BASE_RULES}",
    "code": f"You are a developer advocate creating beautiful code snippet showcase cards as HTML. Use dark themes, accurate syntax highlighting with span-based coloring, clean monospace fonts, subtle glow effects, a filename tab, line numbers, and a language badge.\n{BASE_RULES}",
    "social": f"You are a social media designer creating scroll-stopping cards as HTML. Bold, modern, optimised for sharing. Think Twitter/LinkedIn cards, quote graphics, announcement posts.\n{BASE_RULES}",
    "certificate": f"You are a formal document designer creating elegant certificates as HTML. Use classic serif typography, decorative borders, gold/cream/navy palettes, official seals, and a sense of prestige.\n{BASE_RULES}",
    "custom": f"You are a world-class creative designer. Interpret the prompt freely and produce the most visually impressive HTML design possible.\n{BASE_RULES}",
    "opengraph": f"You are an expert Open Graph image designer. Create stunning 1200x630px HTML cards for social media sharing. The design must be exactly 1200px wide and 630px tall, with no scrollbars. Use bold typography, strong visual hierarchy, a compelling headline, a short tagline, a domain/brand name, and an accent colour that complements the content. Avoid clutter — every element must breathe. Think Twitter cards, LinkedIn posts, Discord embeds.\n{BASE_RULES}",
}

# Pre-built demo designs streamed chunk by chunk when dummy mode is on
DUMMY_DESIGNS = {
    "poster": """<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;700&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;overflow:hidden}
body{
  background:linear-gradient(135deg,#0d0221 0%,#1a0533 40%,#2d0b5a 100%);
  display:flex;align-items:center;justify-content:center;
  font-family:'Inter',sans-serif;
}
.poster{
  width:100%;height:100%;display:flex;flex-direction:column;
  align-items:center;justify-content:center;padding:40px;
  position:relative;overflow:hidden;
}
.poster::before{
  content:'';position:absolute;top:-200px;left:-200px;
  width:600px;height:600px;
  background:radial-gradient(circle,rgba(139,92,246,.35),transparent 70%);
}
.poster::after{
  content:'';position:absolute;bottom:-200px;right:-200px;
  width:600px;height:600px;
  background:radial-gradient(circle,rgba(236,72,153,.25),transparent 70%);
}
.eyebrow{font-size:.75rem;letter-spacing:.4em;text-transform:uppercase;color:rgba(167,139,250,.8);margin-bottom:16px;position:relative;z-index:1;}
h1{font-family:'Bebas Neue',sans-serif;font-size:clamp(3rem,10vw,7rem);letter-spacing:.05em;text-align:center;line-height:.9;position:relative;z-index:1;background:linear-gradient(135deg,#fff 30%,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.sub{font-size:1rem;color:rgba(255,255,255,.5);margin-top:20px;letter-spacing:.1em;text-transform:uppercase;position:relative;z-index:1;}
.date-box{margin-top:32px;padding:10px 28px;border:1px solid rgba(167,139,250,.4);border-radius:99px;font-size:.85rem;color:#a78bfa;letter-spacing:.15em;text-transform:uppercase;position:relative;z-index:1;}
.line{width:60px;height:2px;background:#a78bfa;margin:24px auto;opacity:.4}
.acts{display:flex;gap:24px;flex-wrap:wrap;justify-content:center;position:relative;z-index:1;}
.act{font-size:.9rem;color:rgba(255,255,255,.6);letter-spacing:.08em}
</style></head><body>
<div class="poster">
  <div class="eyebrow">✦ Quill Demo — Poster</div>
  <h1>Neon<br>Festival</h1>
  <div class="sub">A showcase of AI-generated design</div>
  <div class="line"></div>
  <div class="date-box">March 2026 · Lagos, Nigeria</div>
  <div class="acts" style="margin-top:20px">
    <span class="act">Duck Framework</span>
    <span class="act">·</span>
    <span class="act">Lively UI</span>
    <span class="act">·</span>
    <span class="act">Pure Python</span>
  </div>
</div>
</body></html>""",

    "code": """<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@500;600&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;overflow:hidden}
body{background:#0d1117;display:flex;align-items:center;justify-content:center;font-family:'Inter',sans-serif;padding:32px;}
.card{width:100%;max-width:680px;border-radius:14px;overflow:hidden;border:1px solid rgba(255,255,255,.08);box-shadow:0 24px 80px rgba(0,0,0,.6);}
.toolbar{background:#161b22;padding:12px 18px;display:flex;align-items:center;gap:8px;border-bottom:1px solid rgba(255,255,255,.06);}
.dot{width:12px;height:12px;border-radius:50%}
.filename{margin-left:8px;font-size:.78rem;color:rgba(255,255,255,.4);font-family:'JetBrains Mono',monospace;}
.lang-badge{margin-left:auto;font-size:.65rem;font-weight:600;background:rgba(99,102,241,.2);color:#818cf8;padding:2px 8px;border-radius:4px;letter-spacing:.05em;}
.code-body{background:#0d1117;padding:20px 0;display:flex;overflow:hidden;}
.ln-col{padding:0 16px;display:flex;flex-direction:column;border-right:1px solid rgba(255,255,255,.05);min-width:48px;}
.ln{font-family:'JetBrains Mono',monospace;font-size:.78rem;color:rgba(255,255,255,.18);line-height:1.75;text-align:right;}
.code{flex:1;padding:0 20px;font-family:'JetBrains Mono',monospace;font-size:.8rem;line-height:1.75;overflow:hidden}
.cl{display:block;white-space:pre}
.kw{color:#ff7b72}.fn{color:#d2a8ff}.st{color:#a5d6ff}.cm{color:#8b949e}.pl{color:#e6edf3}.nm{color:#f0883e}
</style></head><body>
<div class="card">
  <div class="toolbar">
    <div class="dot" style="background:#ff5f57"></div>
    <div class="dot" style="background:#febc2e"></div>
    <div class="dot" style="background:#28c840"></div>
    <span class="filename">quicksort.py</span>
    <span class="lang-badge">Python</span>
  </div>
  <div class="code-body">
    <div class="ln-col">
      <div class="ln">1</div><div class="ln">2</div><div class="ln">3</div>
      <div class="ln">4</div><div class="ln">5</div><div class="ln">6</div>
      <div class="ln">7</div><div class="ln">8</div><div class="ln">9</div>
    </div>
    <div class="code">
      <span class="cl"><span class="cm"># Quill Demo — Code Snippet</span></span>
      <span class="cl"> </span>
      <span class="cl"><span class="kw">def </span><span class="fn">quicksort</span><span class="pl">(arr: </span><span class="fn">list</span><span class="pl">) -> </span><span class="fn">list</span><span class="pl">:</span></span>
      <span class="cl"><span class="pl">    </span><span class="kw">if </span><span class="fn">len</span><span class="pl">(arr) <= </span><span class="nm">1</span><span class="pl">:</span></span>
      <span class="cl"><span class="pl">        </span><span class="kw">return </span><span class="pl">arr</span></span>
      <span class="cl"><span class="pl">    pivot = arr[</span><span class="nm">len</span><span class="pl">(arr) // </span><span class="nm">2</span><span class="pl">]</span></span>
      <span class="cl"><span class="pl">    left  = [x </span><span class="kw">for </span><span class="pl">x </span><span class="kw">in </span><span class="pl">arr </span><span class="kw">if </span><span class="pl">x < pivot]</span></span>
      <span class="cl"><span class="pl">    mid   = [x </span><span class="kw">for </span><span class="pl">x </span><span class="kw">in </span><span class="pl">arr </span><span class="kw">if </span><span class="pl">x == pivot]</span></span>
      <span class="cl"><span class="pl">    right = [x </span><span class="kw">for </span><span class="pl">x </span><span class="kw">in </span><span class="pl">arr </span><span class="kw">if </span><span class="pl">x > pivot]</span></span>
      <span class="cl"><span class="pl">    </span><span class="kw">return </span><span class="fn">quicksort</span><span class="pl">(left) + mid + </span><span class="fn">quicksort</span><span class="pl">(right)</span></span>
    </div>
  </div>
</div>
</body></html>""",

    "social": """<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Inter:wght@400;500&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;overflow:hidden}
body{background:#000;display:flex;align-items:center;justify-content:center;}
.card{width:100%;height:100%;background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);display:flex;flex-direction:column;align-items:center;justify-content:center;padding:48px;text-align:center;position:relative;overflow:hidden;}
.accent{position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,#6366f1,#8b5cf6,#ec4899);}
.badge{font-family:'Inter',sans-serif;font-size:.72rem;letter-spacing:.15em;text-transform:uppercase;color:#818cf8;margin-bottom:20px;}
h2{font-family:'Syne',sans-serif;font-size:clamp(1.8rem,5vw,3rem);font-weight:800;letter-spacing:-.03em;color:#fff;line-height:1.1;max-width:500px;}
.sub{font-family:'Inter',sans-serif;font-size:1rem;color:rgba(255,255,255,.45);margin-top:16px;max-width:400px;line-height:1.6;}
.footer{position:absolute;bottom:28px;display:flex;align-items:center;gap:10px;font-family:'Inter',sans-serif;font-size:.78rem;color:rgba(255,255,255,.3);}
.avatar{width:28px;height:28px;border-radius:50%;background:linear-gradient(135deg,#6366f1,#ec4899);display:flex;align-items:center;justify-content:center;font-size:.7rem;color:#fff;font-weight:700;}
</style></head><body>
<div class="card">
  <div class="accent"></div>
  <div class="badge">✦ Quill Demo — Social Card</div>
  <h2>Built with Duck Framework. No JavaScript. Pure Python.</h2>
  <div class="sub">This card was generated in seconds by an AI model streaming HTML token by token.</div>
  <div class="footer">
    <div class="avatar">Q</div>
    <span>quill.duckframework.com · AI Design Generator</span>
  </div>
</div>
</body></html>""",

    "certificate": """<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Inter:wght@300;400;500&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;overflow:hidden}
body{background:#f9f5e9;display:flex;align-items:center;justify-content:center;font-family:'Inter',sans-serif;}
.cert{width:90%;max-width:700px;background:#fffef7;border:12px double #c9a84c;padding:48px 56px;text-align:center;position:relative;box-shadow:0 8px 40px rgba(0,0,0,.12);}
.cert::before,.cert::after{content:'✦';position:absolute;font-size:1.5rem;color:#c9a84c;opacity:.4;}
.cert::before{top:16px;left:20px}
.cert::after{bottom:16px;right:20px}
.eyebrow{font-size:.7rem;letter-spacing:.3em;text-transform:uppercase;color:#c9a84c;margin-bottom:20px;}
h1{font-family:'Playfair Display',serif;font-size:2.4rem;color:#2d1f00;margin-bottom:8px;}
.awarded{font-size:.85rem;color:#888;letter-spacing:.05em;margin-bottom:28px}
.name{font-family:'Playfair Display',serif;font-style:italic;font-size:2rem;color:#4a3200;border-bottom:1px solid #c9a84c;display:inline-block;padding-bottom:6px;margin-bottom:28px;}
.desc{font-size:.88rem;color:#666;line-height:1.7;max-width:460px;margin:0 auto}
.footer{margin-top:32px;display:flex;justify-content:space-between;font-size:.75rem;color:#999;border-top:1px solid #e8d8a0;padding-top:16px;}
.seal{width:56px;height:56px;border-radius:50%;background:linear-gradient(135deg,#c9a84c,#f0d060);display:flex;align-items:center;justify-content:center;font-size:1.4rem;margin:0 auto 24px;}
</style></head><body>
<div class="cert">
  <div class="seal">🏆</div>
  <div class="eyebrow">Certificate of Achievement</div>
  <h1>Duck Framework</h1>
  <div class="awarded">This certificate is proudly awarded to</div>
  <div class="name">Brian Musakwa</div>
  <div class="desc">In recognition of creating and maintaining Duck Framework — an open-source Python web framework powering real-time reactive UIs without JavaScript.</div>
  <div class="footer">
    <span>March 2026</span>
    <span>Quill Demo Certificate</span>
    <span>duckframework.com</span>
  </div>
</div>
</body></html>""",

    "opengraph": """<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Mono:wght@400;500&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1200px;height:630px;overflow:hidden}
body{background:#0d0d14;font-family:'Syne',sans-serif;position:relative;}
body::before{content:'';position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,0.025) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.025) 1px,transparent 1px);background-size:48px 48px;}
.glow{position:absolute;top:-100px;left:-80px;width:500px;height:500px;background:radial-gradient(ellipse,rgba(99,102,241,0.12) 0%,transparent 65%);}
.glow2{position:absolute;bottom:-100px;right:-60px;width:420px;height:420px;background:radial-gradient(ellipse,rgba(139,92,246,0.08) 0%,transparent 65%);}
.wrap{position:relative;z-index:1;width:100%;height:100%;display:flex;flex-direction:column;justify-content:space-between;padding:52px 64px 48px;}
.top{display:flex;align-items:center;justify-content:space-between;}
.logo{display:flex;align-items:center;gap:10px;font-family:'DM Mono',monospace;font-size:1rem;color:#f0f0f0;}
.logo-dot{width:9px;height:9px;border-radius:50%;background:#6366f1;}
.badge{font-family:'DM Mono',monospace;font-size:0.7rem;color:#818cf8;background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.22);padding:6px 16px;border-radius:99px;letter-spacing:.12em;text-transform:uppercase;}
.hero{flex:1;display:flex;flex-direction:column;justify-content:center;gap:16px;}
.kicker{font-family:'DM Mono',monospace;font-size:0.72rem;letter-spacing:.18em;text-transform:uppercase;color:#6366f1;display:flex;align-items:center;gap:10px;}
.kicker::before{content:'';display:inline-block;width:24px;height:1px;background:#6366f1;}
h1{font-size:4.2rem;font-weight:800;line-height:1.0;letter-spacing:-0.03em;color:#fff;}
h1 span{background:linear-gradient(90deg,#818cf8,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.desc{font-size:1.05rem;color:rgba(240,240,240,0.4);max-width:560px;line-height:1.6;}
.bottom{display:flex;align-items:center;justify-content:space-between;}
.url{font-family:'DM Mono',monospace;font-size:0.78rem;color:rgba(240,240,240,0.3);}
.powered{font-family:'DM Mono',monospace;font-size:0.7rem;color:rgba(240,240,240,0.22);letter-spacing:.05em;text-align:right;line-height:1.6;}
.powered strong{color:rgba(240,240,240,0.5);}
</style></head><body>
<div class="glow"></div><div class="glow2"></div>
<div class="wrap">
  <div class="top">
    <div class="logo"><div class="logo-dot"></div>quill/</div>
    <div class="badge">✦ OG Image Demo</div>
  </div>
  <div class="hero">
    <div class="kicker">Open Graph Image</div>
    <h1>Share anything.<br><span>Look great.</span></h1>
    <div class="desc">Generate stunning 1200×630 Open Graph images for any website, product, or post. Perfect for Twitter, LinkedIn, and Discord embeds.</div>
  </div>
  <div class="bottom">
    <div class="url">quill.duckframework.com</div>
    <div class="powered"><strong>Duck Framework</strong><br>Pure Python · No JavaScript</div>
  </div>
</div>
</body></html>""",
    "opengraph": """<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Mono:wght@400;500&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1200px;height:630px;overflow:hidden}
body{background:#0d0d14;font-family:'Syne',sans-serif;position:relative;}
body::before{content:'';position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,0.025) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.025) 1px,transparent 1px);background-size:48px 48px;}
.glow{position:absolute;top:-100px;left:-80px;width:500px;height:500px;background:radial-gradient(ellipse,rgba(99,102,241,0.12) 0%,transparent 65%);}
.glow2{position:absolute;bottom:-100px;right:-60px;width:420px;height:420px;background:radial-gradient(ellipse,rgba(139,92,246,0.08) 0%,transparent 65%);}
.wrap{position:relative;z-index:1;width:100%;height:100%;display:flex;flex-direction:column;justify-content:space-between;padding:52px 64px 48px;}
.top{display:flex;align-items:center;justify-content:space-between;}
.logo{display:flex;align-items:center;gap:10px;font-family:'DM Mono',monospace;font-size:1rem;color:#f0f0f0;}
.logo-dot{width:9px;height:9px;border-radius:50%;background:#6366f1;}
.badge{font-family:'DM Mono',monospace;font-size:0.7rem;color:#818cf8;background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.22);padding:6px 16px;border-radius:99px;letter-spacing:.12em;text-transform:uppercase;}
.hero{flex:1;display:flex;flex-direction:column;justify-content:center;gap:16px;}
.kicker{font-family:'DM Mono',monospace;font-size:0.72rem;letter-spacing:.18em;text-transform:uppercase;color:#6366f1;display:flex;align-items:center;gap:10px;}
.kicker::before{content:'';display:inline-block;width:24px;height:1px;background:#6366f1;}
h1{font-size:4.2rem;font-weight:800;line-height:1.0;letter-spacing:-0.03em;color:#fff;}
h1 span{background:linear-gradient(90deg,#818cf8,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.desc{font-size:1.05rem;color:rgba(240,240,240,0.4);max-width:560px;line-height:1.6;}
.bottom{display:flex;align-items:center;justify-content:space-between;}
.url{font-family:'DM Mono',monospace;font-size:0.78rem;color:rgba(240,240,240,0.3);}
.powered{font-family:'DM Mono',monospace;font-size:0.7rem;color:rgba(240,240,240,0.22);letter-spacing:.05em;text-align:right;line-height:1.6;}
.powered strong{color:rgba(240,240,240,0.5);}
</style></head><body>
<div class="glow"></div><div class="glow2"></div>
<div class="wrap">
  <div class="top">
    <div class="logo"><div class="logo-dot"></div>quill/</div>
    <div class="badge">✦ OG Image Demo</div>
  </div>
  <div class="hero">
    <div class="kicker">Open Graph Image</div>
    <h1>Share anything.<br><span>Look great.</span></h1>
    <div class="desc">Generate stunning 1200&#xd7;630 Open Graph images for any website, product, or post. Perfect for Twitter, LinkedIn, and Discord embeds.</div>
  </div>
  <div class="bottom">
    <div class="url">quill.duckframework.com</div>
    <div class="powered"><strong>Duck Framework</strong><br>Pure Python &middot; No JavaScript</div>
  </div>
</div>
</body></html>""",
        "custom": """<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:100%;overflow:hidden}
body{background:#08080f;display:flex;align-items:center;justify-content:center;font-family:'Syne',sans-serif;}
.wrap{width:100%;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:48px;position:relative;overflow:hidden;}
.glow{position:absolute;width:500px;height:500px;border-radius:50%;background:radial-gradient(circle,rgba(99,102,241,.2),transparent 70%);top:50%;left:50%;transform:translate(-50%,-50%);}
.badge{font-size:.7rem;letter-spacing:.2em;text-transform:uppercase;color:#6366f1;background:rgba(99,102,241,.1);border:1px solid rgba(99,102,241,.25);padding:4px 14px;border-radius:99px;margin-bottom:20px;position:relative;z-index:1;}
h1{font-size:clamp(2rem,6vw,4rem);font-weight:800;letter-spacing:-.04em;text-align:center;background:linear-gradient(135deg,#fff 40%,rgba(255,255,255,.4));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1.1;position:relative;z-index:1;}
.sub{font-size:1rem;color:rgba(255,255,255,.35);margin-top:16px;text-align:center;max-width:480px;line-height:1.6;position:relative;z-index:1;}
</style></head><body>
<div class="wrap">
  <div class="glow"></div>
  <div class="badge">✦ Quill Demo — Custom Design</div>
  <h1>Describe Anything.<br>Get a Design.</h1>
  <div class="sub">This is a demo design. Enable live mode and add your API key to generate real AI designs.</div>
</div>
</body></html>""",
}


class RateLimitError(Exception):
    """
    Raised when a provider returns a rate limit response.

    Attributes:
        provider:    Name of the provider e.g. "Gemini".
        reset_time:  Human-readable reset time string, or None.
        retry_after: Seconds until reset, or None.
    """
    def __init__(self, provider: str, reset_time: str | None = None, retry_after: int | None = None):
        self.provider    = provider
        self.reset_time  = reset_time
        self.retry_after = retry_after
        super().__init__(f"Rate limit reached on {provider}")


class InsufficientCreditsError(Exception):
    """
    Raised when a provider returns an insufficient credits response.

    Attributes:
        provider: Name of the provider e.g. "Gemini".
    """
    def __init__(self, provider: str):
        self.provider = provider
        super().__init__(f"Insufficient AI credits on {provider}")


class MissingApiKeyError(Exception):
    """
    Raised when the required API key for a provider is not available.
    """
    def __init__(self, provider: str):
        self.provider = provider
        super().__init__(f"{provider} is currently unavailable")


def format_reset_time(seconds: int | None) -> str | None:
    """
    Converts a retry-after seconds value to a human-readable string.

    Args:
        seconds: Number of seconds until reset, or None.

    Returns:
        A readable string like "2 minutes", or None if seconds is None.
    """
    if seconds is None:
        return None
    
    if seconds < 60:
        return f"{seconds} seconds"
    
    if seconds < 3600:
        return f"{seconds // 60} minutes"
    
    return f"{seconds // 3600} hours"


def is_insufficient_credits(msg: str) -> bool:
    """
    Checks a message indicates an insufficient credits message.
    """
    msg = msg.lower()
    return any(keyword in msg for keyword in [
        "credit", "balance", "insufficient", "billing", "quota exceeded"
    ])


async def stream_dummy(design_type: str, prompt: str) -> AsyncGenerator[str, None]:
    """
    Streams a pre-built HTML design chunk by chunk to simulate real streaming.
    Used when dummy mode is active — no API key needed.

    Args:
        design_type: One of: poster, code, social, certificate, custom.
        prompt: Ignored in dummy mode, present for signature compatibility.
    """
    html = DUMMY_DESIGNS.get(design_type, DUMMY_DESIGNS["custom"])

    # Stream in 80-char chunks with a small delay to simulate real streaming
    chunk_size = 80
    
    for i in range(0, len(html), chunk_size):
        yield html[i:i + chunk_size]
        await asyncio.sleep(0.02)


async def stream_anthropic(model: str, system: str, prompt: str) -> AsyncGenerator[str, None]:
    """
    Streams from Anthropic Claude using the async client.

    Args:
        model: The Anthropic model ID string.
        system: The system prompt.
        prompt: The user prompt.
    """
    import anthropic

    # Check API key
    key = SETTINGS.get("ANTHROPIC_API_KEY", "")
    
    if not key:
        raise MissingApiKeyError("Anthropic")

    client = anthropic.AsyncAnthropic(api_key=key)

    try:
        async with client.messages.stream(
            model=model,
            max_tokens=SETTINGS.get("QUILL_MAX_TOKENS", 4096),
            system=system,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    except anthropic.BadRequestError as e:
        if is_insufficient_credits(str(e)):
            raise InsufficientCreditsError(provider="Claude (Anthropic)") from e
        raise
       
    except anthropic.RateLimitError as e:
        raise RateLimitError(
            provider="Claude (Anthropic)",
            reset_time="about 1 minute",
            retry_after=60,
        ) from e


async def stream_gemini(model: str, system: str, prompt: str) -> AsyncGenerator[str, None]:
    """
    Streams from Google Gemini using the async generate API.

    Args:
        model: The Gemini model ID string.
        system: The system prompt.
        prompt: The user prompt.
    """
    from google import genai
    from google.genai import types

    # Check API key
    key = SETTINGS.get("GEMINI_API_KEY", "")

    if not key:
        raise MissingApiKeyError("Gemini")

    # Create client
    client = genai.Client(api_key=key)

    try:
        stream = await client.aio.models.generate_content_stream(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=SETTINGS.get("QUILL_MAX_TOKENS", 4096),
            ),
        )

        async for chunk in stream:
            if chunk.text:
                yield chunk.text

    except Exception as e:
        msg = str(e).lower()

        # Detect insufficient credits error
        if is_insufficient_credits(str(e)):
            raise InsufficientCreditsError(provider="Gemini")

        # Detect quota / rate limit errors
        if "quota" in msg or "429" in msg or "rate" in msg:
            now_utc = datetime.datetime.utcnow()
            midnight = (now_utc + datetime.timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            # Get delta secs
            delta_secs = int((midnight - now_utc).total_seconds())

            # Raise rate limit error
            raise RateLimitError(
                provider="Gemini Flash (Google)",
                reset_time=f"midnight UTC — in about {format_reset_time(delta_secs)}",
                retry_after=delta_secs,
            ) from e
        raise


async def stream_groq(model: str, system: str, prompt: str) -> AsyncGenerator[str, None]:
    """
    Streams from Groq using the async client.

    Args:
        model:  The Groq model ID string.
        system: The system prompt.
        prompt: The user prompt.
    """
    import groq
    
    # Check API key
    key = SETTINGS.get("GROQ_API_KEY", "")
    
    if not key:
        raise MissingApiKeyError("Groq")

    # Initialize the client.
    client = groq.AsyncGroq(api_key=key)

    try:
        stream = await client.chat.completions.create(
            model=model,
            max_tokens=SETTINGS.get("QUILL_MAX_TOKENS", 4096),
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
            stream=True,
        )
        
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    except groq.BadRequestError as e:
        # Select model label
        model_label = "Llama 3" if "llama" in model.lower() else "Mixtral"
        
        if is_insufficient_credits(str(e)):
            raise InsufficientCreditsError(provider=f"{modal_label} (Groq)") from e
        raise
       
    except groq.RateLimit as e:
        retry_after = None
        reset_str   = None

        # Parse retry time from the error message if available
        raw = str(e)
        match = re.search(r"try again in (\d+\.?\d*)(s|m)", raw, re.IGNORECASE)
        
        if match:
            value = float(match.group(1))
            unit = match.group(2).lower()
            retry_after = int(value * 60 if unit == "m" else value)
            reset_str = format_reset_time(retry_after)

        # Select model label
        model_label = "Llama 3" if "llama" in model.lower() else "Mixtral"
        
        raise RateLimitError(
            provider=f"{model_label} (Groq)",
            reset_time=reset_str,
            retry_after=retry_after,
        ) from e


def get_provider(model_id: str) -> str:
    """
    Returns the provider name for a given model ID from QUILL_MODELS.

    Args:
        model_id: The model ID string to look up.

    Returns:
        Provider name string, defaulting to "anthropic" if not found.
    """
    for mid, _, provider in SETTINGS.get("QUILL_MODELS", []):
        if mid == model_id:
            return provider
    return "anthropic"


async def stream_design(
    prompt: str,
    design_type: str,
    model_id: str,
    force_dummy: bool = False,
) -> AsyncGenerator[str, None]:
    """
    Streams HTML chunks for the given prompt and design type.

    Routes to the correct provider based on model_id, or uses the dummy
    provider if force_dummy is True or QUILL_DUMMY_MODE is set in settings.

    Args:
        prompt: The user's design description.
        design_type: One of: poster, code, social, certificate, custom.
        model_id: The model ID string from QUILL_MODELS.
        force_dummy: If True, use dummy mode regardless of settings.

    Yields:
        str: Partial HTML text chunks as they arrive.

    Raises:
        RateLimitError: When the provider's rate limit is hit.
        MissingApiKeyError: When the required API key is not configured.
    """
    # Use dummy mode if forced from the UI or set in settings
    if force_dummy or SETTINGS.get("QUILL_DUMMY_MODE", False):
        async for chunk in stream_dummy(design_type, prompt):
            yield chunk
        return

    # Resolve provider and system prompt
    system   = SYSTEM_PROMPTS.get(design_type, SYSTEM_PROMPTS["custom"])
    provider = get_provider(model_id)

    # Map provider names to their streaming functions
    providers = {
        "anthropic": stream_anthropic,
        "gemini": stream_gemini,
        "groq": stream_groq,
    }
    
    # Get provider function
    fn = providers.get(provider)
    
    if fn is None:
        raise ValueError(f"Unknown provider: {provider}")

    async for chunk in fn(model_id, system, prompt):
        yield chunk
