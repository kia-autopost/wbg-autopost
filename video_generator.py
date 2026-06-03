"""
WBG Video Generator - V4.1
Fixes: correct font URLs, working photo source, 720x1280 for Railway memory limits
"""
import os, tempfile, shutil, wave, subprocess, random, urllib.request, json, logging
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
import cloudinary, cloudinary.uploader

log = logging.getLogger('WBG')

ASSETS_DIR     = os.path.join(os.path.dirname(__file__), 'assets')
HEADSHOT_PATH  = os.path.join(ASSETS_DIR, 'headshot.png')
PREFERRED_LOGO = 'Logo_Primary_White_01.png'
FALLBACK_LOGOS = [
    'exp_Logo_Secondary_White_01.png',
    'WBG LOGO - ExpLogoLogoPrimaryWhite01.png',
    'exp_Logo_Primary_Dune_01.png',
]

W, H         = 720, 1280   # Railway-safe, correct 9:16 ratio
FPS          = 24
DURATION     = 10
TOTAL_FRAMES = DURATION * FPS  # 240

WHITE  = (255, 255, 255)
CREAM  = (240, 235, 225)
ORANGE = (210, 85, 25)
BLACK  = (8, 8, 8)

# ─── FONTS ───────────────────────────────────────────────────────────────────

FONT_CACHE = {}

# Working Google Fonts direct download URLs (bunny.net CDN mirror - reliable)
GOOGLE_FONTS = {
    'oswald_bold':    'https://fonts.bunny.net/oswald/files/oswald-latin-700-normal.woff2',
    'oswald_regular': 'https://fonts.bunny.net/oswald/files/oswald-latin-400-normal.woff2',
    'raleway_regular':'https://fonts.bunny.net/raleway/files/raleway-latin-400-normal.woff2',
}

# Fallback: use bundled Caladea
def _get_font_path(name):
    cache_dir = '/tmp/wbg_fonts'
    os.makedirs(cache_dir, exist_ok=True)
    # woff2 won't work with PIL - use TTF from Google APIs instead
    ttf_urls = {
        'oswald_bold':    'https://github.com/googlefonts/OswaldFont/raw/main/fonts/TTF/Oswald-Bold.ttf',
        'oswald_regular': 'https://github.com/googlefonts/OswaldFont/raw/main/fonts/TTF/Oswald-Regular.ttf',
        'raleway_regular':'https://github.com/googlefonts/Raleway/raw/main/fonts/ttf/Raleway-Regular.ttf',
    }
    path = os.path.join(cache_dir, f'{name}.ttf')
    if os.path.exists(path) and os.path.getsize(path) > 10000:
        return path
    url = ttf_urls.get(name)
    if not url:
        return None
    try:
        log.info(f'Downloading font: {name}')
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0',
            'Accept': '*/*',
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        if len(data) < 10000:
            raise ValueError(f'Font too small: {len(data)} bytes')
        with open(path, 'wb') as f:
            f.write(data)
        log.info(f'Font cached: {name} ({len(data)} bytes)')
        return path
    except Exception as e:
        log.warning(f'Font download failed for {name}: {e}')
        return None

def _font(name, size):
    key = (name, size)
    if key in FONT_CACHE:
        return FONT_CACHE[key]
    path = _get_font_path(name)
    if path:
        try:
            f = ImageFont.truetype(path, size)
            FONT_CACHE[key] = f
            return f
        except Exception as e:
            log.warning(f'Failed to load {name} at {size}: {e}')
    # Fallback to Caladea
    caladea = os.path.join(ASSETS_DIR, 'Caladea-Regular.ttf')
    if os.path.exists(caladea):
        try:
            f = ImageFont.truetype(caladea, size)
            FONT_CACHE[key] = f
            return f
        except:
            pass
    return ImageFont.load_default()

# ─── BACKGROUND ──────────────────────────────────────────────────────────────

UNSPLASH_KEY = os.getenv('UNSPLASH_ACCESS_KEY', '')

SD_QUERIES = {
    'sd_hidden_gem':      ['san diego neighborhood', 'california coast', 'san diego architecture', 'california landscape'],
    'current_event_tie':  ['san diego skyline', 'san diego downtown', 'california city', 'san diego bay'],
    'hot_take':           ['luxury home interior', 'modern architecture', 'luxury real estate', 'contemporary home'],
    'hyper_local_intel':  ['san diego neighborhood', 'california suburb', 'san diego hills', 'suburban california'],
    'sd_lifestyle_hook':  ['san diego beach', 'la jolla california', 'coronado island', 'del mar california'],
    'property_spotlight': ['luxury home pool', 'modern house exterior', 'mediterranean villa', 'beach house'],
    'market_stat':        ['san diego skyline', 'california coast aerial', 'san diego harbor', 'city aerial'],
    'buyer_seller_tip':   ['modern home interior', 'luxury kitchen', 'living room modern', 'real estate'],
    'investor_quote':     ['city skyline', 'modern architecture', 'luxury penthouse', 'urban skyline'],
    'san_diego_lifestyle':['san diego beach', 'pacific beach sunset', 'ocean beach california', 'la jolla cove'],
}

PEXELS_QUERIES = {
    'sd_hidden_gem':      ['san diego', 'california coast', 'neighborhood street', 'california architecture'],
    'hot_take':           ['luxury interior', 'modern home', 'real estate', 'contemporary house'],
    'sd_lifestyle_hook':  ['beach sunset', 'california beach', 'ocean sunset', 'coastal california'],
    'market_stat':        ['city skyline', 'aerial city', 'downtown buildings', 'urban landscape'],
    'default':            ['san diego', 'california', 'luxury home', 'real estate'],
}

def _fetch_background(content_type, neighborhood=None):
    """Try Unsplash API, then Pexels free, then gradient."""
    bg_w = int(W * 1.12)
    bg_h = int(H * 1.12)

    # 1. Try Unsplash API if key available
    if UNSPLASH_KEY:
        try:
            # Use neighborhood name if available for better photo match
            if neighborhood and neighborhood.lower() not in ('san diego', ''):
                query = (neighborhood.lower() + ' san diego').replace(' ', '+')
            else:
                queries = SD_QUERIES.get(content_type, ['san diego'])
                query = random.choice(queries).replace(' ', '+')
            url = f'https://api.unsplash.com/photos/random?query={query}&orientation=portrait&client_id={UNSPLASH_KEY}'
            req = urllib.request.Request(url, headers={'Accept-Version': 'v1'})
            with urllib.request.urlopen(req, timeout=6) as r:
                data = json.loads(r.read())
            img_url = data['urls']['regular']
            with urllib.request.urlopen(img_url, timeout=10) as r:
                img_data = r.read()
            tmp = tempfile.mktemp(suffix='.jpg')
            with open(tmp, 'wb') as f:
                f.write(img_data)
            bg = Image.open(tmp).convert('RGB')
            os.unlink(tmp)
            ratio = max(bg_w / bg.width, bg_h / bg.height)
            bg = bg.resize((int(bg.width*ratio), int(bg.height*ratio)), Image.LANCZOS)
            log.info(f'Unsplash background loaded')
            return bg
        except Exception as e:
            log.warning(f'Unsplash failed: {e}')

    # 2. Try Pexels (free, no key needed for static URLs)
    try:
        pexels_photos = [
            'https://images.pexels.com/photos/1396122/pexels-photo-1396122.jpeg',  # luxury home
            'https://images.pexels.com/photos/259588/pexels-photo-259588.jpeg',    # modern house
            'https://images.pexels.com/photos/2102587/pexels-photo-2102587.jpeg',  # aerial city
            'https://images.pexels.com/photos/1642125/pexels-photo-1642125.jpeg',  # beach sunset
            'https://images.pexels.com/photos/2467285/pexels-photo-2467285.jpeg',  # modern interior
            'https://images.pexels.com/photos/3935333/pexels-photo-3935333.jpeg',  # coastal
            'https://images.pexels.com/photos/1571460/pexels-photo-1571460.jpeg',  # luxury interior
            'https://images.pexels.com/photos/323780/pexels-photo-323780.jpeg',    # house exterior
            'https://images.pexels.com/photos/2119714/pexels-photo-2119714.jpeg',  # san diego coast
            'https://images.pexels.com/photos/1029599/pexels-photo-1029599.jpeg',  # modern home
        ]
        url = random.choice(pexels_photos) + f'?auto=compress&cs=tinysrgb&w={bg_w}&h={bg_h}&fit=crop'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            img_data = r.read()
        tmp = tempfile.mktemp(suffix='.jpg')
        with open(tmp, 'wb') as f:
            f.write(img_data)
        bg = Image.open(tmp).convert('RGB')
        os.unlink(tmp)
        ratio = max(bg_w / bg.width, bg_h / bg.height)
        if ratio > 1:
            bg = bg.resize((int(bg.width*ratio), int(bg.height*ratio)), Image.LANCZOS)
        log.info(f'Pexels background loaded: {bg.size}')
        return bg
    except Exception as e:
        log.warning(f'Pexels failed: {e}')

    log.warning('Using gradient background')
    return _gradient()

def _gradient():
    bg = Image.new('RGB', (int(W*1.12), int(H*1.12)))
    d = ImageDraw.Draw(bg)
    for y in range(int(H*1.12)):
        t = y / (H*1.12)
        d.line([(0,y),(int(W*1.12),y)], fill=(int(15+t*10), int(12+t*8), int(18+t*14)))
    return bg

# ─── KEN BURNS ───────────────────────────────────────────────────────────────

def _ken_burns(bg, f, total):
    t   = f / max(total - 1, 1)
    t_e = t * t * (3 - 2 * t)
    bw, bh = bg.size
    cw = max(W, int(W + (bw - W) * (1 - t_e) * 0.45))
    ch = max(H, int(H + (bh - H) * (1 - t_e) * 0.45))
    cw = min(cw, bw); ch = min(ch, bh)
    cx = bw//2 + int(18*(1-t_e))
    cy = bh//2 + int(12*(1-t_e))
    l  = max(0, min(cx-cw//2, bw-cw))
    tp = max(0, min(cy-ch//2, bh-ch))
    cropped = bg.crop((l, tp, l+cw, tp+ch))
    if cropped.size != (W, H):
        cropped = cropped.resize((W, H), Image.LANCZOS)
    return cropped

# ─── OVERLAY ─────────────────────────────────────────────────────────────────

def _overlay(bg_frame):
    ov = Image.new('RGBA', (W, H), (0,0,0,0))
    d  = ImageDraw.Draw(ov)
    for y in range(H):
        t = y / H
        if t < 0.44:
            a = int(195 * (1 - t/0.44)**1.6)
        elif t > 0.60:
            a = int(225 * ((t-0.60)/0.40)**1.1)
        else:
            a = 18
        d.line([(0,y),(W,y)], fill=(0,0,0,a))
    return Image.alpha_composite(bg_frame.convert('RGBA'), ov).convert('RGB')

# ─── TEXT HELPERS ────────────────────────────────────────────────────────────

def _wrap(draw, text, font, max_w):
    words = text.split()
    lines, cur = [], ''
    for w in words:
        test = (cur + ' ' + w).strip()
        if draw.textbbox((0,0), test, font=font)[2] <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def _a(f, start, fade=18):
    if f < start: return 0
    e = f - start
    return 255 if e >= fade else int(255 * e / fade)

def _y(f, start, slide=22):
    if f < start: return 45
    e = f - start
    if e >= slide: return 0
    t = e / slide
    return int(45 * (1 - t*t*(3-2*t)))

def _txt(img, text, font, x, y, color, alpha, anchor='mm'):
    if alpha <= 0 or not text: return
    layer = Image.new('RGBA', (W,H), (0,0,0,0))
    d = ImageDraw.Draw(layer)
    r,g,b = color
    d.text((x,y), text, font=font, fill=(r,g,b,alpha), anchor=anchor)
    img.paste(layer, mask=layer)

def _txt_backed(img, draw, text, font, x, y, color, alpha, anchor='mm', pad_x=20, pad_y=8):
    """Draw text with a semi-transparent dark backing pill for readability."""
    if alpha <= 0 or not text: return
    bb = draw.textbbox((x,y), text, font=font, anchor=anchor)
    bx1 = bb[0] - pad_x; by1 = bb[1] - pad_y
    bx2 = bb[2] + pad_x; by2 = bb[3] + pad_y
    back = Image.new('RGBA', (W,H), (0,0,0,0))
    bd = ImageDraw.Draw(back)
    bd.rounded_rectangle([(bx1,by1),(bx2,by2)], radius=6,
                          fill=(0,0,0,int(alpha*0.55)))
    img.paste(back, mask=back)
    _txt(img, text, font, x, y, color, alpha, anchor)

def _line(img, x1, y1, x2, y2, color, alpha, w=4):
    if alpha <= 0: return
    layer = Image.new('RGBA', (W,H), (0,0,0,0))
    d = ImageDraw.Draw(layer)
    r,g,b = color
    d.line([(x1,y1),(x2,y2)], fill=(r,g,b,alpha), width=w)
    img.paste(layer, mask=layer)

# ─── LAYOUT ──────────────────────────────────────────────────────────────────

PAD    = 50   # side padding
CENTER = W // 2

def _render(img, draw, post_data, f):
    ct   = post_data.get('content_type', 'market_stat')
    hood = post_data.get('neighborhood', 'San Diego').upper()
    hl   = post_data.get('headline', post_data.get('insight', ''))
    body = (post_data.get('real_estate_tie') or post_data.get('context') or
            post_data.get('tip') or '')
    stat = str(post_data.get('stat', ''))

    labels = {
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

    if ct == 'market_stat':
        hood = 'MARKET\nUPDATE'
        hl   = post_data.get('context', '')
        stat = str(post_data.get('stat', ''))
        body = ''

    label = labels.get(ct, 'SAN DIEGO')

    # Timing
    T = {
        'label': int(FPS*0.5),
        'hood':  int(FPS*0.9),
        'rule':  int(FPS*1.5),
        'hl':    int(FPS*1.8),
        'body':  int(FPS*2.7),
        'stat':  int(FPS*3.4),
    }

    # ── LABEL ── spaced small caps
    al = _a(f, T['label'], 20)
    yo = _y(f, T['label'], 20)
    if al:
        fl = _font('oswald_regular', 24)
        _txt(img, label, fl, CENTER, 105+yo, CREAM, int(al*0.65))

    # ── NEIGHBORHOOD ── auto-size bold condensed
    al = _a(f, T['hood'], 22)
    yo = _y(f, T['hood'], 24)
    hood_bottom = 200
    if al:
        for sz in [130, 110, 92, 76, 62, 50]:
            fn = _font('oswald_bold', sz)
            parts = hood.split('\n')
            all_lines = []
            for part in parts:
                all_lines += _wrap(draw, part, fn, W - PAD*2)
            if len(all_lines) <= 3:
                break
        y_cur = 160
        for line in all_lines[:3]:
            _txt(img, line, fn, CENTER, y_cur+yo, WHITE, al)
            y_cur += sz + 8
        hood_bottom = y_cur + yo

    # ── ORANGE RULE ──
    al = _a(f, T['rule'], 12)
    rule_y = hood_bottom + 24
    if al:
        _line(img, CENTER-40, rule_y, CENTER+40, rule_y, ORANGE, al, w=4)

    # ── HEADLINE ──
    al = _a(f, T['hl'], 20)
    yo = _y(f, T['hl'], 22)
    hl_bottom = rule_y + 40
    if al and hl:
        fh = _font('oswald_regular', 42)
        hlines = _wrap(draw, hl, fh, W - PAD*2)
        y_cur = rule_y + 50
        for line in hlines[:3]:
            _txt_backed(img, draw, line, fh, CENTER, y_cur+yo, WHITE, int(al*0.95))
            y_cur += 52
        hl_bottom = y_cur + yo

    # ── BODY ──
    al = _a(f, T['body'], 22)
    yo = _y(f, T['body'], 22)
    if al and body:
        fb = _font('raleway_regular', 26)
        blines = _wrap(draw, body[:180], fb, W - PAD*2 - 20)
        y_cur = hl_bottom + 30
        for line in blines[:3]:
            _txt_backed(img, draw, line, fb, CENTER, y_cur+yo, CREAM, int(al*0.72))
            y_cur += 38

    # ── STAT ── auto-sized, locked to safe zone
    al = _a(f, T['stat'], 20)
    yo = _y(f, T['stat'], 20)
    if al and stat:
        for sz in [90, 74, 60, 48, 38]:
            fs = _font('oswald_bold', sz)
            bb = draw.textbbox((0,0), stat, font=fs)
            if bb[2]-bb[0] <= W - PAD*2:
                break
        # Lock stat to bottom content zone, away from logo
        stat_y = min(920, H - 280)
        _txt(img, stat, fs, CENTER, stat_y+yo, ORANGE, al)

# ─── LOGO & HEADSHOT ─────────────────────────────────────────────────────────

def _render_logo(img, logo, f):
    al = _a(f, int(FPS*0.8), 24)
    if not logo or al <= 0: return
    lw = 170; lh = int(lw * logo.height / logo.width)
    lr = logo.resize((lw, lh), Image.LANCZOS)
    if al < 255:
        r,g,b,a2 = lr.split()
        a2 = a2.point(lambda x: int(x*al/255))
        lr = Image.merge('RGBA',(r,g,b,a2))
    img.paste(lr, ((W-lw)//2, H-lh-45), lr)

def _render_headshot(img, f):
    al = _a(f, int(FPS*1.2), 24)
    if al <= 0: return
    try:
        hs = Image.open(HEADSHOT_PATH).convert('RGBA')
        hw = 110; hh = int(hw * hs.height / hs.width)
        hs = hs.resize((hw, hh), Image.LANCZOS)
        if al < 255:
            r,g,b,a2 = hs.split()
            a2 = a2.point(lambda x: int(x*al/255))
            hs = Image.merge('RGBA',(r,g,b,a2))
        img.paste(hs, (W-hw-25, H-hh-170), hs)
    except: pass

HEADSHOT_TYPES = {'buyer_seller_tip', 'hot_take'}

# ─── FRAME LOOP ──────────────────────────────────────────────────────────────

def _build_frames(post_data, bg, logo, tmp_dir):
    ct = post_data.get('content_type', 'market_stat')
    show_hs = ct in HEADSHOT_TYPES
    log.info(f'Rendering {TOTAL_FRAMES} frames at {W}x{H}...')
    for f in range(TOTAL_FRAMES):
        if f % 24 == 0:
            log.info(f'  Frame {f}/{TOTAL_FRAMES}')
        bg_f  = _ken_burns(bg, f, TOTAL_FRAMES)
        frame = _overlay(bg_f).convert('RGBA')
        draw  = ImageDraw.Draw(frame)
        _render(frame, draw, post_data, f)
        _render_logo(frame, logo, f)
        if show_hs: _render_headshot(frame, f)
        frame.convert('RGB').save(
            os.path.join(tmp_dir, f'f{f:05d}.jpg'), 'JPEG', quality=85)
    log.info('Rendering complete.')

# ─── AUDIO ───────────────────────────────────────────────────────────────────

def _silence(path):
    s = np.zeros(int(44100*DURATION), dtype=np.int16)
    with wave.open(path,'w') as w:
        w.setnchannels(1); w.setsampwidth(2)
        w.setframerate(44100); w.writeframes(s.tobytes())

# ─── ENTRY ───────────────────────────────────────────────────────────────────

def generate_reel(post_data: dict) -> str:
    cloudinary.config(
        cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key=os.getenv('CLOUDINARY_API_KEY'),
        api_secret=os.getenv('CLOUDINARY_API_SECRET')
    )
    tmp = tempfile.mkdtemp(prefix='wbg_')
    try:
        # Pre-cache fonts
        log.info('Caching fonts...')
        for name in ['oswald_bold','oswald_regular','raleway_regular']:
            _get_font_path(name)

        # Logo (loaded once)
        logo = None
        for name in [PREFERRED_LOGO]+FALLBACK_LOGOS:
            p = os.path.join(ASSETS_DIR, name)
            if os.path.exists(p):
                try: logo = Image.open(p).convert('RGBA'); log.info(f'Logo: {name}'); break
                except: continue

        # Background
        log.info('Fetching background...')
        bg = _fetch_background(
            post_data.get('content_type','market_stat'),
            post_data.get('neighborhood','')
        )

        # Frames
        _build_frames(post_data, bg, logo, tmp)

        # Audio
        audio = os.path.join(tmp,'audio.wav')
        _silence(audio)

        # Encode - ultrafast preset to avoid SIGKILL
        out = os.path.join(tmp,'reel.mp4')
        log.info('Encoding...')
        subprocess.run([
            imageio_ffmpeg.get_ffmpeg_exe(), '-y',
            '-framerate', str(FPS),
            '-i', os.path.join(tmp,'f%05d.jpg'),
            '-i', audio,
            '-c:v','libx264','-preset','ultrafast','-crf','26',
            '-pix_fmt','yuv420p','-t',str(DURATION),
            '-c:a','aac','-b:a','64k','-shortest',
            out
        ], check=True, capture_output=True, timeout=180)
        log.info('Encoded.')

        # Upload
        log.info('Uploading...')
        r = cloudinary.uploader.upload_large(
            out, resource_type='video',
            public_id='wbg_daily_reel', overwrite=True, timeout=120
        )
        url = r['secure_url']
        log.info(f'Done: {url}')
        return url
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
