"""Presentation for Setu, the local English–Bangla translator."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

HEADER = '''
<header class="setu-nav">
  <div class="setu-brand"><span class="brand-mark" aria-hidden="true">স</span>
    <div><strong>সেতু <span>SETU</span></strong><small>A bridge between languages</small></div>
  </div>
  <span class="local-badge"><i aria-hidden="true"></i> On your Mac</span>
</header>
<section class="setu-hero">
  <div class="hero-copy"><p class="eyebrow">ENGLISH &nbsp; / &nbsp; বাংলা</p>
    <h1>A little closer.<br><em>একটু কাছাকাছি।</em></h1>
    <p class="hero-description">Translate the words. Find the meaning.<br>Make yourself heard in English and Bangla.</p>
  </div>
  <div class="hero-art" aria-hidden="true"><div class="red-sun"></div>
    <span class="art-bangla">অ আ<br>ক খ</span><div class="stitch-line"></div>
    <span class="art-caption">WORDS THAT CONNECT US</span>
  </div>
</section>
'''

FOOTER = '''<footer class="setu-footer"><span>সেতু &nbsp; · &nbsp; Made for connection.</span>
<span>Local translation & audio &nbsp; / &nbsp; Inspired by Bangladesh</span></footer>'''


def theme():
    import gradio as gr
    return gr.themes.Base(primary_hue="emerald", neutral_hue="stone", radius_size="lg",
                          font=["-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"]).set(
        body_background_fill="#f6f4ee", body_background_fill_dark="#f6f4ee",
        body_text_color="#173e35", body_text_color_dark="#173e35",
        block_background_fill="#ffffff", block_background_fill_dark="#ffffff",
        input_background_fill="#ffffff", input_background_fill_dark="#ffffff",
        button_primary_background_fill="#006a50", button_primary_background_fill_dark="#006a50",
        button_primary_text_color="#ffffff", button_primary_text_color_dark="#ffffff",
    )
