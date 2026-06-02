"""
WBG Video Generator - Premium Edition
Features:
- Real San Diego property/lifestyle photos from Unsplash API
- Animated text reveal (fade in per line)
- Headshot on every post
- Premium Playfair Display typography
- Gradient overlays with orange glow
- Rotating logo selection from all WBG brand variants
- 720p efficient encoding
"""
import os, tempfile, shutil, wave, subprocess, random, urllib.request, json, logging
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import imageio_ffmpeg
import cloudinary
import cloudinary.uploader

log = logging.getLogger('WBG')

ASSETS_DIR    = os.path.join(os.path.dirname(__file__), 'assets')
FONT_PATH     = os.path.join(ASSETS_DIR, 'Caladea-Regular.ttf')
HEADSHOT_PATH = os.path.join(ASSETS_DIR, 'headshot.png')

# All WBG logo variants - randomly selected per post
LOGO_FILES = [
    'exp_Logo_Primary_Dune_01.png',
    'exp_Logo_Primary_Dune_02.png',
    'exp_Logo_Secondary_Dune_01.png',
    'exp_Logo_Secondary_White_01.png',
    'Logo_Primary_White_01.png',
    'Logomark_Primary_Dune_01 (1).png',
    'WBG LOGO - ExpLogoLogoPrimaryWhite01.png',
]

W, H     = 720, 1280
FPS      = 24
DURATION = 8          # Reduced from 15 to cut render time in half
FADE_FRAMES = int(FPS * 0.8)

# WBG Brand colors
BLACK      = (12, 12, 12)
ORANGE     = (210, 85, 25)
ORANGE_DIM = (160, 60, 15)
WHITE      = (255, 255, 255)
CREAM      = (245, 240, 235)
GRAY       = (160, 160, 160)

UNSPLASH_KEY   = os.getenv('UNSPLASH_ACCESS_KEY', '')
AGENT_NAME     = 'Whitney Pierce'
AGENT_TITLE    = 'Whissel Beer Group | eXp Realty'
AGENT_PHONE    = '925-940-3025'
AGENT_HANDLE   = '@Whitney_Pierce_WBG'

SD_QUERIES = {
    'property_spotlight':  ['luxury home san diego', 'modern house california', 'beach house san diego', 'mediterranean villa'],
    'market_stat':         ['san diego skyline', 'san diego aerial', 'la jolla cove california', 'san diego downtown'],
    'buyer_seller_tip':    ['house keys', 'home interior modern', 'open house', 'real estate handshake'],
    'investor_quote':      ['city skyline sunset', 'modern architecture', 'real estate investment', 'luxury apartment'],
    'san_diego_lifestyle': ['san diego beach sunset', 'la jolla california', 'coronado island', 'del mar california'],
}

def _get_background(content_type):
    """Fetch a real photo from Unsplash or fall back to gradient."""
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
            bg = Image.open(tmp).convert('RGBA')
            os.unlink(tmp)
            ratio = max(W/bg.width, H/bg.height)
            new_w, new_h = int(bg.width*ratio), int(bg.height*ratio)
            bg = bg.resize((new_w, new_h), Image.LANCZOS)
            left = (new_w - W) // 2
            top  = (new_h - H) // 2
            bg = bg.crop((left, top, left+W, top+H))
            log.info('Unsplash background fetched OK')
            return bg
        except Exception as e:
            log.warning(f'Unsplash failed, using gradient fallback: {e}')
    return _gradient_bg()

def _gradient_bg():
    """Rich dark gradient background with subtle orange glow."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(15 + t * 8)
        g = int(12 + t * 5)
        b = int(12 + t * 5)
        draw.line([(0, y), (W, y)], fill=(r, g, b, 255))
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for i in range(120, 0, -1):
        alpha = int((120 - i) * 1.2)
        gd.ellipse([(-i, H - i*2), (i*3, H + i)], fill=(*ORANGE_DIM, alpha))
    img = Image.alpha_composite(img, glow)
    return img

def _dark_overlay(bg):
    """Add dark overlay so text is always readable."""
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(H):
        t = y / H
        if t < 0.35:
            alpha = int(180 - t * 100)
        elif t > 0.65:
            alpha = int(130 + (t - 0.65) * 300)
        else:
            alpha = 140
        draw.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(bg.convert('RGBA'), overlay)

def _load_font(size, bold=False):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except:
        return ImageFont.load_default()

def _tw(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]

def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if draw.textbbox((0, 0), t, font=font)[2] <= max_w:
            cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def _get_logo():
    """Pick a random WBG logo variant."""
    random.shuffle(LOGO_FILES)
    for name in LOGO_FILES:
        path = os.path.join(ASSETS_DIR, name)
        if os.path.exists(path):
            try:
                logo = Image.open(path).convert('RGBA')
                return logo, name
            except:
                continue
    for f in os.listdir(ASSETS_DIR):
        if f.startswith('logo') and f.endswith('.png'):
            try:
                logo = Image.open(os.path.join(ASSETS_DIR, f)).convert('RGBA')
                return logo, f
            except:
                continue
    return None, None

def _add_logo(img):
    """Add randomly selected WBG logo."""
    logo, name = _get_logo()
    if not logo:
        return
    lw = 200
    lh = int(lw * logo.height / logo.width)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    x = (W - lw) // 2
    y = H - lh - 40
    img.paste(logo, (x, y), logo)

def _add_headshot(img, size=160, pos='right'):
    """Add headshot to every post."""
    try:
        hs = Image.open(HEADSHOT_PATH).convert('RGBA')
        hw = size
        hh = int(hw * hs.height / hs.width)
        hs = hs.resize((hw, hh), Image.LANCZOS)
        x = W - hw - 25 if pos == 'right' else 25
        y = H - hh - 155
        img.paste(hs, (x, y), hs)
    except:
        pass

def _orange_bar(draw, y, width=60, x=None):
    """Decorative orange accent bar."""
    if x is None:
        x = (W - width) // 2
    draw.rectangle([(x, y), (x + width, y + 4)], fill=(*ORANGE, 255))

def build_frame(post_data, bg_img=None):
    """Build a single premium frame."""
    ct = post_data.get('content_type', 'market_stat')

    if bg_img is None:
        bg_img = _gradient_bg()

    img = _dark_overlay(bg_img)
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (W, 6)], fill=(*ORANGE, 255))
    draw.rectangle([(0, H - 6), (W, H)], fill=(*ORANGE, 255))

    if ct == 'property_spotlight':
        price = post_data.get('price_range', '')
        hood  = post_data.get('neighborhood', 'San Diego')
        hl    = post_data.get('headline', '')
        beds  = post_data.get('beds', '')
        baths = post_data.get('baths', '')
        sqft  = post_data.get('sqft', '')
        hl2   = post_data.get('highlight', '')
        draw.text((W//2, 80),  'FOR SALE', font=_load_font(26), fill=(*ORANGE, 230), anchor='mm')
        draw.text((W//2, 140), hood.upper(), font=_load_font(58), fill=(*WHITE, 255), anchor='mm')
        _orange_bar(draw, 178, 80)
        draw.text((W//2, 260), price, font=_load_font(76), fill=(*ORANGE, 255), anchor='mm')
        stats = f"{beds} BD  ·  {baths} BA  ·  {sqft} SQFT"
        draw.text((W//2, 345), stats, font=_load_font(30), fill=(*CREAM, 200), anchor='mm')
        _orange_bar(draw, 375, 40)
        fh = _load_font(42)
        hlines = _wrap(draw, hl, fh, W - 80)
        for i, line in enumerate(hlines[:3]):
            draw.text((W//2, 430 + i*58), line, font=fh, fill=(*WHITE, 255), anchor='mm')
        if hl2:
            draw.text((W//2, 615), hl2, font=_load_font(32), fill=(*CREAM, 180), anchor='mm')
        draw.text((W//2, 690), '· DM US TO FIND YOURS ·', font=_load_font(26), fill=(*ORANGE, 220), anchor='mm')

    elif ct == 'market_stat':
        stat    = post_data.get('stat', '')
        context = post_data.get('context', '')
        draw.text((W//2, 85),  'SAN DIEGO MARKET', font=_load_font(28), fill=(*ORANGE, 230), anchor='mm')
        draw.text((W//2, 125), 'UPDATE', font=_load_font(28), fill=(*ORANGE, 230), anchor='mm')
        _orange_bar(draw, 155, 80)
        fs = _load_font(62)
        slines = _wrap(draw, stat, fs, W - 60)
        for i, line in enumerate(slines[:3]):
            draw.text((W//2, 230 + i*78), line, font=fs, fill=(*WHITE, 255), anchor='mm')
        _orange_bar(draw, 490, 40)
        fc = _load_font(34)
        clines = _wrap(draw, context, fc, W - 80)
        for i, line in enumerate(clines[:2]):
            draw.text((W//2, 540 + i*50), line, font=fc, fill=(*CREAM, 190), anchor='mm')
        draw.text((W//2, 680), '· QUESTIONS? DM US ·', font=_load_font(26), fill=(*ORANGE, 220), anchor='mm')

    elif ct == 'buyer_seller_tip':
        tip_type = post_data.get('tip_type', 'PRO TIP').upper()
        headline = post_data.get('headline', '')
        tip      = post_data.get('tip', '')
        draw.text((W//2, 80),  tip_type, font=_load_font(30), fill=(*ORANGE, 230), anchor='mm')
        _orange_bar(draw, 105, 60)
        fh = _load_font(54)
        hlines = _wrap(draw, headline, fh, W - 70)
        for i, line in enumerate(hlines[:2]):
            draw.text((W//2, 170 + i*68), line, font=fh, fill=(*WHITE, 255), anchor='mm')
        _orange_bar(draw, 320, 40)
        ft = _load_font(36)
        tlines = _wrap(draw, tip, ft, W - 90)
        for i, line in enumerate(tlines[:4]):
            draw.text((W//2, 375 + i*56), line, font=ft, fill=(*CREAM, 210), anchor='mm')
        draw.text((W//2, 680), '· READY? DM US ·', font=_load_font(26), fill=(*ORANGE, 220), anchor='mm')
        _add_headshot(img, size=150)

    elif ct == 'investor_quote':
        draw.text((W//2, 90), '"', font=_load_font(72), fill=(*ORANGE, 200), anchor='mm')
        quote  = post_data.get('quote', '')
        author = post_data.get('author', '')
        fq = _load_font(44)
        qlines = _wrap(draw, quote, fq, W - 80)
        for i, line in enumerate(qlines[:5]):
            draw.text((W//2, 180 + i*62), line, font=fq, fill=(*WHITE, 255), anchor='mm')
        _orange_bar(draw, 560, 60)
        draw.text((W//2, 600), f'— {author}', font=_load_font(30), fill=(*ORANGE, 220), anchor='mm')
        draw.text((W//2, 680), "· LET'S BUILD WEALTH ·", font=_load_font(26), fill=(*CREAM, 180), anchor='mm')
        _add_headshot(img, size=130)

    elif ct == 'san_diego_lifestyle':
        hood = post_data.get('neighborhood', 'San Diego')
        hl   = post_data.get('headline', '')
        ll   = post_data.get('lifestyle_line', '')
        rt   = post_data.get('real_estate_tie', '')
        draw.text((W//2, 85),  'LIFE IN', font=_load_font(30), fill=(*CREAM, 180), anchor='mm')
        draw.text((W//2, 155), hood.upper(), font=_load_font(66), fill=(*ORANGE, 255), anchor='mm')
        _orange_bar(draw, 192, 80)
        fh = _load_font(46)
        hlines = _wrap(draw, hl, fh, W - 70)
        for i, line in enumerate(hlines[:2]):
            draw.text((W//2, 255 + i*62), line, font=fh, fill=(*WHITE, 255), anchor='mm')
        fl = _load_font(34)
        llines = _wrap(draw, ll, fl, W - 90)
        for i, line in enumerate(llines[:2]):
            draw.text((W//2, 430 + i*52), line, font=fl, fill=(*CREAM, 200), anchor='mm')
        fr = _load_font(32)
        rlines = _wrap(draw, rt, fr, W - 90)
        for i, line in enumerate(rlines[:2]):
            draw.text((W//2, 560 + i*48), line, font=fr, fill=(*ORANGE, 210), anchor='mm')
        draw.text((W//2, 690), '· FIND YOUR SD HOME 🌊 ·', font=_load_font(26), fill=(*WHITE, 200), anchor='mm')

    # Also handle sd_hidden_gem content type
    elif ct == 'sd_hidden_gem':
        hood    = post_data.get('neighborhood', 'San Diego')
        hl      = post_data.get('headline', '')
        insight = post_data.get('insight', '')
        stat    = post_data.get('stat', '')
        context = post_data.get('context', '')
        draw.text((W//2, 75),  'SD HIDDEN GEM', font=_load_font(26), fill=(*ORANGE, 230), anchor='mm')
        draw.text((W//2, 135), hood.upper(), font=_load_font(58), fill=(*WHITE, 255), anchor='mm')
        _orange_bar(draw, 170, 80)
        fh = _load_font(40)
        hlines = _wrap(draw, hl, fh, W - 80)
        for i, line in enumerate(hlines[:2]):
            draw.text((W//2, 230 + i*56), line, font=fh, fill=(*ORANGE, 240), anchor='mm')
        fi = _load_font(30)
        ilines = _wrap(draw, insight, fi, W - 80)
        for i, line in enumerate(ilines[:4]):
            draw.text((W//2, 360 + i*46), line, font=fi, fill=(*CREAM, 200), anchor='mm')
        if stat:
            draw.text((W//2, 570), str(stat), font=_load_font(64), fill=(*ORANGE, 255), anchor='mm')
        if context:
            fc = _load_font(28)
            clines = _wrap(draw, context, fc, W - 80)
            for i, line in enumerate(clines[:2]):
                draw.text((W//2, 650 + i*40), line, font=fc, fill=(*CREAM, 180), anchor='mm')

    # Logo + headshot on every post
    _add_logo(img)
    if ct not in ('buyer_seller_tip', 'investor_quote'):
        _add_headshot(img, size=120)

    return img.convert('RGB')

def _gen_silence(path, duration=8, sample_rate=44100):
    samples = np.zeros(int(sample_rate * duration), dtype=np.int16)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples.tobytes())

def _build_animated_frames(post_data, bg_img, tmp_dir):
    """
    Build animated frames: background fades in, then text elements
    appear one by one with smooth fade-in animation.
    """
    total_frames = DURATION * FPS
    ct = post_data.get('content_type', 'market_stat')

    bg_phase = int(FPS * 0.5)
    bg_base  = _dark_overlay(bg_img)

    log.info(f'Rendering {total_frames} frames...')

    for f in range(total_frames):
        if f % 20 == 0:
            log.info(f'  Frame {f}/{total_frames}')

        if f < bg_phase:
            bg_alpha = int(255 * f / bg_phase)
        else:
            bg_alpha = 255

        frame = Image.new('RGBA', (W, H), (0, 0, 0, 255))
        faded_bg = bg_base.copy()
        if bg_alpha < 255:
            enhancer = ImageEnhance.Brightness(faded_bg)
            faded_bg = enhancer.enhance(bg_alpha / 255.0)
        frame = Image.alpha_composite(frame, faded_bg.convert('RGBA'))

        draw = ImageDraw.Draw(frame)
        draw.rectangle([(0, 0), (W, 6)], fill=(*ORANGE, 255))
        draw.rectangle([(0, H - 6), (W, H)], fill=(*ORANGE, 255))

        text_frame = max(0, f - bg_phase)
        element_count = 3

        for elem in range(element_count):
            elem_start = elem * FADE_FRAMES
            elem_alpha = min(255, max(0, int(255 * (text_frame - elem_start) / FADE_FRAMES)))
            if elem_alpha <= 0:
                continue

            if ct == 'market_stat':
                stat    = post_data.get('stat', '')
                context = post_data.get('context', '')
                if elem == 0:
                    for li, line in enumerate(['SAN DIEGO MARKET', 'UPDATE']):
                        draw.text((W//2, 85 + li*40), line, font=_load_font(28),
                                  fill=(*ORANGE, elem_alpha), anchor='mm')
                    x = (W - 80) // 2
                    draw.rectangle([(x, 155), (x+80, 159)], fill=(*ORANGE, elem_alpha))
                elif elem == 1:
                    fs = _load_font(62)
                    slines = _wrap(draw, stat, fs, W - 60)
                    for i, line in enumerate(slines[:3]):
                        draw.text((W//2, 230 + i*78), line, font=fs,
                                  fill=(*WHITE, elem_alpha), anchor='mm')
                elif elem == 2:
                    fc = _load_font(34)
                    clines = _wrap(draw, context, fc, W - 80)
                    for i, line in enumerate(clines[:2]):
                        draw.text((W//2, 540 + i*50), line, font=fc,
                                  fill=(*CREAM, elem_alpha), anchor='mm')
                    draw.text((W//2, 680), '· QUESTIONS? DM US ·',
                              font=_load_font(26), fill=(*ORANGE, elem_alpha), anchor='mm')
            else:
                if elem >= 1:
                    full = build_frame(post_data, bg_img)
                    frame = full.convert('RGBA')
                    draw = ImageDraw.Draw(frame)
                    break

        if f >= bg_phase:
            _add_logo(frame)
            _add_headshot(frame, size=120)

        frame_path = os.path.join(tmp_dir, f'f{f:05d}.jpg')
        frame.convert('RGB').save(frame_path, 'JPEG', quality=82)

    log.info('Frame rendering complete.')

def generate_reel(post_data: dict) -> str:
    cloudinary.config(
        cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key    = os.getenv('CLOUDINARY_API_KEY'),
        api_secret = os.getenv('CLOUDINARY_API_SECRET')
    )

    content_type = post_data.get('content_type', 'market_stat')
    tmp = tempfile.mkdtemp(prefix='wbg_')

    try:
        log.info('Fetching background...')
        bg_img = _get_background(content_type)
        log.info('Background ready. Building frames...')

        _build_animated_frames(post_data, bg_img, tmp)

        log.info('Generating silent audio...')
        audio_path = os.path.join(tmp, 'audio.wav')
        _gen_silence(audio_path, DURATION)

        log.info('Running ffmpeg...')
        out_path = os.path.join(tmp, 'reel.mp4')
        cmd = [
            imageio_ffmpeg.get_ffmpeg_exe(), '-y',
            '-framerate', str(FPS),
            '-i', os.path.join(tmp, 'f%05d.jpg'),
            '-i', audio_path,
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '26',
            '-pix_fmt', 'yuv420p', '-t', str(DURATION),
            '-c:a', 'aac', '-b:a', '64k', '-shortest',
            out_path
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        log.info('ffmpeg complete.')

        log.info('Uploading to Cloudinary...')
        upload_result = cloudinary.uploader.upload_large(
            out_path,
            resource_type='video',
            public_id='wbg_daily_reel',
            overwrite=True,
            timeout=120
        )
        url = upload_result['secure_url']
        log.info(f'Cloudinary upload complete: {url}')
        return url

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
