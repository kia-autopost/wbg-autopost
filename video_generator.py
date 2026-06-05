"""
WBG Video Generator - V6 Full Bleed + Audio Edition
- DARK CINEMATIC: sd_hidden_gem, market_stat, current_event_tie, investor_quote
- LIGHT EDITORIAL: buyer_seller_tip, hot_take, hyper_local_intel, sd_lifestyle_hook,
                   san_diego_lifestyle, property_spotlight
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
DARK_LOGO      = 'Logomark_Primary_Dune_01 (1).png'  # WB mark in Dune for light backgrounds
FALLBACK_LOGOS = ['exp_Logo_Secondary_White_01.png', 'WBG LOGO - ExpLogoLogoPrimaryWhite01.png']

W, H         = 720, 1280
FPS          = 24
DURATION     = 10
TOTAL_FRAMES = DURATION * FPS

# Colors
WHITE  = (255, 255, 255)
CREAM  = (245, 240, 230)
CREAM2 = (250, 247, 242)
BLACK  = (12, 12, 12)
DKGRAY = (30, 30, 30)
ORANGE = (210, 85, 25)
LTGRAY = (180, 175, 168)

# Style routing
DARK_TYPES  = {'sd_hidden_gem', 'market_stat', 'current_event_tie', 'investor_quote', 'market_data'}
LIGHT_TYPES = {'buyer_seller_tip', 'hot_take', 'hyper_local_intel', 'sd_lifestyle_hook',
               'san_diego_lifestyle', 'property_spotlight', 'home_tour'}
HEADSHOT_TYPES = {'buyer_seller_tip', 'hot_take'}

UNSPLASH_KEY = os.getenv('UNSPLASH_ACCESS_KEY', 'gWh-_occEjfxnSZSyxlrqYJYB3indaIXCp3STJyGesc')

# ─── FONTS ───────────────────────────────────────────────────────────────────

FONT_CACHE = {}
FONT_FILES = {
    'oswald_bold':    'Oswald-VariableFont_wght.ttf',
    'oswald_regular': 'Oswald-VariableFont_wght.ttf',
    'raleway':        'Raleway-VariableFont_wght.ttf',
    'caladea':        'Caladea-Regular.ttf',
}

def _font(name, size):
    key = (name, size)
    if key in FONT_CACHE: return FONT_CACHE[key]
    fname = FONT_FILES.get(name, 'Caladea-Regular.ttf')
    path  = os.path.join(ASSETS_DIR, fname)
    if not os.path.exists(path):
        path = os.path.join(ASSETS_DIR, 'Caladea-Regular.ttf')
    try:
        f = ImageFont.truetype(path, size)
        FONT_CACHE[key] = f
        return f
    except:
        return ImageFont.load_default()

# ─── BACKGROUND FETCH ────────────────────────────────────────────────────────

PEXELS_BY_TYPE = {
    # Dark cinematic types - moody SD/coastal/architectural shots
    'sd_hidden_gem':      ['1642125','2119714','2559941','3849407','1174732','2422915','1308940'],
    'current_event_tie':  ['2119714','2559941','1642125','3849407','2102587','1732414'],
    'investor_quote':     ['2102587','1732414','3849407','2467285','1571460','1396122'],
    'market_stat':        ['2102587','1732414','2119714','3849407','1642125','2559941'],
    # Light editorial types - bright homes/interiors
    'sd_lifestyle_hook':  ['1642125','2559941','3849407','1174732','2422915'],
    'san_diego_lifestyle':['1642125','2559941','2422915','1174732','2119714'],
    'hot_take':           ['1571460','2467285','1396122','259588','1029599'],
    'buyer_seller_tip':   ['1571460','2467285','3935333','1396122','323780'],
    'hyper_local_intel':  ['2119714','1308940','259588','323780','1396122'],
    'current_event_tie':  ['2119714','3849407','2102587','1732414','2559941'],
    'property_spotlight': ['1396122','259588','1029599','323780','2467285'],
}

PHOTO_STATE_FILE = '/tmp/wbg_photo_state.json'

def _get_photo_pool(is_dark):
    all_jpgs = sorted([
        f for f in os.listdir(ASSETS_DIR)
        if f.endswith('.jpg') and os.path.exists(os.path.join(ASSETS_DIR, f))
    ])
    # If most photos have generic names (like Unsplash hash names),
    # keyword matching won't work — just use all photos for both pools
    dark_kw  = ['sunset', 'aerial', 'neighborhood', 'palm', 'craftsman',
                'coast', 'beach', 'street', 'city', 'urban']
    light_kw = ['luxury', 'modern', 'house', 'home', 'interior',
                'pool', 'kitchen', 'living', 'bedroom', 'backyard']
    dark_pool  = [f for f in all_jpgs if any(k in f.lower() for k in dark_kw)]
    light_pool = [f for f in all_jpgs if any(k in f.lower() for k in light_kw)]
    # If fewer than 10 keyword matches, use ALL photos (most have hash names)
    if len(dark_pool)  < 10: dark_pool  = all_jpgs
    if len(light_pool) < 10: light_pool = all_jpgs
    return dark_pool if is_dark else light_pool

def _pick_photo(is_dark):
    pool = _get_photo_pool(is_dark)

    if not pool:
        all_jpgs = [f for f in os.listdir(ASSETS_DIR) if f.endswith('.jpg')]
        pool = all_jpgs if all_jpgs else []

    if not pool:
        log.warning('No photos in assets folder')
        return None

    state = {}
    try:
        if os.path.exists(PHOTO_STATE_FILE):
            with open(PHOTO_STATE_FILE, 'r') as f:
                state = json.load(f)
    except:
        state = {}

    key        = 'used_dark' if is_dark else 'used_light'
    used       = set(state.get(key, []))
    last_photo = state.get('last_photo', '')  # Track very last photo used across all posts

    # Remove recently used photo from consideration to prevent back-to-back repeats
    unused = [p for p in pool if p not in used and p != last_photo]

    # Reset if exhausted
    if not unused:
        log.info(f'Photo pool exhausted ({key}), resetting rotation')
        unused = [p for p in pool if p != last_photo]
        if not unused:
            unused = pool
        used = set()

    chosen = random.choice(unused)
    used.add(chosen)
    state[key]        = list(used)
    state['last_photo'] = chosen  # Remember across dark/light pools

    try:
        with open(PHOTO_STATE_FILE, 'w') as f:
            json.dump(state, f)
    except:
        pass

    log.info(f'Photo: {chosen} ({len(unused)-1} unused left of {len(pool)})')
    return chosen

def _fetch_bg(content_type, neighborhood='', size_w=None, size_h=None):
    bw = size_w or int(W * 1.12)
    bh = size_h or int(H * 1.12)
    is_dark = content_type in DARK_TYPES
    chosen  = _pick_photo(is_dark)
    path    = os.path.join(ASSETS_DIR, chosen)
    if chosen and os.path.exists(path):
        try:
            bg = Image.open(path).convert('RGB')
            # Crop bottom 50px to remove watermarks
            if bg.height > 200: bg = bg.crop((0, 0, bg.width, bg.height - 50))
            # Crop bottom 50px to remove any watermarks
            if bg.height > 100:
                bg = bg.crop((0, 0, bg.width, bg.height - 50))
            ratio = max(bw/bg.width, bh/bg.height)
            bg = bg.resize((int(bg.width*ratio), int(bg.height*ratio)), Image.LANCZOS)
            return bg
        except Exception as e:
            log.warning(f'Photo load failed for {chosen}: {e}')
    log.warning('Falling back to gradient')
    return _gradient(bw, bh)

def _gradient(w, h):
    # Rich cinematic gradient - deep charcoal with warm orange glow
    bg = Image.new('RGBA', (w, h), (0,0,0,255))
    d  = ImageDraw.Draw(bg)
    for y in range(h):
        t = y/h
        r = int(20 + t*12)
        g = int(16 + t*8)
        b = int(25 + t*10)
        d.line([(0,y),(w,y)], fill=(r,g,b,255))
    glow = Image.new('RGBA', (w,h), (0,0,0,0))
    gd = ImageDraw.Draw(glow)
    for i in range(180, 0, -1):
        alpha = min(int((180-i) * 0.7), 120)
        gd.ellipse([(-i, h-i*2),(i*3, h+i)], fill=(180,60,10,alpha))
    return Image.alpha_composite(bg, glow).convert('RGB')

# ─── KEN BURNS ───────────────────────────────────────────────────────────────

def _ken_burns(bg, f, total):
    t   = f / max(total-1, 1)
    t_e = t*t*(3-2*t)
    bw, bh = bg.size
    scale = 1.08 + (1.0-1.08)*t_e
    cw = max(W, min(int(W*scale), bw))
    ch = max(H, min(int(H*scale), bh))
    cx = bw//2; cy = bh//2
    l  = max(0, min(cx-cw//2, bw-cw))
    tp = max(0, min(cy-ch//2, bh-ch))
    cropped = bg.crop((l, tp, l+cw, tp+ch))
    if cropped.size != (W,H): cropped = cropped.resize((W,H), Image.LANCZOS)
    return cropped

# ─── OVERLAYS ────────────────────────────────────────────────────────────────

def _dark_overlay(bg_frame):
    """Smooth cinematic vignette - no hard bands, natural darkening."""
    import math
    ov = Image.new('RGBA', (W,H), (0,0,0,0))
    d  = ImageDraw.Draw(ov)
    for y in range(H):
        t = y / H
        # Smooth cosine curve - dark at top and bottom, clear in middle
        # Top vignette: fades smoothly from 210 to 0 over top 55%
        if t < 0.55:
            top_a = int(210 * (math.cos(t / 0.55 * math.pi / 2)) ** 1.4)
        else:
            top_a = 0
        # Bottom vignette: fades smoothly from 0 to 220 over bottom 45%
        if t > 0.55:
            bot_a = int(220 * (math.sin((t - 0.55) / 0.45 * math.pi / 2)) ** 1.2)
        else:
            bot_a = 0
        # Base dark tint across whole frame for photo desaturation
        base_a = 60
        a = min(255, top_a + bot_a + base_a)
        d.line([(0,y),(W,y)], fill=(0,0,0,a))
    return Image.alpha_composite(bg_frame.convert('RGBA'), ov).convert('RGB')

def _light_overlay(bg_frame):
    """Full-bleed airy overlay - warm vignette, photo shows everywhere."""
    import math
    ov = Image.new('RGBA', (W,H), (0,0,0,0))
    d  = ImageDraw.Draw(ov)
    for y in range(H):
        t = y / H
        if t < 0.5:
            top_a = int(160 * (math.cos(t / 0.5 * math.pi / 2)) ** 1.6)
        else:
            top_a = 0
        if t > 0.6:
            bot_a = int(180 * (math.sin((t-0.6)/0.4 * math.pi/2)) ** 1.4)
        else:
            bot_a = 0
        base_a = 35
        a = min(230, top_a + bot_a + base_a)
        d.line([(0,y),(W,y)], fill=(0,0,0,a))
    result = Image.alpha_composite(bg_frame.convert('RGBA'), ov)
    return result.convert('RGB')

# ─── TEXT HELPERS ────────────────────────────────────────────────────────────

def _wrap(draw, text, font, max_w):
    words = text.split()
    lines, cur = [], ''
    for w in words:
        test = (cur+' '+w).strip()
        if draw.textbbox((0,0),test,font=font)[2] <= max_w: cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def _a(f, start, fade=18):
    if f < start: return 0
    e = f-start
    return 255 if e >= fade else int(255*e/fade)

def _y(f, start, slide=20):
    if f < start: return 45
    e = f-start
    if e >= slide: return 0
    t = e/slide
    return int(45*(1-t*t*(3-2*t)))

def _paste(img, text, font, x, y, color, alpha, anchor='mm'):
    if alpha <= 0 or not text: return
    layer = Image.new('RGBA',(W,H),(0,0,0,0))
    d = ImageDraw.Draw(layer)
    r,g,b = color
    d.text((x,y), text, font=font, fill=(r,g,b,alpha), anchor=anchor)
    img.paste(layer, mask=layer)

def _paste_backed(img, draw, text, font, x, y, fg, alpha, anchor='mm', bg_color=(0,0,0), bg_alpha_mult=0.75, pad_x=22, pad_y=10):
    """Text with dark backing pill — for readability over photos."""
    if alpha <= 0 or not text: return
    bb = draw.textbbox((x,y), text, font=font, anchor=anchor)
    bx1=bb[0]-pad_x; by1=bb[1]-pad_y; bx2=bb[2]+pad_x; by2=bb[3]+pad_y
    back = Image.new('RGBA',(W,H),(0,0,0,0))
    bd = ImageDraw.Draw(back)
    r,g,b = bg_color
    bd.rounded_rectangle([(bx1,by1),(bx2,by2)], radius=8, fill=(r,g,b,int(alpha*bg_alpha_mult)))
    img.paste(back, mask=back)
    _paste(img, text, font, x, y, fg, alpha, anchor)

def _paste_line(img, x1, y1, x2, y2, color, alpha, w=4):
    if alpha <= 0: return
    layer = Image.new('RGBA',(W,H),(0,0,0,0))
    d = ImageDraw.Draw(layer)
    r,g,b = color
    d.line([(x1,y1),(x2,y2)], fill=(r,g,b,alpha), width=w)
    img.paste(layer, mask=layer)

# ─── DARK CINEMATIC RENDERER ─────────────────────────────────────────────────

def _render_dark(img, draw, post_data, f):
    """Dark cinematic layout - big type, photo background, dark overlay."""
    ct   = post_data.get('content_type','market_stat')
    hood = post_data.get('neighborhood','San Diego').upper()
    hl   = post_data.get('headline', post_data.get('insight',''))
    body = (post_data.get('real_estate_tie') or post_data.get('context') or '')
    stat = str(post_data.get('stat',''))

    labels = {
        'sd_hidden_gem':    'LIFE IN',
        'market_stat':      'SAN DIEGO',
        'current_event_tie':'RIGHT NOW IN SD',
        'investor_quote':   'INVEST IN SD',
        'market_data':      'MARKET UPDATE',
    }
    label = labels.get(ct,'SAN DIEGO')

    if ct == 'market_stat':
        hood = 'MARKET\nUPDATE'
        hl   = post_data.get('context','')
        body = ''

    PAD = 50; CX = W//2
    T = {'label':int(FPS*0.5), 'hood':int(FPS*0.9), 'rule':int(FPS*1.5),
         'hl':int(FPS*1.9), 'body':int(FPS*2.8), 'stat':int(FPS*3.4)}

    # Label
    al = _a(f,T['label'],20); yo = _y(f,T['label'],20)
    _paste(img, label, _font('oswald_regular',24), CX, 105+yo, CREAM, int(al*0.65))

    # Neighborhood - massive
    al = _a(f,T['hood'],22); yo = _y(f,T['hood'],24)
    hood_bottom = 200
    if al:
        for sz in [120,100,84,70,58]:
            fn = _font('oswald_bold',sz)
            parts = hood.split('\n')
            all_lines = []
            for p in parts: all_lines += _wrap(draw, p, fn, W-PAD*2)
            if len(all_lines) <= 3: break
        y_cur = 155
        for line in all_lines[:3]:
            _paste(img, line, fn, CX, y_cur+yo, WHITE, al)
            y_cur += sz+8
        hood_bottom = y_cur+yo

    # Orange rule
    al = _a(f,T['rule'],12); rule_y = hood_bottom+22
    _paste_line(img, CX-40, rule_y, CX+40, rule_y, ORANGE, al, w=4)

    # Headline
    al = _a(f,T['hl'],20); yo = _y(f,T['hl'],22); hl_bottom = rule_y+40
    if al and hl:
        fh = _font('oswald_regular',40)
        hlines = _wrap(draw, hl, fh, W-PAD*2)
        y_cur = rule_y+50
        for line in hlines[:3]:
            # Soft shadow instead of boxy pill
            _paste(img, line, fh, CX+2, y_cur+yo+2, BLACK, int(al*0.5))
            _paste(img, line, fh, CX, y_cur+yo, WHITE, int(al*0.97))
            y_cur += 50
        hl_bottom = y_cur+yo

    # Body - max 2 lines, truncated to fit cleanly
    al = _a(f,T['body'],22); yo = _y(f,T['body'],22); body_bottom = hl_bottom+30
    if al and body:
        fb = _font('oswald_regular',26)
        # Truncate body to ~120 chars so it fits in 2 lines cleanly
        body_short = body[:100].rsplit(' ',1)[0] if len(body) > 100 else body
        blines = _wrap(draw, body_short, fb, W-PAD*2)
        y_cur = hl_bottom+36
        for line in blines[:2]:
            bar = Image.new("RGBA", (W, 40), (0,0,0,int(al*0.55)))
            img.paste(bar, (0, y_cur+yo-16), bar)
            _paste(img, line, fb, CX, y_cur+yo, WHITE, int(al*0.95))
        body_bottom = y_cur+yo

    # Stat - hard truncate to 25 chars, auto-size to fit
    al = _a(f,T['stat'],20); yo = _y(f,T['stat'],20)
    if al and stat:
        # Hard truncate - stat should be a short number/phrase only
        stat_short = stat[:25].rsplit(' ',1)[0] if len(stat) > 25 else stat
        for sz in [72,58,46,38,30]:
            fs = _font('oswald_bold',sz)
            if draw.textbbox((0,0),stat_short,font=fs)[2] <= W-PAD*2: break
        stat_y = min(body_bottom+36, H-290)
        _paste(img, stat_short, fs, CX, stat_y+yo, ORANGE, al)

# ─── LIGHT EDITORIAL RENDERER ────────────────────────────────────────────────

def _render_light(img, draw, post_data, f):
    """Light editorial: photo top 52%, cream panel bottom 48%."""
    ct   = post_data.get('content_type','buyer_seller_tip')
    hood = post_data.get('neighborhood','San Diego').upper()
    hl   = post_data.get('headline', post_data.get('insight',''))
    body = (post_data.get('real_estate_tie') or post_data.get('context') or
            post_data.get('tip') or '')
    stat = str(post_data.get('stat',''))

    labels = {
        'buyer_seller_tip':   'PRO TIP',
        'hot_take':           'HOT TAKE',
        'hyper_local_intel':  'MARKET INTEL',
        'sd_lifestyle_hook':  'SD LIVING',
        'san_diego_lifestyle':'LIFE IN SD',
        'property_spotlight': 'JUST LISTED',
        'home_tour':          'JUST LISTED',
    }
    label = labels.get(ct,'SAN DIEGO')

    PAD = 50; CX = W//2

    T = {'label':int(FPS*0.4), 'hood':int(FPS*0.8), 'rule':int(FPS*1.3),
         'hl':int(FPS*1.7), 'stat':int(FPS*2.3), 'body':int(FPS*2.9)}

    # Label - small spaced caps at top
    al = _a(f,T['label'],18); yo = _y(f,T['label'],18)
    _paste(img, label, _font('oswald_regular',24), CX, 100+yo, CREAM, int(al*0.70))

    # Neighborhood - MASSIVE white, full bleed
    al = _a(f,T['hood'],22); yo = _y(f,T['hood'],22)
    hood_bottom = 260
    if al:
        for sz in [120,100,84,70,58]:
            fn = _font('oswald_bold',sz)
            nlines = _wrap(draw, hood, fn, W-PAD*2)
            if len(nlines) <= 2: break
        y_cur = 155
        for line in nlines[:2]:
            _paste(img, line, fn, CX, y_cur+yo, WHITE, al)
            y_cur += sz+8
        hood_bottom = y_cur + yo + 5

    # Orange rule
    al = _a(f,T['rule'],10); rule_y = hood_bottom + 20
    _paste_line(img, CX-40, rule_y, CX+40, rule_y, ORANGE, al, w=4)

    # Headline - cream/white on photo
    al = _a(f,T['hl'],18); yo = _y(f,T['hl'],20)
    hl_bottom = rule_y + 50
    if al and hl:
        for fsz in [38,32,28,24]:
            fh = _font('oswald_regular', fsz)
            hlines = _wrap(draw, hl, fh, W-PAD*2)
            if len(hlines) <= 2: break
        y_cur = rule_y + 50
        for line in hlines[:2]:
            _paste(img, line, fh, CX, y_cur+yo, WHITE, int(al*0.95))
            y_cur += fsz + 10
        hl_bottom = y_cur + yo

    # Stat - orange, bold
    al = _a(f,T['stat'],18); yo = _y(f,T['stat'],18)
    stat_bottom = hl_bottom + 50
    if al and stat:
        stat_short = stat[:20].rsplit(' ',1)[0] if len(stat) > 20 else stat
        for ssz in [62,50,42,34]:
            fs = _font('oswald_bold', ssz)
            if draw.textbbox((0,0),stat_short,font=fs)[2] <= W-PAD*2: break
        stat_y = max(hl_bottom + 45, 620)
        stat_y = min(stat_y, H - 310)
        _paste(img, stat_short, fs, CX, stat_y+yo, ORANGE, al)
        stat_bottom = stat_y + ssz + 15

    # Body - cream text on photo
    al = _a(f,T['body'],20); yo = _y(f,T['body'],20)
    if al and body:
        fb = _font('raleway', 26)
        body_short = body[:100].rsplit(' ',1)[0] if len(body) > 100 else body
        blines = _wrap(draw, body_short, fb, W-PAD*2)
        y_cur = stat_bottom + 20
        for line in blines[:2]:
            bar = Image.new("RGBA", (W, 40), (0,0,0,int(al*0.55)))
            img.paste(bar, (0, y_cur+yo-16), bar)
            _paste(img, line, fb, CX, y_cur+yo, WHITE, int(al*0.95))
                      y_cur += 36

# ─── LOGO ────────────────────────────────────────────────────────────────────

def _render_logo(img, f, is_light=False):
    al = _a(f, int(FPS*0.8), 24)
    if al <= 0: return
    # Use dark logo on light backgrounds, white on dark
    # Both styles now full-bleed dark background - always use white logo
    logo_file = PREFERRED_LOGO
    fallbacks = FALLBACK_LOGOS
    logo = None
    for name in [logo_file] + fallbacks:
        p = os.path.join(ASSETS_DIR, name)
        if os.path.exists(p):
            try: logo = Image.open(p).convert('RGBA'); break
            except: continue
    if not logo: return
    lw = 200; lh = int(lw*logo.height/logo.width)
    lr = logo.resize((lw,lh), Image.LANCZOS)
    if al < 255:
        r,g,b,a2 = lr.split()
        a2 = a2.point(lambda x: int(x*al/255))
        lr = Image.merge('RGBA',(r,g,b,a2))
    img.paste(lr, ((W-lw)//2, H-lh-40), lr)

def _render_headshot(img, f):
    al = _a(f, int(FPS*1.2), 24)
    if al <= 0: return
    try:
        hs = Image.open(HEADSHOT_PATH).convert('RGBA')
        hw = 90; hh = int(hw*hs.height/hs.width)
        hs = hs.resize((hw,hh), Image.LANCZOS)
        if al < 255:
            r,g,b,a2 = hs.split()
            a2 = a2.point(lambda x: int(x*al/255))
            hs = Image.merge('RGBA',(r,g,b,a2))
        # Position in cream panel bottom right, above logo
        img.paste(hs, (W-hw-25, H-hh-185), hs)
    except: pass

# ─── MARKET DATA RENDERER ───────────────────────────────────────────────────

def _render_market_data(img, draw, post_data, f):
    """Dark cinematic market data — big stats, Whitney interpretation."""
    hood      = post_data.get('neighborhood', 'San Diego').upper()
    median    = post_data.get('median_price', '')
    dom       = post_data.get('days_on_market', '')
    yoy       = post_data.get('price_change_yoy', '')
    temp      = post_data.get('market_temp', 'active').upper()
    insight   = post_data.get('insight', '')
    stat      = post_data.get('stat', median)

    PAD = 50; CX = W//2
    T = {'label':int(FPS*0.4), 'hood':int(FPS*0.8), 'rule':int(FPS*1.3),
         'stats':int(FPS*1.7), 'insight':int(FPS*2.8)}

    # Market Update label
    al = _a(f,T['label'],18); yo = _y(f,T['label'],18)
    _paste(img, 'MARKET UPDATE', _font('oswald_regular',24), CX, 100+yo, CREAM, int(al*0.65))

    # Neighborhood
    al = _a(f,T['hood'],22); yo = _y(f,T['hood'],22)
    if al:
        for sz in [110,92,76,62,50]:
            fn = _font('oswald_bold',sz)
            nlines = _wrap(draw, hood, fn, W-PAD*2)
            if len(nlines) <= 2: break
        y_cur = 148
        for line in nlines[:2]:
            _paste(img, line, fn, CX, y_cur+yo, WHITE, al)
            y_cur += sz+8
        hood_bottom = y_cur+yo
    else:
        hood_bottom = 260

    # Orange rule
    al = _a(f,T['rule'],10); rule_y = hood_bottom+18
    _paste_line(img, CX-40, rule_y, CX+40, rule_y, ORANGE, al, w=4)

    # Market temp badge
    al = _a(f,T['rule'],10)
    if al and temp:
        temp_colors = {'HOT':(220,60,30), 'WARM':(210,130,30), 'COOL':(60,130,200), 'COLD':(80,120,220), 'ACTIVE':(210,85,25)}
        tc = temp_colors.get(temp, ORANGE)
        _paste(img, f'{temp} MARKET', _font('oswald_bold',28), CX, rule_y+35+yo, tc, int(al*0.9))

    # Big stats grid
    al = _a(f,T['stats'],20); yo = _y(f,T['stats'],22)
    if al:
        stat_y = rule_y + 80
        # Median price - biggest
        if median:
            _paste(img, 'MEDIAN PRICE', _font('oswald_regular',22), CX, stat_y+yo, CREAM, int(al*0.6))
            _paste(img, median, _font('oswald_bold',72), CX, stat_y+55+yo, WHITE, al)
        # DOM and YoY side by side
        if dom or yoy:
            sub_y = stat_y + 130
            if dom:
                _paste(img, 'AVG DOM', _font('oswald_regular',20), W//4, sub_y+yo, CREAM, int(al*0.6))
                _paste(img, dom.replace(' days','d').replace(' ',''), _font('oswald_bold',46), W//4, sub_y+40+yo, ORANGE, al)
            if yoy:
                color = (80,200,100) if '+' in yoy else (200,80,80)
                _paste(img, 'YoY CHANGE', _font('oswald_regular',20), 3*W//4, sub_y+yo, CREAM, int(al*0.6))
                _paste(img, yoy, _font('oswald_bold',46), 3*W//4, sub_y+40+yo, color, al)

    # Whitney insight - always below stats grid
    al = _a(f,T['insight'],22); yo = _y(f,T['insight'],22)
    if al and insight:
        fi = _font('oswald_regular',26)
        # Truncate insight to fit cleanly in 2 lines
        insight_short = insight[:110].rsplit(' ',1)[0] if len(insight) > 110 else insight
        ilines = _wrap(draw, insight_short, fi, W-PAD*2)
        # Always start below the stats grid (rule_y + 320 minimum)
        y_cur = max(rule_y + 320, 620)
        y_cur = min(y_cur, H - 280)  # never overlap logo
        for line in ilines[:2]:
            if y_cur + yo < H - 250:
                _paste(img, line, fi, CX, y_cur+yo, CREAM, int(al*0.80))
                y_cur += 36

# ─── HOME TOUR RENDERER ──────────────────────────────────────────────────────

def _render_home_tour(img, draw, post_data, f):
    """Light editorial home tour - property details, dramatic reveal."""
    hood     = post_data.get('neighborhood', 'San Diego').upper()
    price    = post_data.get('price', '')
    beds     = post_data.get('beds', '')
    baths    = post_data.get('baths', '')
    sqft     = post_data.get('sqft', '')
    feat1    = post_data.get('feature_1', '')
    feat2    = post_data.get('feature_2', '')
    feat3    = post_data.get('feature_3', '')
    stat     = post_data.get('stat', '')

    PAD = 50; CX = W//2

    T = {'label':int(FPS*0.3), 'price':int(FPS*0.7), 'hood':int(FPS*1.1),
         'rule':int(FPS*1.5), 'details':int(FPS*1.9), 'features':int(FPS*2.6)}

    # JUST LISTED label
    al = _a(f,T['label'],16); yo = _y(f,T['label'],16)
    _paste(img, 'JUST LISTED', _font('oswald_regular',24), CX, 100+yo, CREAM, int(al*0.70))

    # Price — dramatic, large
    al = _a(f,T['price'],20); yo = _y(f,T['price'],20)
    if al and price:
        _paste(img, price, _font('oswald_bold',72), CX, 185+yo, WHITE, al)

    # Neighborhood - white, full bleed
    al = _a(f,T['hood'],22); yo = _y(f,T['hood'],22)
    hood_bottom = 320
    if al:
        for sz in [92,76,62,50,42]:
            fn = _font('oswald_bold',sz)
            nlines = _wrap(draw, hood, fn, W-PAD*2)
            if len(nlines) <= 2: break
        y_cur = 300
        for line in nlines[:2]:
            _paste(img, line, fn, CX, y_cur+yo, WHITE, al)
            y_cur += sz+6
        hood_bottom = y_cur+yo+5

    # Orange rule
    al = _a(f,T['rule'],10); rule_y = hood_bottom+16
    _paste_line(img, CX-40, rule_y, CX+40, rule_y, ORANGE, al, w=4)

    # Beds/Baths/Sqft details
    al = _a(f,T['details'],18); yo = _y(f,T['details'],18)
    if al and (beds or baths or sqft):
        fd = _font('oswald_regular',34)
        details = []
        if beds:  details.append(f'{beds} BD')
        if baths: details.append(f'{baths} BA')
        if sqft:  details.append(f'{sqft} SQFT')
        detail_str = '  ·  '.join(details)
        _paste(img, detail_str, fd, CX, rule_y+42+yo, CREAM, int(al*0.90))

    # Features list
    al = _a(f,T['features'],20); yo = _y(f,T['features'],20)
    if al:
        ff = _font('oswald_regular', 28)
        feat_y = rule_y + 80
        for feat in [feat1, feat2, feat3]:
            if feat and feat_y+yo < H-250:
                feat_short = feat[:38].rsplit(' ',1)[0] if len(feat) > 38 else feat
                # Full-width semi-transparent dark bar behind each feature
                bar = Image.new('RGBA', (W, 46), (0,0,0,int(al*0.60)))
                img.paste(bar, (0, feat_y+yo-20), bar)
                # Orange arrow + white text
                _paste(img, '▶', _font('oswald_regular',18), PAD+8, feat_y+yo, ORANGE, int(al*0.9))
                _paste(img, feat_short, ff, PAD+32, feat_y+yo, WHITE, int(al*0.95), anchor='lm')
                feat_y += 50

    # Stat
    al = _a(f,T['features'],18); yo = _y(f,T['features'],18)
    if al and stat:
        stat_short = stat[:20].rsplit(' ',1)[0] if len(stat) > 20 else stat
        _paste(img, stat_short, _font('oswald_bold',36), CX, min(feat_y+30+yo, H-260), ORANGE, al)

# ─── FRAME BUILDER ───────────────────────────────────────────────────────────

def _build_frames(post_data, bg, tmp_dir):
    ct       = post_data.get('content_type','market_stat')
    is_light = ct in LIGHT_TYPES
    show_hs  = ct in HEADSHOT_TYPES

    log.info(f'Style: {"LIGHT EDITORIAL" if is_light else "DARK CINEMATIC"} | {TOTAL_FRAMES} frames')

    for f in range(TOTAL_FRAMES):
        if f % 24 == 0: log.info(f'  Frame {f}/{TOTAL_FRAMES}')

        bg_f  = _ken_burns(bg, f, TOTAL_FRAMES)

        if is_light:
            frame = _light_overlay(bg_f).convert('RGBA')
        else:
            frame = _dark_overlay(bg_f).convert('RGBA')

        draw = ImageDraw.Draw(frame)

        ct = post_data.get('content_type','market_stat')
        if ct == 'market_data':
            _render_market_data(frame, draw, post_data, f)
        elif ct == 'home_tour':
            _render_home_tour(frame, draw, post_data, f)
        elif is_light:
            _render_light(frame, draw, post_data, f)
        else:
            _render_dark(frame, draw, post_data, f)

        _render_logo(frame, f, is_light)
        if show_hs: _render_headshot(frame, f)

        frame.convert('RGB').save(
            os.path.join(tmp_dir, f'f{f:05d}.jpg'), 'JPEG', quality=85)

    log.info('Rendering complete.')

# ─── AUDIO & ENCODE ──────────────────────────────────────────────────────────

def _silence(path):
    s = np.zeros(int(44100*DURATION), dtype=np.int16)
    with wave.open(path,'w') as w:
        w.setnchannels(1); w.setsampwidth(2)
        w.setframerate(44100); w.writeframes(s.tobytes())

AUDIO_STATE_FILE = '/tmp/wbg_audio_state.json'

def _get_audio_track():
    """Pick a random mp3 from assets, rotating through all before repeating."""
    all_tracks = sorted([
        f for f in os.listdir(ASSETS_DIR)
        if f.endswith('.mp3') and os.path.exists(os.path.join(ASSETS_DIR, f))
        and f.startswith('fixed_')  # Use properly encoded tracks only
    ])
    # Fallback to any mp3 if no fixed_ tracks found
    if not all_tracks:
        all_tracks = sorted([
            f for f in os.listdir(ASSETS_DIR)
            if f.endswith('.mp3') and os.path.exists(os.path.join(ASSETS_DIR, f))
        ])
    if not all_tracks:
        return None
    state = {}
    try:
        if os.path.exists(AUDIO_STATE_FILE):
            with open(AUDIO_STATE_FILE, 'r') as f:
                state = json.load(f)
    except:
        state = {}
    used   = set(state.get('used_tracks', []))
    unused = [t for t in all_tracks if t not in used]
    if not unused:
        log.info('Audio pool exhausted, resetting')
        unused = all_tracks
        used   = set()
    chosen = random.choice(unused)
    used.add(chosen)
    state['used_tracks'] = list(used)
    try:
        with open(AUDIO_STATE_FILE, 'w') as f:
            json.dump(state, f)
    except:
        pass
    log.info(f'Audio: {chosen} ({len(unused)-1} unused of {len(all_tracks)})')
    return os.path.join(ASSETS_DIR, chosen)

def _prepare_audio(tmp_dir, post_data=None):
    """Embed a royalty-free music track directly into the video."""
    audio_path = os.path.join(tmp_dir, 'audio.wav')
    track = _get_audio_track()
    if track and os.path.exists(track):
        try:
            converted = os.path.join(tmp_dir, 'music.wav')
            subprocess.run([
                imageio_ffmpeg.get_ffmpeg_exe(), '-y',
                '-i', track,
                '-t', str(DURATION),
                '-af', f'afade=t=in:st=0:d=1,afade=t=out:st={DURATION-2}:d=2,volume=0.8',
                '-ar', '44100', '-ac', '1', converted
            ], check=True, capture_output=True, timeout=30)
            log.info(f'Music embedded: {os.path.basename(track)}')
            return converted
        except Exception as e:
            log.warning(f'Music failed: {e}')
    _silence(audio_path)
    return audio_path


# ─── ENTRY ───────────────────────────────────────────────────────────────────

def generate_reel(post_data: dict) -> str:
    cloudinary.config(
        cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key=os.getenv('CLOUDINARY_API_KEY'),
        api_secret=os.getenv('CLOUDINARY_API_SECRET')
    )
    tmp = tempfile.mkdtemp(prefix='wbg_')
    try:
        ct   = post_data.get('content_type','market_stat')
        hood = post_data.get('neighborhood','')

        log.info(f'Generating reel: {ct} | {hood}')
        log.info('Fetching background...')
        bg = _fetch_bg(ct, hood)

        log.info('Building frames...')
        _build_frames(post_data, bg, tmp)

        audio = _prepare_audio(tmp, post_data)

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
