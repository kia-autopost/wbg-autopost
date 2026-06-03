"""
WBG Video Generator - V3 Cinematic Edition
Design direction: Editorial luxury real estate
- Full-bleed Unsplash photo background with slow Ken Burns zoom
- Massive condensed typography, text slides up cinematically
- Near-black overlay, cream/white text
- Single thin Blaze Orange accent line (not everywhere)
- White WBG logo, small and tasteful bottom center
- Headshot only on buyer_seller_tip and hot_take
- One logo picked at start, held for entire video
"""
import os, tempfile, shutil, wave, subprocess, random, urllib.request, json, logging
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import imageio_ffmpeg
import cloudinary
import cloudinary.uploader

log = logging.getLogger('WBG')

ASSETS_DIR    = os.path.join(os.path.dirname(__file__), 'assets')
HEADSHOT_PATH = os.path.join(ASSETS_DIR, 'headshot.png')

# V3: Single preferred white logo for dark backgrounds
PREFERRED_LOGO = 'Logo_Primary_White_01.png'
FALLBACK_LOGOS = [
    'exp_Logo_Secondary_White_01.png',
    'WBG LOGO - ExpLogoLogoPrimaryWhite01.png',
    'exp_Logo_Primary_Dune_01.png',
]

# Font paths
FONT_PATHS = [
    os.path.join(ASSETS_DIR, 'Caladea-Regular.ttf'),
    os.path.join(ASSETS_DIR, 'Caladea-Bold.ttf'),
]

W, H          = 720, 1280
FPS           = 24
DURATION      = 10
TOTAL_FRAMES  = DURATION * FPS  # 240 frames

# WBG Brand colors - V3 restrained palette
BLACK     = (8, 8, 8)
ORANGE    = (210, 85, 25)
WHITE     = (255, 255, 255)
CREAM     = (242, 238, 230)
DARK_GRAY = (20, 20, 20)

UNSPLASH_KEY = os.getenv('UNSPLASH_ACCESS_KEY', '')

SD_QUERIES = {
    'sd_hidden_gem':      ['san diego neighborhood aerial', 'san diego coastline', 'california coastal town', 'san diego architecture'],
    'current_event_tie':  ['san diego skyline sunset', 'san diego downtown', 'california city aerial', 'san diego waterfront'],
    'hot_take':           ['modern luxury interior', 'contemporary home exterior', 'luxury real estate', 'modern architecture california'],
    'hyper_local_intel':  ['san diego neighborhood street', 'california suburb aerial', 'san diego hills', 'san diego residential'],
    'sd_lifestyle_hook':  ['san diego beach golden hour', 'la jolla cove sunrise', 'coronado bridge sunset', 'del mar bluffs'],
    'property_spotlight': ['luxury home pool san diego', 'modern house exterior', 'mediterranean villa california', 'beach house interior'],
    'market_stat':        ['san diego skyline night', 'san diego aerial cityscape', 'california coast aerial', 'san diego harbor'],
    'buyer_seller_tip':   ['modern home interior minimal', 'luxury kitchen interior', 'open plan living room', 'real estate modern home'],
    'investor_quote':     ['city skyline dusk', 'modern architecture glass', 'luxury penthouse view', 'urban skyline california'],
    'san_diego_lifestyle':['san diego beach lifestyle', 'pacific beach sunset', 'ocean beach california', 'la jolla sunset cliffs'],
}

# ─── LOGO ────────────────────────────────────────────────────────────────────

def _load_logo():
    path = os.path.join(ASSETS_DIR, PREFERRED_LOGO)
    if os.path.exists(path):
        try:
            return Image.open(path).convert('RGBA')
        except:
            pass
    for name in FALLBACK_LOGOS:
        path = os.path.join(ASSETS_DIR, name)
        if os.path.exists(path):
            try:
                return Image.open(path).convert('RGBA')
            except:
                continue
    return None

# ─── FONTS ───────────────────────────────────────────────────────────────────

def _load_font(size):
    for path in FONT_PATHS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
    return ImageFont.load_default()

# ─── BACKGROUND ──────────────────────────────────────────────────────────────

def _fetch_background(content_type):
    if UNSPLASH_KEY:
        try:
            queries = SD_QUERIES.get(content_type, ['san diego'])
            query = random.choice(queries).replace(' ', '+')
            url = f'https://api.unsplash.com/photos/random?query={query}&orientation=portrait&client_id={UNSPLASH_KEY}'
            req = urllib.request.Request(url, headers={'Accept-Version': 'v1'})
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read())
            img_url = data['urls']['regular']
            with urllib.request.urlopen(img_url, timeout=8) as r:
                img_data = r.read()
            tmp = tempfile.mktemp(suffix='.jpg')
            with open(tmp, 'wb') as f:
                f.write(img_data)
            bg = Image.open(tmp).convert('RGB')
            os.unlink(tmp)
            # Size larger for Ken Burns zoom room
            ratio = max((W * 1.1) / bg.width, (H * 1.1) / bg.height)
            new_w = int(bg.width * ratio)
            new_h = int(bg.height * ratio)
            bg = bg.resize((new_w, new_h), Image.LANCZOS)
            log.info('Unsplash background fetched OK')
            return bg
        except Exception as e:
            log.warning(f'Unsplash failed, using gradient: {e}')
    return _cinematic_gradient()

def _cinematic_gradient():
    img = Image.new('RGB', (int(W * 1.1), int(H * 1.1)), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    for y in range(int(H * 1.1)):
        t = y / (H * 1.1)
        r = int(18 + t * 12)
        g = int(16 + t * 10)
        b = int(20 + t * 15)
        draw.line([(0, y), (int(W * 1.1), y)], fill=(r, g, b))
    return img

# ─── KEN BURNS ───────────────────────────────────────────────────────────────

def _ken_burns_frame(bg, frame_idx, total_frames):
    bg_w, bg_h = bg.size
    t = frame_idx / max(total_frames - 1, 1)
    t_eased = t * t * (3 - 2 * t)

    # Slow push in: starts slightly wider, ends at exact canvas size
    zoom_start = 1.08
    zoom_end   = 1.0

    # Crop size starts larger, shrinks to W x H
    crop_w = int(W * (zoom_start + (zoom_end - zoom_start) * t_eased))
    crop_h = int(H * (zoom_start + (zoom_end - zoom_start) * t_eased))
    crop_w = max(crop_w, W)
    crop_h = max(crop_h, H)

    # Center with subtle drift
    cx = bg_w // 2 + int(15 * (1 - t_eased))
    cy = bg_h // 2 + int(10 * (1 - t_eased))

    left = max(0, min(cx - crop_w // 2, bg_w - crop_w))
    top  = max(0, min(cy - crop_h // 2, bg_h - crop_h))

    cropped = bg.crop((left, top, left + crop_w, top + crop_h))
    if cropped.size != (W, H):
        cropped = cropped.resize((W, H), Image.LANCZOS)
    return cropped

# ─── OVERLAY ─────────────────────────────────────────────────────────────────

def _cinematic_overlay(frame_img):
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(H):
        t = y / H
        if t < 0.42:
            alpha = int(220 * (1 - t / 0.42) ** 1.8)
        elif t > 0.52:
            alpha = int(250 * ((t - 0.52) / 0.48) ** 1.1)
        else:
            alpha = 25
        draw.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
    result = Image.alpha_composite(frame_img.convert('RGBA'), overlay)
    return result.convert('RGB')

# ─── TEXT HELPERS ────────────────────────────────────────────────────────────

def _wrap_text(draw, text, font, max_w):
    words = text.split()
    lines, cur = [], ''
    for w in words:
        test = (cur + ' ' + w).strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def _alpha_at(f, start, fade=14):
    if f < start: return 0
    elapsed = f - start
    if elapsed >= fade: return 255
    return int(255 * (elapsed / fade))

def _offset_at(f, start, slide=18):
    if f < start: return 40
    elapsed = f - start
    if elapsed >= slide: return 0
    t = elapsed / slide
    t_e = t * t * (3 - 2 * t)
    return int(40 * (1 - t_e))

def _draw_txt(img, text, font, x, y, color, alpha, anchor='mm'):
    if alpha <= 0: return
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r, g, b = color
    d.text((x, y), text, font=font, fill=(r, g, b, alpha), anchor=anchor)
    img.paste(layer, mask=layer)

def _draw_ln(img, x1, y1, x2, y2, color, alpha, width=3):
    if alpha <= 0: return
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r, g, b = color
    d.line([(x1, y1), (x2, y2)], fill=(r, g, b, alpha), width=width)
    img.paste(layer, mask=layer)

# ─── RENDERERS ───────────────────────────────────────────────────────────────

def _render_sd_hidden_gem(img, draw, post_data, f):
    hood    = post_data.get('neighborhood', 'San Diego').upper()
    hl      = post_data.get('headline', '')
    insight = post_data.get('insight', '')
    stat    = str(post_data.get('stat', ''))

    t0, t1, t2, t3, t4, t5 = int(FPS*1.0), int(FPS*1.5), int(FPS*2.0), int(FPS*2.3), int(FPS*3.0), int(FPS*3.8)

    a = _alpha_at(f, t0); yo = _offset_at(f, t0)
    _draw_txt(img, 'LIFE IN', _load_font(22), W//2, 110+yo, CREAM, int(a*0.65))

    a = _alpha_at(f, t1, 20); yo = _offset_at(f, t1, 22)
    fn = _load_font(88)
    nlines = _wrap_text(draw, hood, fn, W-60)
    for i, line in enumerate(nlines[:2]):
        _draw_txt(img, line, fn, W//2, 195+i*92+yo, WHITE, a)

    a = _alpha_at(f, t2, 10)
    lx = (W-50)//2; ly = 200 + min(len(nlines),2)*92 + 18
    _draw_ln(img, lx, ly, lx+50, ly, ORANGE, a)

    a = _alpha_at(f, t3); yo = _offset_at(f, t3)
    fh = _load_font(36)
    hlines = _wrap_text(draw, hl, fh, W-80)
    for i, line in enumerate(hlines[:2]):
        _draw_txt(img, line, fh, W//2, ly+50+i*50+yo, CREAM, int(a*0.95))

    a = _alpha_at(f, t4); yo = _offset_at(f, t4)
    fb = _load_font(26)
    blines = _wrap_text(draw, insight, fb, W-100)
    body_y = ly+50+len(hlines)*50+20
    for i, line in enumerate(blines[:3]):
        _draw_txt(img, line, fb, W//2, body_y+i*38+yo, CREAM, int(a*0.72))

    if stat:
        a = _alpha_at(f, t5); yo = _offset_at(f, t5)
        _draw_txt(img, stat, _load_font(72), W//2, 710+yo, ORANGE, a)

def _render_market_stat(img, draw, post_data, f):
    stat    = str(post_data.get('stat', ''))
    context = post_data.get('context', '')

    t0, t1, t2, t3 = int(FPS*0.8), int(FPS*1.4), int(FPS*2.0), int(FPS*2.5)

    a = _alpha_at(f, t0); yo = _offset_at(f, t0)
    _draw_txt(img, 'SAN DIEGO MARKET UPDATE', _load_font(22), W//2, 145+yo, CREAM, int(a*0.6))

    a = _alpha_at(f, t1, 22); yo = _offset_at(f, t1, 24)
    fs = _load_font(96)
    slines = _wrap_text(draw, stat, fs, W-40)
    for i, line in enumerate(slines[:2]):
        _draw_txt(img, line, fs, W//2, 310+i*104+yo, WHITE, a)

    a = _alpha_at(f, t2, 8)
    lx = (W-60)//2
    _draw_ln(img, lx, 500, lx+60, 500, ORANGE, a)

    a = _alpha_at(f, t3); yo = _offset_at(f, t3)
    fc = _load_font(30)
    clines = _wrap_text(draw, context, fc, W-90)
    for i, line in enumerate(clines[:3]):
        _draw_txt(img, line, fc, W//2, 550+i*46+yo, CREAM, int(a*0.85))

def _render_hot_take(img, draw, post_data, f):
    hood    = post_data.get('neighborhood', '').upper()
    hl      = post_data.get('headline', '')
    insight = post_data.get('insight', '')

    t0, t1, t2, t3, t4 = int(FPS*0.8), int(FPS*1.2), int(FPS*1.8), int(FPS*2.2), int(FPS*2.7)

    a = _alpha_at(f, t0); yo = _offset_at(f, t0)
    _draw_txt(img, 'HOT TAKE', _load_font(20), W//2, 112+yo, ORANGE, int(a*0.9))

    if hood:
        a = _alpha_at(f, t1); yo = _offset_at(f, t1)
        _draw_txt(img, hood, _load_font(64), W//2, 198+yo, WHITE, a)

    a = _alpha_at(f, t2, 20); yo = _offset_at(f, t2, 20)
    fh = _load_font(44)
    hlines = _wrap_text(draw, hl, fh, W-70)
    sy = 275 if hood else 225
    for i, line in enumerate(hlines[:3]):
        _draw_txt(img, line, fh, W//2, sy+i*60+yo, WHITE, a)

    a = _alpha_at(f, t3, 8)
    lx = (W-50)//2; ly = sy+len(hlines)*60+18
    _draw_ln(img, lx, ly, lx+50, ly, ORANGE, a)

    a = _alpha_at(f, t4); yo = _offset_at(f, t4)
    fb = _load_font(28)
    blines = _wrap_text(draw, insight, fb, W-100)
    for i, line in enumerate(blines[:3]):
        _draw_txt(img, line, fb, W//2, ly+40+i*44+yo, CREAM, int(a*0.8))

def _render_generic(img, draw, post_data, f):
    ct   = post_data.get('content_type', '')
    hood = post_data.get('neighborhood', 'San Diego').upper()
    hl   = post_data.get('headline', post_data.get('insight', ''))
    body = post_data.get('real_estate_tie', post_data.get('context', post_data.get('tip', '')))
    stat = str(post_data.get('stat', ''))

    labels = {
        'hyper_local_intel':  'MARKET INTEL',
        'sd_lifestyle_hook':  'SD LIVING',
        'buyer_seller_tip':   'PRO TIP',
        'investor_quote':     'INVEST IN SD',
        'san_diego_lifestyle':'LIFE IN SD',
        'current_event_tie':  'RIGHT NOW IN SD',
        'property_spotlight': 'JUST LISTED',
    }
    label = labels.get(ct, 'SAN DIEGO')

    t0, t1, t2, t3, t4, t5 = int(FPS*0.8), int(FPS*1.3), int(FPS*1.9), int(FPS*2.3), int(FPS*3.1), int(FPS*3.7)

    a = _alpha_at(f, t0); yo = _offset_at(f, t0)
    _draw_txt(img, label, _load_font(22), W//2, 115+yo, CREAM, int(a*0.65))

    a = _alpha_at(f, t1, 22); yo = _offset_at(f, t1, 22)
    fn = _load_font(76)
    nlines = _wrap_text(draw, hood, fn, W-60)
    for i, line in enumerate(nlines[:2]):
        _draw_txt(img, line, fn, W//2, 202+i*84+yo, WHITE, a)

    a = _alpha_at(f, t2, 8)
    lx = (W-50)//2; ly = 202+min(len(nlines),2)*84+14
    _draw_ln(img, lx, ly, lx+50, ly, ORANGE, a)

    a = _alpha_at(f, t3); yo = _offset_at(f, t3)
    fh = _load_font(36)
    hlines = _wrap_text(draw, hl, fh, W-80)
    for i, line in enumerate(hlines[:2]):
        _draw_txt(img, line, fh, W//2, ly+50+i*52+yo, CREAM, int(a*0.95))

    if body:
        a = _alpha_at(f, t4); yo = _offset_at(f, t4)
        fb = _load_font(26)
        blines = _wrap_text(draw, body, fb, W-100)
        by = ly+50+len(hlines)*52+20
        for i, line in enumerate(blines[:3]):
            _draw_txt(img, line, fb, W//2, by+i*38+yo, CREAM, int(a*0.72))

    if stat:
        a = _alpha_at(f, t5); yo = _offset_at(f, t5)
        _draw_txt(img, stat, _load_font(64), W//2, 715+yo, ORANGE, a)

# ─── FRAME LOOP ──────────────────────────────────────────────────────────────

HEADSHOT_TYPES = {'buyer_seller_tip', 'hot_take'}

def _build_frames(post_data, bg, logo, tmp_dir):
    ct = post_data.get('content_type', 'market_stat')
    show_headshot = ct in HEADSHOT_TYPES
    t_logo = int(FPS * 1.0)
    t_hs   = int(FPS * 1.5)

    log.info(f'Rendering {TOTAL_FRAMES} frames...')

    for f in range(TOTAL_FRAMES):
        if f % 24 == 0:
            log.info(f'  Frame {f}/{TOTAL_FRAMES}')

        bg_frame = _ken_burns_frame(bg, f, TOTAL_FRAMES)
        frame    = _cinematic_overlay(bg_frame).convert('RGBA')
        draw     = ImageDraw.Draw(frame)

        # Content
        if ct == 'sd_hidden_gem':
            _render_sd_hidden_gem(frame, draw, post_data, f)
        elif ct == 'market_stat':
            _render_market_stat(frame, draw, post_data, f)
        elif ct == 'hot_take':
            _render_hot_take(frame, draw, post_data, f)
        else:
            _render_generic(frame, draw, post_data, f)

        # Logo - bottom center, fades in once
        logo_a = _alpha_at(f, t_logo, 20)
        if logo and logo_a > 0:
            lw = 160
            lh = int(lw * logo.height / logo.width)
            lr = logo.resize((lw, lh), Image.LANCZOS)
            if logo_a < 255:
                r2, g2, b2, a2 = lr.split()
                a2 = a2.point(lambda x: int(x * logo_a / 255))
                lr = Image.merge('RGBA', (r2, g2, b2, a2))
            frame.paste(lr, ((W-lw)//2, H-lh-35), lr)

        # Headshot
        if show_headshot:
            hs_a = _alpha_at(f, t_hs, 20)
            if hs_a > 0:
                try:
                    hs = Image.open(HEADSHOT_PATH).convert('RGBA')
                    hw = 130; hh = int(hw * hs.height / hs.width)
                    hs = hs.resize((hw, hh), Image.LANCZOS)
                    if hs_a < 255:
                        r2, g2, b2, a2 = hs.split()
                        a2 = a2.point(lambda x: int(x * hs_a / 255))
                        hs = Image.merge('RGBA', (r2, g2, b2, a2))
                    frame.paste(hs, (W-hw-20, H-hh-160), hs)
                except:
                    pass

        frame.convert('RGB').save(
            os.path.join(tmp_dir, f'f{f:05d}.jpg'), 'JPEG', quality=85)

    log.info('Frame rendering complete.')

# ─── SILENCE ─────────────────────────────────────────────────────────────────

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
        log.info('Loading logo...')
        logo = _load_logo()
        log.info(f'Logo: {PREFERRED_LOGO if logo else "not found"}')

        log.info('Fetching background...')
        bg = _fetch_background(post_data.get('content_type', 'market_stat'))

        log.info('Building cinematic frames...')
        _build_frames(post_data, bg, logo, tmp)

        log.info('Generating audio...')
        audio_path = os.path.join(tmp, 'audio.wav')
        _gen_silence(audio_path)

        log.info('Running ffmpeg...')
        out_path = os.path.join(tmp, 'reel.mp4')
        cmd = [
            imageio_ffmpeg.get_ffmpeg_exe(), '-y',
            '-framerate', str(FPS),
            '-i', os.path.join(tmp, 'f%05d.jpg'),
            '-i', audio_path,
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-pix_fmt', 'yuv420p', '-t', str(DURATION),
            '-c:a', 'aac', '-b:a', '128k', '-shortest',
            out_path
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=180)
        log.info('ffmpeg complete.')

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
