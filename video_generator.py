"""
WBG Video Generator - V5 Dual Style Edition
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
DARK_TYPES  = {'sd_hidden_gem', 'market_stat', 'current_event_tie', 'investor_quote'}
LIGHT_TYPES = {'buyer_seller_tip', 'hot_take', 'hyper_local_intel', 'sd_lifestyle_hook',
               'san_diego_lifestyle', 'property_spotlight'}
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

def _fetch_bg(content_type, neighborhood='', size_w=None, size_h=None):
    bw = size_w or int(W * 1.12)
    bh = size_h or int(H * 1.12)

    # Try Unsplash API
    if UNSPLASH_KEY:
        try:
            if neighborhood and neighborhood.lower() not in ('san diego',''):
                # Anchor to real estate/residential to avoid nature/ocean shots
                suffixes = ['california real estate', 'california homes', 'california residential street', 'san diego neighborhood']
                suffix = random.choice(suffixes)
                query = (neighborhood.lower() + ' ' + suffix).replace(' ','+')
            else:
                queries = SD_QUERIES.get(content_type, ['san diego real estate'])
                query = random.choice(queries).replace(' ','+')
            url = f'https://api.unsplash.com/photos/random?query={query}&orientation=portrait&client_id={UNSPLASH_KEY}'
            req = urllib.request.Request(url, headers={'Accept-Version':'v1'})
            with urllib.request.urlopen(req, timeout=6) as r:
                data = json.loads(r.read())
            with urllib.request.urlopen(data['urls']['regular'], timeout=10) as r:
                img_data = r.read()
            tmp = tempfile.mktemp(suffix='.jpg')
            open(tmp,'wb').write(img_data)
            bg = Image.open(tmp).convert('RGB'); os.unlink(tmp)
            ratio = max(bw/bg.width, bh/bg.height)
            bg = bg.resize((int(bg.width*ratio), int(bg.height*ratio)), Image.LANCZOS)
            log.info('Unsplash bg loaded')
            return bg
        except Exception as e:
            log.warning(f'Unsplash failed: {e}')

    # Try Pexels
    try:
        ids = PEXELS_BY_TYPE.get(content_type, ['2119714','1396122','1642125'])
        pid = random.choice(ids)
        url = f'https://images.pexels.com/photos/{pid}/pexels-photo-{pid}.jpeg?auto=compress&cs=tinysrgb&w={bw}&h={bh}&fit=crop'
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            img_data = r.read()
        tmp = tempfile.mktemp(suffix='.jpg')
        open(tmp,'wb').write(img_data)
        bg = Image.open(tmp).convert('RGB'); os.unlink(tmp)
        ratio = max(bw/bg.width, bh/bg.height)
        if ratio > 1: bg = bg.resize((int(bg.width*ratio), int(bg.height*ratio)), Image.LANCZOS)
        log.info(f'Pexels bg loaded: {bg.size}')
        return bg
    except Exception as e:
        log.warning(f'Pexels failed: {e}')

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
    """Very heavy dark overlay - photo gives atmosphere, text stays king."""
    ov = Image.new('RGBA', (W,H), (0,0,0,0))
    d  = ImageDraw.Draw(ov)
    for y in range(H):
        t = y/H
        if t < 0.50:
            # Top half: very dark so text pops
            a = int(230*(1-t/0.50)**1.2)
            a = max(a, 160)
        elif t > 0.55:
            # Bottom half: even darker for logo zone
            a = int(200 + int(55*((t-0.55)/0.45)))
        else:
            # Narrow window: slightly lighter to let photo breathe
            a = 140
        d.line([(0,y),(W,y)], fill=(0,0,0,min(a,245)))
    return Image.alpha_composite(bg_frame.convert('RGBA'), ov).convert('RGB')

def _light_overlay(bg_frame):
    """
    Light editorial style: photo occupies top 58%, 
    cream panel slides up from bottom 42%.
    """
    frame = bg_frame.copy().convert('RGBA')
    
    # Subtle dark gradient at very top of photo (for label legibility)
    top_grad = Image.new('RGBA', (W,H), (0,0,0,0))
    tg = ImageDraw.Draw(top_grad)
    for y in range(int(H*0.25)):
        a = int(120*(1-y/(H*0.25))**1.2)
        tg.line([(0,y),(W,y)], fill=(0,0,0,a))
    frame = Image.alpha_composite(frame, top_grad)

    # Cream panel bottom 45%
    panel_top = int(H * 0.55)
    panel = Image.new('RGBA', (W,H), (0,0,0,0))
    pd = ImageDraw.Draw(panel)
    # Soft feathered edge at panel top
    feather = 60
    for y in range(feather):
        a = int(245 * (y/feather)**1.8)
        r,g,b = CREAM2
        pd.line([(0, panel_top+y),(W, panel_top+y)], fill=(r,g,b,a))
    pd.rectangle([(0, panel_top+feather),(W,H)], fill=(*CREAM2, 252))
    frame = Image.alpha_composite(frame, panel)

    return frame.convert('RGB')

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
        body_short = body[:120].rsplit(' ',1)[0] if len(body) > 120 else body
        blines = _wrap(draw, body_short, fb, W-PAD*2)
        y_cur = hl_bottom+36
        for line in blines[:2]:
            _paste(img, line, fb, CX+1, y_cur+yo+1, BLACK, int(al*0.45))
            _paste(img, line, fb, CX, y_cur+yo, CREAM, int(al*0.85))
            y_cur += 38
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
    }
    label = labels.get(ct,'SAN DIEGO')

    PAD = 45; CX = W//2
    PANEL_TOP = int(H * 0.52)

    T = {'label':int(FPS*0.4), 'hood':int(FPS*0.85), 'rule':int(FPS*1.3),
         'hl':int(FPS*1.6), 'stat':int(FPS*2.2), 'body':int(FPS*2.8)}

    # Label - top of photo, white, more visible
    al = _a(f,T['label'],18); yo = _y(f,T['label'],18)
    _paste(img, label, _font('oswald_regular',26), CX, 95+yo, WHITE, int(al*0.90))

    # Neighborhood - MASSIVE black in cream panel
    al = _a(f,T['hood'],22); yo = _y(f,T['hood'],22)
    hood_bottom = PANEL_TOP + 90
    if al:
        for sz in [100,84,70,58,48]:
            fn = _font('oswald_bold',sz)
            nlines = _wrap(draw, hood, fn, W-PAD*2)
            if len(nlines) <= 2: break
        y_cur = PANEL_TOP + 52
        for line in nlines[:2]:
            _paste(img, line, fn, CX, y_cur+yo, BLACK, al)
            y_cur += sz+8
        hood_bottom = y_cur + yo + 5

    # Orange rule
    al = _a(f,T['rule'],10); rule_y = hood_bottom + 16
    _paste_line(img, CX-35, rule_y, CX+35, rule_y, ORANGE, al, w=3)

    # Headline - black oswald, fits 1-2 lines
    al = _a(f,T['hl'],18); yo = _y(f,T['hl'],20)
    hl_bottom = rule_y + 42
    if al and hl:
        for fsz in [34,28,24]:
            fh = _font('oswald_regular', fsz)
            hlines = _wrap(draw, hl, fh, W-PAD*2)
            if len(hlines) <= 2: break
        y_cur = rule_y + 42
        for line in hlines[:2]:
            _paste(img, line, fh, CX, y_cur+yo, DKGRAY, int(al*0.95))
            y_cur += fsz + 10
        hl_bottom = y_cur + yo

    # Stat - below headline with guaranteed clearance
    al = _a(f,T['stat'],18); yo = _y(f,T['stat'],18)
    stat_bottom = hl_bottom + 60
    if al and stat:
        stat_short = stat[:20].rsplit(' ',1)[0] if len(stat) > 20 else stat
        for ssz in [52,42,34,28]:
            fs = _font('oswald_bold', ssz)
            if draw.textbbox((0,0),stat_short,font=fs)[2] <= W-PAD*2: break
        # Always at least 40px below hl_bottom, never in logo zone
        stat_y = max(hl_bottom + 40, PANEL_TOP + 200)
        stat_y = min(stat_y, H - 310)
        _paste(img, stat_short, fs, CX, stat_y+yo, ORANGE, al)
        stat_bottom = stat_y + ssz + 15

    # Body - darker, more visible, after stat
    al = _a(f,T['body'],20); yo = _y(f,T['body'],20)
    if al and body:
        fb = _font('raleway', 24)
        body_short = body[:110].rsplit(' ',1)[0] if len(body) > 110 else body
        blines = _wrap(draw, body_short, fb, W-PAD*2)
        y_cur = stat_bottom + 22
        for line in blines[:2]:
            if y_cur + yo < H - 250:  # never overlap logo
                _paste(img, line, fb, CX, y_cur+yo, DKGRAY, int(al*0.70))
                y_cur += 34

# ─── LOGO ────────────────────────────────────────────────────────────────────

def _render_logo(img, f, is_light=False):
    al = _a(f, int(FPS*0.8), 24)
    if al <= 0: return
    # Use dark logo on light backgrounds, white on dark
    logo_file = DARK_LOGO if is_light else PREFERRED_LOGO
    fallbacks = [PREFERRED_LOGO] + FALLBACK_LOGOS if is_light else FALLBACK_LOGOS
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

        if is_light:
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

        audio = os.path.join(tmp,'audio.wav')
        _silence(audio)

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
