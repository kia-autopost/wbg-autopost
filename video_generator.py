"""
WBG Video Generator
Creates branded real estate Reels for Whissel Beer Group.
Uses 720p single-frame loop for memory efficiency on Railway.
"""
import os, tempfile, shutil, wave, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
import cloudinary
import cloudinary.uploader

ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
FONT_PATH  = os.path.join(ASSETS_DIR, 'Caladea-Regular.ttf')
LOGO_PATH  = os.path.join(ASSETS_DIR, 'logo.png')
HEADSHOT_PATH = os.path.join(ASSETS_DIR, 'headshot.png')

W, H     = 720, 1280
FPS      = 24
DURATION = 15

# WBG Brand colors
BG_COLOR     = (18, 18, 18)       # Near black
ORANGE       = (210, 90, 30)      # WBG orange
WHITE        = (255, 255, 255)
LIGHT_GRAY   = (200, 200, 200)
DARK_GRAY    = (60, 60, 60)

def _tw(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]

def _load_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except:
        return ImageFont.load_default()

def _wrap_text(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if draw.textbbox((0,0), t, font=font)[2] <= max_w:
            cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def _add_logo(img):
    try:
        logo = Image.open(LOGO_PATH).convert('RGBA')
        lw = 220
        lh = int(lw * logo.height / logo.width)
        logo = logo.resize((lw, lh), Image.LANCZOS)
        x = (W - lw) // 2
        y = H - lh - 50
        img.paste(logo, (x, y), logo)
    except Exception as e:
        pass

def _add_headshot(img):
    try:
        hs = Image.open(HEADSHOT_PATH).convert('RGBA')
        hw = 180
        hh = int(hw * hs.height / hs.width)
        hs = hs.resize((hw, hh), Image.LANCZOS)
        img.paste(hs, (W - hw - 30, H - hh - 160), hs)
    except:
        pass

def build_frame(post_data: dict) -> Image.Image:
    img = Image.new('RGBA', (W, H), (*BG_COLOR, 255))
    draw = ImageDraw.Draw(img)
    ct = post_data.get('content_type', 'market_stat')

    # Orange accent bar at top
    draw.rectangle([(0, 0), (W, 8)], fill=(*ORANGE, 255))

    if ct == 'property_spotlight':
        # Large price
        price = post_data.get('price_range', '')
        hood  = post_data.get('neighborhood', 'San Diego')
        hl    = post_data.get('headline', '')
        beds  = post_data.get('beds', '')
        baths = post_data.get('baths', '')
        sqft  = post_data.get('sqft', '')

        draw.text((W//2, 120), 'FOR SALE', font=_load_font(28), fill=(*ORANGE,255), anchor='mm')
        draw.text((W//2, 200), hood.upper(), font=_load_font(52), fill=(*WHITE,255), anchor='mm')
        draw.rectangle([(60, 240), (W-60, 243)], fill=(*ORANGE,255))

        draw.text((W//2, 310), price, font=_load_font(72), fill=(*ORANGE,255), anchor='mm')

        stats = f"{beds} BD  |  {baths} BA  |  {sqft} SQFT"
        draw.text((W//2, 400), stats, font=_load_font(32), fill=(*LIGHT_GRAY,255), anchor='mm')

        f = _load_font(38)
        lines = _wrap_text(draw, hl, f, W-80)
        for i, line in enumerate(lines[:3]):
            draw.text((W//2, 500 + i*55), line, font=f, fill=(*WHITE,255), anchor='mm')

        draw.text((W//2, 720), 'DM US TO FIND YOURS', font=_load_font(30), fill=(*ORANGE,255), anchor='mm')

    elif ct == 'market_stat':
        stat    = post_data.get('stat', '')
        context = post_data.get('context', '')
        draw.text((W//2, 140), 'SAN DIEGO', font=_load_font(32), fill=(*ORANGE,255), anchor='mm')
        draw.text((W//2, 185), 'MARKET UPDATE', font=_load_font(32), fill=(*ORANGE,255), anchor='mm')
        draw.rectangle([(60, 220), (W-60, 223)], fill=(*ORANGE,255))

        f = _load_font(58)
        lines = _wrap_text(draw, stat, f, W-80)
        for i, line in enumerate(lines[:3]):
            draw.text((W//2, 320 + i*75), line, font=f, fill=(*WHITE,255), anchor='mm')

        fc = _load_font(34)
        clines = _wrap_text(draw, context, fc, W-80)
        for i, line in enumerate(clines[:2]):
            draw.text((W//2, 580 + i*50), line, font=fc, fill=(*LIGHT_GRAY,255), anchor='mm')

        draw.text((W//2, 730), 'QUESTIONS? DM US 📊', font=_load_font(28), fill=(*ORANGE,255), anchor='mm')

    elif ct == 'buyer_seller_tip':
        tip_type = post_data.get('tip_type', 'Pro Tip').upper()
        headline = post_data.get('headline', '')
        tip      = post_data.get('tip', '')
        draw.text((W//2, 130), tip_type, font=_load_font(36), fill=(*ORANGE,255), anchor='mm')
        draw.rectangle([(60, 160), (W-60, 163)], fill=(*ORANGE,255))

        fh = _load_font(52)
        hlines = _wrap_text(draw, headline, fh, W-80)
        for i, line in enumerate(hlines[:2]):
            draw.text((W//2, 230 + i*65), line, font=fh, fill=(*WHITE,255), anchor='mm')

        ft = _load_font(36)
        tlines = _wrap_text(draw, tip, ft, W-100)
        for i, line in enumerate(tlines[:4]):
            draw.text((W//2, 430 + i*55), line, font=ft, fill=(*LIGHT_GRAY,255), anchor='mm')

        draw.text((W//2, 730), 'READY? DM US 💡', font=_load_font(28), fill=(*ORANGE,255), anchor='mm')
        _add_headshot(img)

    elif ct == 'investor_quote':
        draw.text((W//2, 120), '💼', font=_load_font(60), fill=(*WHITE,255), anchor='mm')
        quote  = post_data.get('quote', '')
        author = post_data.get('author', '')
        draw.text((W//2, 210), '"', font=_load_font(80), fill=(*ORANGE,255), anchor='mm')
        fq = _load_font(44)
        qlines = _wrap_text(draw, quote, fq, W-100)
        for i, line in enumerate(qlines[:5]):
            draw.text((W//2, 290 + i*60), line, font=fq, fill=(*WHITE,255), anchor='mm')
        draw.text((W//2, 630), f'— {author}', font=_load_font(32), fill=(*ORANGE,255), anchor='mm')
        draw.text((W//2, 730), "LET'S BUILD WEALTH 💼", font=_load_font(28), fill=(*LIGHT_GRAY,255), anchor='mm')

    elif ct == 'san_diego_lifestyle':
        hood = post_data.get('neighborhood', 'San Diego')
        hl   = post_data.get('headline', '')
        ll   = post_data.get('lifestyle_line', '')
        rt   = post_data.get('real_estate_tie', '')
        draw.text((W//2, 110), 'LIFE IN', font=_load_font(32), fill=(*LIGHT_GRAY,255), anchor='mm')
        draw.text((W//2, 175), hood.upper(), font=_load_font(62), fill=(*ORANGE,255), anchor='mm')
        draw.rectangle([(60, 215), (W-60, 218)], fill=(*ORANGE,255))

        fh = _load_font(44)
        hlines = _wrap_text(draw, hl, fh, W-80)
        for i, line in enumerate(hlines[:2]):
            draw.text((W//2, 280 + i*60), line, font=fh, fill=(*WHITE,255), anchor='mm')

        fl = _load_font(34)
        llines = _wrap_text(draw, ll, fl, W-100)
        for i, line in enumerate(llines[:2]):
            draw.text((W//2, 460 + i*50), line, font=fl, fill=(*LIGHT_GRAY,255), anchor='mm')

        fr = _load_font(32)
        rlines = _wrap_text(draw, rt, fr, W-100)
        for i, line in enumerate(rlines[:2]):
            draw.text((W//2, 580 + i*48), line, font=fr, fill=(*ORANGE,255), anchor='mm')

        draw.text((W//2, 730), 'FIND YOUR SD HOME 🌊', font=_load_font(28), fill=(*WHITE,255), anchor='mm')

    # Orange accent bar at bottom
    draw.rectangle([(0, H-8), (W, H)], fill=(*ORANGE, 255))
    # Logo
    _add_logo(img)
    return img.convert('RGB')

def _gen_silence(path, duration=15, sample_rate=44100):
    samples = np.zeros(int(sample_rate * duration), dtype=np.int16)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2)
        wf.setframerate(sample_rate); wf.writeframes(samples.tobytes())

def generate_reel(post_data: dict) -> str:
    cloudinary.config(
        cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key    = os.getenv('CLOUDINARY_API_KEY'),
        api_secret = os.getenv('CLOUDINARY_API_SECRET')
    )
    tmp = tempfile.mkdtemp(prefix='wbg_')
    try:
        frame = build_frame(post_data)
        frame_path = os.path.join(tmp, 'frame.jpg')
        frame.save(frame_path, 'JPEG', quality=90)

        audio_path = os.path.join(tmp, 'audio.wav')
        _gen_silence(audio_path, DURATION)

        out_path = os.path.join(tmp, 'reel.mp4')
        cmd = [
            imageio_ffmpeg.get_ffmpeg_exe(), '-y',
            '-loop', '1', '-i', frame_path,
            '-i', audio_path,
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
            '-pix_fmt', 'yuv420p', '-t', str(DURATION),
            '-c:a', 'aac', '-b:a', '64k', '-shortest', out_path
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)

        result = cloudinary.uploader.upload_large(
            out_path, resource_type='video',
            public_id='wbg_daily_reel', overwrite=True
        )
        return result['secure_url']
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
