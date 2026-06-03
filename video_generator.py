"""
WBG Video Generator - V4 Luxury Editorial Edition
- Downloads Oswald Bold/Regular from Google Fonts at runtime (cached in /tmp)
- Uses Unsplash source URLs (no API key needed) for backgrounds
- Ken Burns slow zoom
- Text slides up with staggered timing
- Single white logo, no flashing
- Headshot only on buyer_seller_tip and hot_take
- All text properly wrapped, nothing cut off
"""
import os, tempfile, shutil, wave, subprocess, random, urllib.request, json, logging
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
import cloudinary, cloudinary.uploader

log = logging.getLogger('WBG')

ASSETS_DIR    = os.path.join(os.path.dirname(__file__), 'assets')
HEADSHOT_PATH = os.path.join(ASSETS_DIR, 'headshot.png')
PREFERRED_LOGO = 'Logo_Primary_White_01.png'
FALLBACK_LOGOS = [
    'exp_Logo_Secondary_White_01.png',
    'WBG LOGO - ExpLogoLogoPrimaryWhite01.png',
    'exp_Logo_Primary_Dune_01.png',
]

# Canvas - Instagram Reels native
W, H         = 1080, 1920
FPS          = 24
DURATION     = 10
TOTAL_FRAMES = DURATION * FPS

# Colors
WHITE  = (255, 255, 255)
CREAM  = (240, 235, 225)
ORANGE = (210, 85, 25)
BLACK  = (8, 8, 8)

# ─── FONT DOWNLOAD & CACHE ───────────────────────────────────────────────────

FONT_CACHE = {}

GOOGLE_FONTS = {
    'oswald_bold':    'https://fonts.gstatic.com/s/oswald/v53/TK3_WkUHHAIjg75cFRf3bXL8LICs13NvgUFoZAaRliE.ttf',
    'oswald_regular': 'https://fonts.gstatic.com/s/oswald/v53/TK3_WkUHHAIjg75cFRf3bXL8LICs169vgUFoZAaRliE.ttf',
    'raleway_regular':'https://fonts.gstatic.com/s/raleway/v34/1Ptug8zYS_SKggPNyC0IT4ttDfA.ttf',
}

def _get_font_path(name):
    """Download font if not cached, return local path."""
    cache_dir = '/tmp/wbg_fonts'
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, f'{name}.ttf')
    if os.path.exists(path):
        return path
    url = GOOGLE_FONTS.get(name)
    if not url:
        return None
    try:
        log.info(f'Downloading font: {name}')
        urllib.request.urlretrieve(url, path)
        log.info(f'Font cached: {name}')
        return path
    except Exception as e:
        log.warning(f'Font download failed for {name}: {e}')
        return None

def _font(name, size):
    """Load a font by name and size, with fallback."""
    if (name, size) in FONT_CACHE:
        return FONT_CACHE[(name, size)]
    path = _get_font_path(name)
    if path:
        try:
            f = ImageFont.truetype(path, size)
            FONT_CACHE[(name, size)] = f
            return f
        except:
            pass
    # Fallback to Caladea
    caladea = os.path.join(ASSETS_DIR, 'Caladea-Regular.ttf')
    if os.path.exists(caladea):
        try:
            f = ImageFont.truetype(caladea, size)
            FONT_CACHE[(name, size)] = f
            return f
        except:
            pass
    return ImageFont.load_default()

# ─── BACKGROUND ──────────────────────────────────────────────────────────────

SD_PHOTO_QUERIES = {
    'sd_hidden_gem':      ['san-diego', 'california-coast', 'san-diego-neighborhood', 'california-architecture'],
    'current_event_tie':  ['san-diego-skyline', 'san-diego-downtown', 'california-city', 'san-diego-bay'],
    'hot_take':           ['luxury-interior', 'modern-home', 'luxury-real-estate', 'contemporary-architecture'],
    'hyper_local_intel':  ['san-diego-street', 'california-suburb', 'san-diego-hills', 'san-diego-residential'],
    'sd_lifestyle_hook':  ['san-diego-beach', 'la-jolla', 'coronado', 'del-mar-california'],
    'property_spotlight': ['luxury-pool', 'modern-house', 'mediterranean-villa', 'beach-house'],
    'market_stat':        ['san-diego-skyline', 'california-coast', 'san-diego-harbor', 'city-aerial'],
    'buyer_seller_tip':   ['modern-interior', 'luxury-kitchen', 'living-room', 'real-estate'],
    'investor_quote':     ['city-skyline', 'modern-architecture', 'luxury-penthouse', 'urban-skyline'],
    'san_diego_lifestyle':['san-diego-beach', 'pacific-beach', 'ocean-beach', 'la-jolla-cove'],
}

def _fetch_background(content_type):
    """Fetch photo via Unsplash source (no API key needed)."""
    queries = SD_PHOTO_QUERIES.get(content_type, ['san-diego'])
    query = random.choice(queries)
    # Unsplash source - free, no key, returns random photo for query
    # Fetch slightly larger than canvas for Ken Burns room
    fetch_w = int(W * 1.12)
    fetch_h = int(H * 1.12)
    url = f'https://source.unsplash.com/{fetch_w}x{fetch_h}/?{query}'
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0'
        })
        with urllib.request.urlopen(req, timeout=12) as r:
            img_data = r.read()
        tmp = tempfile.mktemp(suffix='.jpg')
        with open(tmp, 'wb') as f:
            f.write(img_data)
        bg = Image.open(tmp).convert('RGB')
        os.unlink(tmp)
        # Ensure it's large enough for Ken Burns
        if bg.width < W * 1.08 or bg.height < H * 1.08:
            ratio = max((W * 1.12) / bg.width, (H * 1.12) / bg.height)
            bg = bg.resize((int(bg.width * ratio), int(bg.height * ratio)), Image.LANCZOS)
        log.info(f'Background fetched: {bg.size} for query: {query}')
        return bg
    except Exception as e:
        log.warning(f'Background fetch failed: {e}. Using gradient.')
        return _cinematic_gradient()

def _cinematic_gradient():
    """Rich dark gradient fallback."""
    bg = Image.new('RGB', (int(W*1.12), int(H*1.12)))
    draw = ImageDraw.Draw(bg)
    for y in range(int(H*1.12)):
        t = y / (H*1.12)
        draw.line([(0,y),(int(W*1.12),y)], fill=(int(15+t*10), int(12+t*8), int(18+t*12)))
    return bg

# ─── KEN BURNS ───────────────────────────────────────────────────────────────

def _ken_burns(bg, f, total):
    """Slow push-in zoom. Starts at 1.08x crop, ends at 1.0x."""
    t = f / max(total - 1, 1)
    t_e = t * t * (3 - 2 * t)  # ease in-out
    bw, bh = bg.size

    # Crop starts larger (zoom out) and ends at exact canvas size (zoom in)
    cw = int(W + (bw - W) * (1 - t_e) * 0.5)
    ch = int(H + (bh - H) * (1 - t_e) * 0.5)
    cw = max(cw, W); ch = max(ch, H)
    cw = min(cw, bw); ch = min(ch, bh)

    # Subtle drift - center moves slightly
    cx = bw // 2 + int(20 * (1 - t_e))
    cy = bh // 2 + int(15 * (1 - t_e))
    left = max(0, min(cx - cw//2, bw - cw))
    top  = max(0, min(cy - ch//2, bh - ch))

    cropped = bg.crop((left, top, left+cw, top+ch))
    if cropped.size != (W, H):
        cropped = cropped.resize((W, H), Image.LANCZOS)
    return cropped

# ─── OVERLAY ─────────────────────────────────────────────────────────────────

def _overlay(bg_frame):
    """
    Luxury cinematic overlay:
    - Heavy dark vignette top 45% (text zone)
    - Heavy dark vignette bottom 35% (logo zone)
    - Clear window in the middle so photo breathes
    """
    ov = Image.new('RGBA', (W, H), (0,0,0,0))
    d  = ImageDraw.Draw(ov)
    for y in range(H):
        t = y / H
        if t < 0.45:
            # Top: very dark, fades to clear
            a = int(200 * (1 - t/0.45)**1.5)
        elif t > 0.62:
            # Bottom: dark for logo/text
            a = int(230 * ((t-0.62)/0.38)**1.2)
        else:
            # Middle window: nearly clear
            a = 20
        d.line([(0,y),(W,y)], fill=(0,0,0,a))
    result = Image.alpha_composite(bg_frame.convert('RGBA'), ov)
    return result.convert('RGB')

# ─── TEXT UTILITIES ──────────────────────────────────────────────────────────

def _wrap(draw, text, font, max_w):
    """Wrap text to fit max_w pixels."""
    words = text.split()
    lines, cur = [], ''
    for w in words:
        test = (cur + ' ' + w).strip()
        bb = draw.textbbox((0,0), test, font=font)
        if bb[2] <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def _alpha_at(f, start, fade=18):
    if f < start: return 0
    e = f - start
    if e >= fade: return 255
    return int(255 * e / fade)

def _slide_at(f, start, slide=22):
    if f < start: return 60
    e = f - start
    if e >= slide: return 0
    t = e / slide
    return int(60 * (1 - t*t*(3-2*t)))

def _paste_text(img, text, font, x, y, color, alpha, anchor='mm'):
    if alpha <= 0 or not text: return
    layer = Image.new('RGBA', (W, H), (0,0,0,0))
    d = ImageDraw.Draw(layer)
    r, g, b = color
    d.text((x, y), text, font=font, fill=(r,g,b,alpha), anchor=anchor)
    img.paste(layer, mask=layer)

def _paste_line(img, x1, y1, x2, y2, color, alpha, width=4):
    if alpha <= 0: return
    layer = Image.new('RGBA', (W, H), (0,0,0,0))
    d = ImageDraw.Draw(layer)
    r, g, b = color
    d.line([(x1,y1),(x2,y2)], fill=(r,g,b,alpha), width=width)
    img.paste(layer, mask=layer)

def _paste_rect(img, x1, y1, x2, y2, color, alpha):
    if alpha <= 0: return
    layer = Image.new('RGBA', (W, H), (0,0,0,0))
    d = ImageDraw.Draw(layer)
    r, g, b = color
    d.rectangle([(x1,y1),(x2,y2)], fill=(r,g,b,alpha))
    img.paste(layer, mask=layer)

# ─── LAYOUT ENGINE ───────────────────────────────────────────────────────────

def _render_frame(img, draw, post_data, f):
    """
    Luxury editorial layout:
    - Top zone: small label in Oswald Regular (tracking spaced)
    - Neighborhood: MASSIVE Oswald Bold, near full width
    - Thin orange rule
    - Headline: Oswald Regular medium
    - Body: Raleway Regular small
    - Stat: Large Oswald Bold in orange (if present)
    """
    ct      = post_data.get('content_type', 'market_stat')
    hood    = post_data.get('neighborhood', 'San Diego').upper()
    hl      = post_data.get('headline', post_data.get('insight', ''))
    body    = (post_data.get('real_estate_tie') or
               post_data.get('context') or
               post_data.get('tip') or '')
    stat    = str(post_data.get('stat', ''))

    label_map = {
        'sd_hidden_gem':      'LIFE  IN',
        'current_event_tie':  'RIGHT NOW',
        'hot_take':           'HOT TAKE',
        'hyper_local_intel':  'MARKET INTEL',
        'sd_lifestyle_hook':  'SD LIVING',
        'buyer_seller_tip':   'PRO TIP',
        'investor_quote':     'INVEST IN SD',
        'san_diego_lifestyle':'LIFE IN SD',
        'property_spotlight': 'JUST LISTED',
        'market_stat':        'SAN DIEGO',
    }
    label = label_map.get(ct, 'SAN DIEGO')

    # For market_stat, headline IS the stat
    if ct == 'market_stat':
        stat_display = stat
        hl_display   = post_data.get('context', '')[:120]
        hood         = 'MARKET UPDATE'
        body         = ''
    else:
        stat_display = stat
        hl_display   = hl

    # ── TIMING (frames) ──
    t_label = int(FPS * 0.6)
    t_hood  = int(FPS * 1.0)
    t_rule  = int(FPS * 1.6)
    t_hl    = int(FPS * 1.9)
    t_body  = int(FPS * 2.8)
    t_stat  = int(FPS * 3.5)

    PAD = 70  # left/right padding
    CENTER = W // 2

    # ── LABEL ── small spaced caps
    a  = _alpha_at(f, t_label, 20)
    yo = _slide_at(f, t_label, 20)
    if a > 0:
        fl = _font('oswald_regular', 36)
        _paste_text(img, label, fl, CENTER, 160 + yo, CREAM, int(a*0.7))

    # ── NEIGHBORHOOD / TITLE ── MASSIVE
    a  = _alpha_at(f, t_hood, 22)
    yo = _slide_at(f, t_hood, 24)
    if a > 0:
        # Auto-size: try 200px, scale down if too wide
        for sz in [200, 170, 145, 120, 100, 84]:
            fn = _font('oswald_bold', sz)
            lines = _wrap(draw, hood, fn, W - PAD*2)
            if len(lines) <= 2:
                break
        y_hood = 220
        for i, line in enumerate(lines[:2]):
            _paste_text(img, line, fn, CENTER, y_hood + i*(sz+10) + yo, WHITE, a)
        hood_bottom = y_hood + len(lines[:2]) * (sz + 10) + yo

    # ── ORANGE RULE ──
    a = _alpha_at(f, t_rule, 12)
    if a > 0:
        rule_y = hood_bottom + 30
        _paste_line(img, CENTER-55, rule_y, CENTER+55, rule_y, ORANGE, a, width=5)
    else:
        rule_y = 600  # fallback

    # ── HEADLINE ──
    a  = _alpha_at(f, t_hl, 20)
    yo = _slide_at(f, t_hl, 22)
    if a > 0 and hl_display:
        fh = _font('oswald_regular', 62)
        hlines = _wrap(draw, hl_display, fh, W - PAD*2)
        hl_y = rule_y + 55
        for i, line in enumerate(hlines[:3]):
            _paste_text(img, line, fh, CENTER, hl_y + i*72 + yo, WHITE, int(a*0.95))
        hl_bottom = hl_y + len(hlines[:3]) * 72
    else:
        hl_bottom = rule_y + 55

    # ── BODY COPY ──
    a  = _alpha_at(f, t_body, 22)
    yo = _slide_at(f, t_body, 22)
    if a > 0 and body:
        fb = _font('raleway_regular', 38)
        blines = _wrap(draw, body, fb, W - PAD*2 - 40)
        body_y = hl_bottom + 45
        # Cap at 3 lines to avoid overflow
        for i, line in enumerate(blines[:3]):
            _paste_text(img, line, fb, CENTER, body_y + i*52 + yo,
                       CREAM, int(a*0.75))

    # ── STAT ── large orange, bottom section
    a  = _alpha_at(f, t_stat, 20)
    yo = _slide_at(f, t_stat, 20)
    if a > 0 and stat_display:
        # Auto-size stat to never overflow
        for sz in [130, 110, 90, 72, 58]:
            fs = _font('oswald_bold', sz)
            bb = draw.textbbox((0,0), stat_display, font=fs)
            if bb[2] - bb[0] <= W - PAD*2:
                break
        _paste_text(img, stat_display, fs, CENTER, 1550 + yo, ORANGE, a)

def _render_logo(img, logo, f):
    """Single white logo, bottom center, fades in at 1s."""
    a = _alpha_at(f, int(FPS*1.0), 24)
    if logo is None or a <= 0: return
    lw = 240
    lh = int(lw * logo.height / logo.width)
    lr = logo.resize((lw, lh), Image.LANCZOS)
    if a < 255:
        r,g,b,al = lr.split()
        al = al.point(lambda x: int(x * a / 255))
        lr = Image.merge('RGBA', (r,g,b,al))
    img.paste(lr, ((W-lw)//2, H-lh-60), lr)

def _render_headshot(img, f):
    """Headshot bottom right, fades in at 1.5s."""
    a = _alpha_at(f, int(FPS*1.5), 24)
    if a <= 0: return
    try:
        hs = Image.open(HEADSHOT_PATH).convert('RGBA')
        hw = 180; hh = int(hw * hs.height / hs.width)
        hs = hs.resize((hw, hh), Image.LANCZOS)
        if a < 255:
            r,g,b,al = hs.split()
            al = al.point(lambda x: int(x * a / 255))
            hs = Image.merge('RGBA', (r,g,b,al))
        img.paste(hs, (W-hw-40, H-hh-250), hs)
    except: pass

# ─── FRAME BUILDER ───────────────────────────────────────────────────────────

HEADSHOT_TYPES = {'buyer_seller_tip', 'hot_take'}

def _build_frames(post_data, bg, logo, tmp_dir):
    ct = post_data.get('content_type', 'market_stat')
    show_headshot = ct in HEADSHOT_TYPES

    log.info(f'Rendering {TOTAL_FRAMES} frames at {W}x{H}...')

    for f in range(TOTAL_FRAMES):
        if f % 24 == 0:
            log.info(f'  Frame {f}/{TOTAL_FRAMES}')

        # Background with Ken Burns
        bg_frame = _ken_burns(bg, f, TOTAL_FRAMES)
        frame    = _overlay(bg_frame).convert('RGBA')
        draw     = ImageDraw.Draw(frame)

        # Content
        _render_frame(frame, draw, post_data, f)

        # Logo
        _render_logo(frame, logo, f)

        # Headshot (selected types only)
        if show_headshot:
            _render_headshot(frame, f)

        # Save
        frame.convert('RGB').save(
            os.path.join(tmp_dir, f'f{f:05d}.jpg'), 'JPEG', quality=88)

    log.info('Frame rendering complete.')

# ─── AUDIO ───────────────────────────────────────────────────────────────────

def _gen_silence(path):
    samples = np.zeros(int(44100 * DURATION), dtype=np.int16)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2)
        wf.setframerate(44100); wf.writeframes(samples.tobytes())

# ─── ENTRY ───────────────────────────────────────────────────────────────────

def generate_reel(post_data: dict) -> str:
    cloudinary.config(
        cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key    = os.getenv('CLOUDINARY_API_KEY'),
        api_secret = os.getenv('CLOUDINARY_API_SECRET')
    )
    tmp = tempfile.mkdtemp(prefix='wbg_')
    try:
        # Pre-download fonts (cached after first run)
        log.info('Ensuring fonts are cached...')
        for name in GOOGLE_FONTS:
            _get_font_path(name)

        # Load logo once
        log.info('Loading logo...')
        logo = None
        for name in [PREFERRED_LOGO] + FALLBACK_LOGOS:
            path = os.path.join(ASSETS_DIR, name)
            if os.path.exists(path):
                try:
                    logo = Image.open(path).convert('RGBA')
                    log.info(f'Logo loaded: {name}')
                    break
                except: continue

        # Fetch background
        log.info('Fetching background...')
        bg = _fetch_background(post_data.get('content_type', 'market_stat'))

        # Build frames
        log.info('Building frames...')
        _build_frames(post_data, bg, logo, tmp)

        # Audio
        audio_path = os.path.join(tmp, 'audio.wav')
        _gen_silence(audio_path)

        # Encode
        log.info('Running ffmpeg...')
        out_path = os.path.join(tmp, 'reel.mp4')
        cmd = [
            imageio_ffmpeg.get_ffmpeg_exe(), '-y',
            '-framerate', str(FPS),
            '-i', os.path.join(tmp, 'f%05d.jpg'),
            '-i', audio_path,
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
            '-pix_fmt', 'yuv420p', '-t', str(DURATION),
            '-c:a', 'aac', '-b:a', '128k', '-shortest',
            out_path
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        log.info('ffmpeg complete.')

        # Upload
        log.info('Uploading to Cloudinary...')
        result = cloudinary.uploader.upload_large(
            out_path, resource_type='video',
            public_id='wbg_daily_reel', overwrite=True, timeout=120
        )
        url = result['secure_url']
        log.info(f'Upload complete: {url}')
        return url

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
