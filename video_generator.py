"""
WBG Video Generator - V7 Dynamic Edition
- DARK CINEMATIC: sd_hidden_gem, market_stat, current_event_tie, investor_quote, market_data
- LIGHT EDITORIAL: buyer_seller_tip, hot_take, hyper_local_intel, sd_lifestyle_hook,
                   san_diego_lifestyle, property_spotlight, home_tour
"""
import os, tempfile, shutil, wave, subprocess, random, urllib.request, json, logging, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
import cloudinary, cloudinary.uploader

log = logging.getLogger('WBG')

ASSETS_DIR     = os.path.join(os.path.dirname(__file__), 'assets')
HEADSHOT_PATH  = os.path.join(ASSETS_DIR, 'headshot.png')
PREFERRED_LOGO = 'Logo_Primary_White_01.png'
FALLBACK_LOGOS = ['exp_Logo_Secondary_White_01.png', 'WBG LOGO - ExpLogoLogoPrimaryWhite01.png']

W, H         = 720, 1280
FPS          = 24
DURATION     = 10
TOTAL_FRAMES = DURATION * FPS

WHITE  = (255, 255, 255)
CREAM  = (245, 240, 230)
CREAM2 = (250, 247, 242)
BLACK  = (12, 12, 12)
DKGRAY = (30, 30, 30)
ORANGE = (210, 85, 25)
LTGRAY = (180, 175, 168)
GOLD   = (195, 155, 60)

DARK_TYPES     = {'sd_hidden_gem', 'market_stat', 'current_event_tie', 'investor_quote', 'market_data'}
LIGHT_TYPES    = {'buyer_seller_tip', 'hot_take', 'hyper_local_intel', 'sd_lifestyle_hook',
                  'san_diego_lifestyle', 'property_spotlight', 'home_tour'}
HEADSHOT_TYPES = {'buyer_seller_tip', 'hot_take', 'sd_hidden_gem', 'hyper_local_intel',
                  'sd_lifestyle_hook', 'current_event_tie'}

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

# ─── PHOTO POOL ──────────────────────────────────────────────────────────────

PHOTO_STATE_FILE = os.path.join(ASSETS_DIR, '.photo_state.json')

def _get_photo_pool(is_dark):
    all_jpgs = sorted([f for f in os.listdir(ASSETS_DIR)
                       if f.endswith('.jpg') and os.path.exists(os.path.join(ASSETS_DIR, f))])
    dark_kw  = ['sunset','aerial','neighborhood','palm','craftsman','coast','beach','street','city','urban']
    light_kw = ['luxury','modern','house','home','interior','pool','kitchen','living','bedroom','backyard']
    dark_pool  = [f for f in all_jpgs if any(k in f.lower() for k in dark_kw)]
    light_pool = [f for f in all_jpgs if any(k in f.lower() for k in light_kw)]
    if len(dark_pool)  < 10: dark_pool  = all_jpgs
    if len(light_pool) < 10: light_pool = all_jpgs
    return dark_pool if is_dark else light_pool

def _pick_photo(is_dark):
    pool = _get_photo_pool(is_dark)
    if not pool:
        all_jpgs = [f for f in os.listdir(ASSETS_DIR) if f.endswith('.jpg')]
        pool = all_jpgs if all_jpgs else []
    if not pool: return None

    state = {}
    try:
        if os.path.exists(PHOTO_STATE_FILE):
            with open(PHOTO_STATE_FILE,'r') as f: state = json.load(f)
    except: state = {}

    key        = 'used_dark' if is_dark else 'used_light'
    used       = set(state.get(key,[]))
    last_photo = state.get('last_photo','')
    unused     = [p for p in pool if p not in used and p != last_photo]
    if not unused:
        unused = [p for p in pool if p != last_photo]
        if not unused: unused = pool
        used = set()

    chosen = random.choice(unused)
    used.add(chosen)
    state[key] = list(used)
    state['last_photo'] = chosen
    try:
        with open(PHOTO_STATE_FILE,'w') as f: json.dump(state, f)
    except: pass
    log.info(f'Photo: {chosen} ({len(unused)-1} unused left of {len(pool)})')
    return chosen

def _fetch_bg(content_type, neighborhood='', size_w=None, size_h=None):
    bw = size_w or int(W * 1.12)
    bh = size_h or int(H * 1.12)
    is_dark = content_type in DARK_TYPES

    chosen = None
    if neighborhood and neighborhood.lower() not in ('san diego',''):
        hood_key = neighborhood.lower().replace(' ','_').replace("'",'')
        all_jpgs = [f for f in os.listdir(ASSETS_DIR) if f.endswith('.jpg')]
        hood_matches = [f for f in all_jpgs if hood_key in f.lower()]
        if hood_matches:
            chosen = random.choice(hood_matches)
            log.info(f'Neighborhood photo: {chosen}')

    if not chosen: chosen = _pick_photo(is_dark)

    path = os.path.join(ASSETS_DIR, chosen) if chosen else None
    if path and os.path.exists(path):
        try:
            bg = Image.open(path).convert('RGB')
            if bg.height > 200: bg = bg.crop((0,0,bg.width,bg.height-60))
            ratio = max(bw/bg.width, bh/bg.height)
            bg = bg.resize((int(bg.width*ratio),int(bg.height*ratio)), Image.LANCZOS)
            return bg
        except Exception as e:
            log.warning(f'Photo load failed: {e}')
    return _gradient(bw, bh)

def _gradient(w, h):
    bg = Image.new('RGBA',(w,h),(0,0,0,255))
    d  = ImageDraw.Draw(bg)
    for y in range(h):
        t = y/h
        d.line([(0,y),(w,y)], fill=(int(20+t*12),int(16+t*8),int(25+t*10),255))
    glow = Image.new('RGBA',(w,h),(0,0,0,0))
    gd   = ImageDraw.Draw(glow)
    for i in range(180,0,-1):
        gd.ellipse([(-i,h-i*2),(i*3,h+i)], fill=(180,60,10,min(int((180-i)*0.7),120)))
    return Image.alpha_composite(bg,glow).convert('RGB')

# ─── KEN BURNS ───────────────────────────────────────────────────────────────

def _ken_burns(bg, f, total):
    t   = f/max(total-1,1)
    t_e = t*t*(3-2*t)
    bw,bh = bg.size
    scale = 1.08+(1.0-1.08)*t_e
    cw = max(W,min(int(W*scale),bw))
    ch = max(H,min(int(H*scale),bh))
    cx=bw//2; cy=bh//2
    l  = max(0,min(cx-cw//2,bw-cw))
    tp = max(0,min(cy-ch//2,bh-ch))
    cropped = bg.crop((l,tp,l+cw,tp+ch))
    if cropped.size!=(W,H): cropped=cropped.resize((W,H),Image.LANCZOS)
    return cropped

# ─── OVERLAYS ────────────────────────────────────────────────────────────────

def _dark_overlay(bg_frame):
    ov = Image.new('RGBA',(W,H),(0,0,0,0))
    d  = ImageDraw.Draw(ov)
    for y in range(H):
        t = y/H
        top_a = int(210*(math.cos(t/0.55*math.pi/2))**1.4) if t<0.55 else 0
        bot_a = int(220*(math.sin((t-0.55)/0.45*math.pi/2))**1.2) if t>0.55 else 0
        a = min(255, top_a+bot_a+60)
        d.line([(0,y),(W,y)], fill=(0,0,0,a))
    return Image.alpha_composite(bg_frame.convert('RGBA'),ov).convert('RGB')

def _light_overlay(bg_frame):
    ov = Image.new('RGBA',(W,H),(0,0,0,0))
    d  = ImageDraw.Draw(ov)
    for y in range(H):
        t = y/H
        top_a = int(160*(math.cos(t/0.5*math.pi/2))**1.6) if t<0.5 else 0
        bot_a = int(180*(math.sin((t-0.6)/0.4*math.pi/2))**1.4) if t>0.6 else 0
        a = min(230, top_a+bot_a+35)
        d.line([(0,y),(W,y)], fill=(0,0,0,a))
    return Image.alpha_composite(bg_frame.convert('RGBA'),ov).convert('RGB')

# ─── TEXT HELPERS ────────────────────────────────────────────────────────────

def _wrap(draw, text, font, max_w):
    words = text.split()
    lines,cur = [],''
    for w in words:
        test = (cur+' '+w).strip()
        if draw.textbbox((0,0),test,font=font)[2] <= max_w: cur=test
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return lines

def _a(f,start,fade=18):
    if f<start: return 0
    e=f-start
    return 255 if e>=fade else int(255*e/fade)

def _y(f,start,slide=20):
    if f<start: return 45
    e=f-start
    if e>=slide: return 0
    t=e/slide
    return int(45*(1-t*t*(3-2*t)))

def _paste(img,text,font,x,y,color,alpha,anchor='mm'):
    if alpha<=0 or not text: return
    layer=Image.new('RGBA',(W,H),(0,0,0,0))
    d=ImageDraw.Draw(layer)
    r,g,b=color
    d.text((x,y),text,font=font,fill=(r,g,b,alpha),anchor=anchor)
    img.paste(layer,mask=layer)

def _paste_pill(img, draw, text, font, x, y, fg, alpha, bg_color=(0,0,0), bg_alpha=130, pad_x=24, pad_y=10):
    """Text with fitted rounded pill backing."""
    if alpha<=0 or not text: return
    tw = draw.textbbox((0,0),text,font=font)[2]
    th = draw.textbbox((0,0),text,font=font)[3]
    bx1 = x - tw//2 - pad_x
    bx2 = x + tw//2 + pad_x
    by1 = y - th//2 - pad_y + 4
    by2 = y + th//2 + pad_y + 4
    pill = Image.new('RGBA',(W,H),(0,0,0,0))
    pd   = ImageDraw.Draw(pill)
    r,g,b = bg_color
    pd.rounded_rectangle([(bx1,by1),(bx2,by2)], radius=20, fill=(r,g,b,int(bg_alpha*alpha/255)))
    img.alpha_composite(pill)
    _paste(img,text,font,x,y,fg,alpha)

def _paste_line(img,x1,y1,x2,y2,color,alpha,w=4):
    if alpha<=0: return
    layer=Image.new('RGBA',(W,H),(0,0,0,0))
    d=ImageDraw.Draw(layer)
    r,g,b=color
    d.line([(x1,y1),(x2,y2)],fill=(r,g,b,alpha),width=w)
    img.paste(layer,mask=layer)

def _orange_accent_bar(img, y, al, width=80):
    """Thin orange horizontal accent line."""
    CX = W//2
    _paste_line(img, CX-width//2, y, CX+width//2, y, ORANGE, al, w=3)

# ─── HEADSHOT ────────────────────────────────────────────────────────────────

def _render_headshot(img, f):
    al = _a(f, int(FPS*1.5), 30)
    if al<=0: return
    try:
        hs = Image.open(HEADSHOT_PATH).convert('RGBA')
        hw = 260; hh = int(hw*hs.height/hs.width)
        hs = hs.resize((hw,hh), Image.LANCZOS)
        if al<255:
            r,g,b,a2 = hs.split()
            a2 = a2.point(lambda x: int(x*al/255))
            hs = Image.merge('RGBA',(r,g,b,a2))
        # Bottom LEFT corner — never overlaps center text
        x_pos = 20
        y_pos = H - hh - 160
        img.paste(hs, (x_pos, y_pos), hs)
    except: pass

# ─── LOGO ────────────────────────────────────────────────────────────────────

def _render_logo(img, f):
    al = _a(f, int(FPS*0.8), 24)
    if al<=0: return
    logo = None
    for name in [PREFERRED_LOGO]+FALLBACK_LOGOS:
        p = os.path.join(ASSETS_DIR,name)
        if os.path.exists(p):
            try: logo=Image.open(p).convert('RGBA'); break
            except: continue
    if not logo: return
    lw=200; lh=int(lw*logo.height/logo.width)
    lr=logo.resize((lw,lh),Image.LANCZOS)
    if al<255:
        r,g,b,a2=lr.split()
        a2=a2.point(lambda x: int(x*al/255))
        lr=Image.merge('RGBA',(r,g,b,a2))
    img.paste(lr,((W-lw)//2,H-lh-40),lr)

# ─── DARK CINEMATIC RENDERER ─────────────────────────────────────────────────

def _render_dark(img, draw, post_data, f):
    ct   = post_data.get('content_type','market_stat')
    hood = post_data.get('neighborhood','San Diego').upper()
    hl   = post_data.get('headline', post_data.get('insight',''))
    body = (post_data.get('real_estate_tie') or post_data.get('context') or '')
    stat = str(post_data.get('stat',''))

    labels = {'sd_hidden_gem':'LIFE IN','market_stat':'SAN DIEGO',
              'current_event_tie':'RIGHT NOW IN SD','investor_quote':'INVEST IN SD',
              'market_data':'MARKET UPDATE'}
    label = labels.get(ct,'SAN DIEGO')

    PAD=50; CX=W//2
    T = {'label':int(FPS*0.5),'hood':int(FPS*0.9),'rule':int(FPS*1.5),
         'hl':int(FPS*1.9),'body':int(FPS*2.6),'stat':int(FPS*3.2)}

    # Label - small spaced caps
    al=_a(f,T['label'],20); yo=_y(f,T['label'],20)
    _paste(img, label, _font('oswald_regular',22), CX, 105+yo, ORANGE, int(al*0.85))

    # Neighborhood - massive white
    al=_a(f,T['hood'],22); yo=_y(f,T['hood'],24)
    hood_bottom=200
    if al:
        for sz in [120,100,84,70,58]:
            fn=_font('oswald_bold',sz)
            all_lines=_wrap(draw,hood,fn,W-PAD*2)
            if len(all_lines)<=3: break
        y_cur=155
        for line in all_lines[:3]:
            _paste(img,line,fn,CX,y_cur+yo,WHITE,al)
            y_cur+=sz+8
        hood_bottom=y_cur+yo

    # Orange accent bar
    al=_a(f,T['rule'],12); rule_y=hood_bottom+22
    _orange_accent_bar(img, rule_y, al, width=100)

    # Headline - white with subtle shadow
    al=_a(f,T['hl'],20); yo=_y(f,T['hl'],22); hl_bottom=rule_y+50
    if al and hl:
        fh=_font('oswald_regular',40)
        hlines=_wrap(draw,hl,fh,W-PAD*2)
        y_cur=rule_y+50
        for line in hlines[:3]:
            _paste(img,line,fh,CX+2,y_cur+yo+2,BLACK,int(al*0.5))
            _paste(img,line,fh,CX,y_cur+yo,WHITE,int(al*0.97))
            y_cur+=50
        hl_bottom=y_cur+yo

    # Body - pill backing, large readable font
    al=_a(f,T['body'],22); yo=_y(f,T['body'],22)
    body_bottom=hl_bottom+30
    if al and body:
        fb=_font('oswald_bold',32)
        # Truncate at natural break — period, dash, or word boundary
        b = body[:90]
        for sep in ['. ', ' — ', ', ']:
            idx = b.rfind(sep)
            if idx > 35:
                b = b[:idx+1].strip(); break
        else:
            b = b.rsplit(' ',1)[0] if len(body)>90 else body
        # Render as single multi-line pill backing
        blines=_wrap(draw,b,fb,W-PAD*2-40)[:2]
        if blines:
            # Measure full pill height
            line_h = 38
            total_h = len(blines)*line_h + 28
            # Find widest line
            max_tw = max(draw.textbbox((0,0),l,font=fb)[2] for l in blines)
            bx1 = CX - max_tw//2 - 32
            bx2 = CX + max_tw//2 + 32
            by1 = hl_bottom + 42 + yo - 14
            by2 = by1 + total_h
            pill = Image.new("RGBA",(W,H),(0,0,0,0))
            pd   = ImageDraw.Draw(pill)
            pd.rounded_rectangle([(bx1,by1),(bx2,by2)],radius=22,fill=(0,0,0,int(al*0.82)))
            img.alpha_composite(pill)
            y_cur = hl_bottom + 52 + yo
            for line in blines:
                _paste(img,line,fb,CX,y_cur,WHITE,al)
                y_cur += line_h
            body_bottom = y_cur + yo

    # Stat - large orange
    al=_a(f,T['stat'],20); yo=_y(f,T['stat'],20)
    if al and stat:
        stat_short=stat[:25].rsplit(' ',1)[0] if len(stat)>25 else stat
        for sz in [80,64,52,42,34]:
            fs=_font('oswald_bold',sz)
            if draw.textbbox((0,0),stat_short,font=fs)[2]<=W-PAD*2: break
        stat_y=min(body_bottom+40,H-290)
        _paste(img,stat_short,fs,CX,stat_y+yo,ORANGE,al)

# ─── LIGHT EDITORIAL RENDERER ────────────────────────────────────────────────

def _render_light(img, draw, post_data, f):
    ct   = post_data.get('content_type','buyer_seller_tip')
    hood = post_data.get('neighborhood','San Diego').upper()
    hl   = post_data.get('headline',post_data.get('insight',''))
    body = (post_data.get('real_estate_tie') or post_data.get('context') or
            post_data.get('tip') or '')
    stat = str(post_data.get('stat',''))

    labels = {'buyer_seller_tip':'PRO TIP','hot_take':'HOT TAKE',
              'hyper_local_intel':'MARKET INTEL','sd_lifestyle_hook':'SD LIVING',
              'san_diego_lifestyle':'LIFE IN SD','property_spotlight':'JUST LISTED','home_tour':'JUST LISTED'}
    label=labels.get(ct,'SAN DIEGO')

    PAD=50; CX=W//2
    T={'label':int(FPS*0.4),'hood':int(FPS*0.8),'rule':int(FPS*1.3),
       'hl':int(FPS*1.7),'stat':int(FPS*2.3),'body':int(FPS*2.9)}

    # Label - orange accent
    al=_a(f,T['label'],18); yo=_y(f,T['label'],18)
    _paste(img,label,_font('oswald_regular',22),CX,100+yo,ORANGE,int(al*0.90))

    # Neighborhood - massive
    al=_a(f,T['hood'],22); yo=_y(f,T['hood'],22)
    hood_bottom=260
    if al:
        for sz in [120,100,84,70,58]:
            fn=_font('oswald_bold',sz)
            nlines=_wrap(draw,hood,fn,W-PAD*2)
            if len(nlines)<=2: break
        y_cur=155
        for line in nlines[:2]:
            _paste(img,line,fn,CX,y_cur+yo,WHITE,al)
            y_cur+=sz+8
        hood_bottom=y_cur+yo+5

    # Orange accent bar
    al=_a(f,T['rule'],10); rule_y=hood_bottom+20
    _orange_accent_bar(img,rule_y,al,width=100)

    # Headline
    al=_a(f,T['hl'],18); yo=_y(f,T['hl'],20); hl_bottom=rule_y+50
    if al and hl:
        for fsz in [38,32,28,24]:
            fh=_font('oswald_regular',fsz)
            hlines=_wrap(draw,hl,fh,W-PAD*2)
            if len(hlines)<=2: break
        y_cur=rule_y+50
        for line in hlines[:2]:
            _paste(img,line,fh,CX+1,y_cur+yo+1,BLACK,int(al*0.4))
            _paste(img,line,fh,CX,y_cur+yo,WHITE,int(al*0.97))
            y_cur+=fsz+12
        hl_bottom=y_cur+yo

    # Stat - orange bold
    al=_a(f,T['stat'],18); yo=_y(f,T['stat'],18); stat_bottom=hl_bottom+50
    if al and stat:
        stat_short=stat[:20].rsplit(' ',1)[0] if len(stat)>20 else stat
        for ssz in [62,50,42,34]:
            fs=_font('oswald_bold',ssz)
            if draw.textbbox((0,0),stat_short,font=fs)[2]<=W-PAD*2: break
        stat_y=max(hl_bottom+45,620); stat_y=min(stat_y,H-310)
        _paste(img,stat_short,fs,CX,stat_y+yo,ORANGE,al)
        stat_bottom=stat_y+ssz+15

    # Body - pill backing
    al=_a(f,T['body'],20); yo=_y(f,T['body'],20)
    if al and body:
        fb=_font('raleway',30)
        body_short=body[:75].rsplit(' ',1)[0] if len(body)>75 else body
        blines=_wrap(draw,body_short,fb,W-PAD*2-40)
        y_cur=stat_bottom+22
        for line in blines[:2]:
            _paste_pill(img,draw,line,fb,CX,y_cur+yo,WHITE,al,bg_color=(0,0,0),bg_alpha=200,pad_x=32,pad_y=14)
            y_cur+=52

# ─── MARKET DATA RENDERER ────────────────────────────────────────────────────

def _render_market_data(img, draw, post_data, f):
    hood    = post_data.get('neighborhood','San Diego').upper()
    median  = post_data.get('median_price','')
    dom     = post_data.get('days_on_market','')
    yoy     = post_data.get('price_change_yoy','')
    temp    = post_data.get('market_temp','active').upper()
    insight = post_data.get('insight','')

    PAD=50; CX=W//2
    T={'label':int(FPS*0.4),'hood':int(FPS*0.8),'rule':int(FPS*1.3),
       'stats':int(FPS*1.7),'insight':int(FPS*2.8)}

    al=_a(f,T['label'],18); yo=_y(f,T['label'],18)
    _paste(img,'MARKET UPDATE',_font('oswald_regular',22),CX,100+yo,ORANGE,int(al*0.85))

    al=_a(f,T['hood'],22); yo=_y(f,T['hood'],22)
    hood_bottom=260
    if al:
        for sz in [110,92,76,62,50]:
            fn=_font('oswald_bold',sz)
            nlines=_wrap(draw,hood,fn,W-PAD*2)
            if len(nlines)<=2: break
        y_cur=148
        for line in nlines[:2]:
            _paste(img,line,fn,CX,y_cur+yo,WHITE,al)
            y_cur+=sz+8
        hood_bottom=y_cur+yo
    
    al=_a(f,T['rule'],10); rule_y=hood_bottom+18
    _orange_accent_bar(img,rule_y,al,width=100)

    temp_colors={'HOT':(220,60,30),'WARM':(210,130,30),'COOL':(60,130,200),'COLD':(80,120,220),'ACTIVE':(210,85,25)}
    al=_a(f,T['rule'],10)
    if al and temp:
        tc=temp_colors.get(temp,ORANGE)
        _paste(img,f'{temp} MARKET',_font('oswald_bold',28),CX,rule_y+38+yo,tc,int(al*0.9))

    al=_a(f,T['stats'],20); yo=_y(f,T['stats'],22)
    if al:
        stat_y=rule_y+85
        if median:
            _paste(img,'MEDIAN PRICE',_font('oswald_regular',20),CX,stat_y+yo,CREAM,int(al*0.6))
            _paste(img,median,_font('oswald_bold',72),CX,stat_y+55+yo,WHITE,al)
        if dom or yoy:
            sub_y=stat_y+135
            if dom:
                _paste(img,'AVG DOM',_font('oswald_regular',20),W//4,sub_y+yo,CREAM,int(al*0.6))
                _paste(img,dom.replace(' days','d').replace(' ',''),_font('oswald_bold',46),W//4,sub_y+42+yo,ORANGE,al)
            if yoy:
                color=(80,200,100) if '+' in yoy else (200,80,80)
                _paste(img,'YoY CHANGE',_font('oswald_regular',20),3*W//4,sub_y+yo,CREAM,int(al*0.6))
                _paste(img,yoy,_font('oswald_bold',46),3*W//4,sub_y+42+yo,color,al)

    al=_a(f,T['insight'],22); yo=_y(f,T['insight'],22)
    if al and insight:
        fi=_font('raleway',28)
        insight_short=insight[:90].rsplit(' ',1)[0] if len(insight)>90 else insight
        ilines=_wrap(draw,insight_short,fi,W-PAD*2-40)
        y_cur=max(rule_y+325,630); y_cur=min(y_cur,H-280)
        for line in ilines[:2]:
            if y_cur+yo < H-250:
                _paste_pill(img,draw,line,fi,CX,y_cur+yo,WHITE,al,bg_color=(0,0,0),bg_alpha=150,pad_x=28,pad_y=12)
                y_cur+=44

# ─── HOME TOUR RENDERER ──────────────────────────────────────────────────────

def _render_home_tour(img, draw, post_data, f):
    hood  = post_data.get('neighborhood','San Diego').upper()
    price = post_data.get('price','')
    beds  = post_data.get('beds','')
    baths = post_data.get('baths','')
    sqft  = post_data.get('sqft','')
    feat1 = post_data.get('feature_1','')
    feat2 = post_data.get('feature_2','')
    feat3 = post_data.get('feature_3','')
    stat  = post_data.get('stat','')

    PAD=50; CX=W//2
    T={'label':int(FPS*0.3),'price':int(FPS*0.7),'hood':int(FPS*1.1),
       'rule':int(FPS*1.5),'details':int(FPS*1.9),'features':int(FPS*2.6)}

    al=_a(f,T['label'],16); yo=_y(f,T['label'],16)
    _paste(img,'JUST LISTED',_font('oswald_regular',22),CX,100+yo,ORANGE,int(al*0.85))

    al=_a(f,T['price'],20); yo=_y(f,T['price'],20)
    if al and price:
        _paste(img,price,_font('oswald_bold',72),CX,185+yo,WHITE,al)

    al=_a(f,T['hood'],22); yo=_y(f,T['hood'],22); hood_bottom=320
    if al:
        for sz in [92,76,62,50,42]:
            fn=_font('oswald_bold',sz)
            nlines=_wrap(draw,hood,fn,W-PAD*2)
            if len(nlines)<=2: break
        y_cur=300
        for line in nlines[:2]:
            _paste(img,line,fn,CX,y_cur+yo,WHITE,al)
            y_cur+=sz+6
        hood_bottom=y_cur+yo+5

    al=_a(f,T['rule'],10); rule_y=hood_bottom+16
    _orange_accent_bar(img,rule_y,al,width=100)

    al=_a(f,T['details'],18); yo=_y(f,T['details'],18)
    if al and (beds or baths or sqft):
        fd=_font('oswald_regular',34)
        details=[]
        if beds:  details.append(f'{beds} BD')
        if baths: details.append(f'{baths} BA')
        if sqft:  details.append(f'{sqft} SQFT')
        _paste(img,'  ·  '.join(details),fd,CX,rule_y+42+yo,CREAM,int(al*0.90))

    al=_a(f,T['features'],20); yo=_y(f,T['features'],20)
    feat_y=rule_y+90
    if al:
        ff=_font('oswald_regular',28)
        for feat in [feat1,feat2,feat3]:
            if feat and feat_y+yo<H-260:
                feat_short=feat[:38].rsplit(' ',1)[0] if len(feat)>38 else feat
                bar=Image.new('RGBA',(W,46),(0,0,0,0))
                bd=ImageDraw.Draw(bar)
                bd.rectangle([(0,0),(W,46)],fill=(0,0,0,int(al*0.60)))
                img.paste(bar,(0,feat_y+yo-18),bar)
                _paste(img,'▶',_font('oswald_regular',18),PAD+8,feat_y+yo,ORANGE,int(al*0.9))
                _paste(img,feat_short,ff,PAD+32,feat_y+yo,WHITE,int(al*0.95),anchor='lm')
                feat_y+=50

    al=_a(f,T['features'],18); yo=_y(f,T['features'],18)
    if al and stat:
        stat_short=stat[:20].rsplit(' ',1)[0] if len(stat)>20 else stat
        _paste(img,stat_short,_font('oswald_bold',36),CX,min(feat_y+30+yo,H-260),ORANGE,al)

# ─── FRAME BUILDER ───────────────────────────────────────────────────────────

def _build_frames(post_data, bg, tmp_dir):
    ct      = post_data.get('content_type','market_stat')
    is_light= ct in LIGHT_TYPES
    show_hs = ct in HEADSHOT_TYPES

    log.info(f'Style: {"LIGHT" if is_light else "DARK"} | {TOTAL_FRAMES} frames')

    for f in range(TOTAL_FRAMES):
        if f%24==0: log.info(f'  Frame {f}/{TOTAL_FRAMES}')
        bg_f  = _ken_burns(bg,f,TOTAL_FRAMES)
        frame = (_light_overlay if is_light else _dark_overlay)(bg_f).convert('RGBA')
        draw  = ImageDraw.Draw(frame)

        if   ct=='market_data': _render_market_data(frame,draw,post_data,f)
        elif ct=='home_tour':   _render_home_tour(frame,draw,post_data,f)
        elif is_light:          _render_light(frame,draw,post_data,f)
        else:                   _render_dark(frame,draw,post_data,f)

        _render_logo(frame,f)
        if show_hs: _render_headshot(frame,f)

        frame.convert('RGB').save(os.path.join(tmp_dir,f'f{f:05d}.jpg'),'JPEG',quality=85)

    log.info('Rendering complete.')

# ─── AUDIO ───────────────────────────────────────────────────────────────────

def _silence(path):
    s=np.zeros(int(44100*DURATION),dtype=np.int16)
    with wave.open(path,'w') as w:
        w.setnchannels(1); w.setsampwidth(2)
        w.setframerate(44100); w.writeframes(s.tobytes())

AUDIO_STATE_FILE = os.path.join(ASSETS_DIR,'.audio_state.json')

def _get_audio_track():
    all_tracks=sorted([f for f in os.listdir(ASSETS_DIR)
                       if f.endswith('.mp3') and f.startswith('fixed_')
                       and os.path.exists(os.path.join(ASSETS_DIR,f))])
    if not all_tracks:
        all_tracks=sorted([f for f in os.listdir(ASSETS_DIR) if f.endswith('.mp3')
                          and os.path.exists(os.path.join(ASSETS_DIR,f))])
    if not all_tracks: return None

    state={}
    try:
        if os.path.exists(AUDIO_STATE_FILE):
            with open(AUDIO_STATE_FILE,'r') as f: state=json.load(f)
    except: state={}

    used  =set(state.get('used_tracks',[]))
    unused=[t for t in all_tracks if t not in used]
    if not unused:
        unused=all_tracks; used=set()

    chosen=random.choice(unused)
    used.add(chosen)
    state['used_tracks']=list(used)
    try:
        with open(AUDIO_STATE_FILE,'w') as f: json.dump(state,f)
    except: pass
    log.info(f'Audio: {chosen} ({len(unused)-1} unused of {len(all_tracks)})')
    return os.path.join(ASSETS_DIR,chosen)

def _prepare_audio(tmp_dir, post_data=None):
    audio_path=os.path.join(tmp_dir,'audio.wav')
    track=_get_audio_track()
    if track and os.path.exists(track):
        try:
            converted=os.path.join(tmp_dir,'music.wav')
            subprocess.run([
                imageio_ffmpeg.get_ffmpeg_exe(),'-y',
                '-i',track,'-t',str(DURATION),
                '-af',f'afade=t=in:st=0:d=1,afade=t=out:st={DURATION-2}:d=2,volume=0.8',
                '-ar','44100','-ac','1',converted
            ],check=True,capture_output=True,timeout=30)
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
    tmp=tempfile.mkdtemp(prefix='wbg_')
    try:
        ct  =post_data.get('content_type','market_stat')
        hood=post_data.get('neighborhood','')
        log.info(f'Generating reel: {ct} | {hood}')
        bg=_fetch_bg(ct,hood)
        log.info('Building frames...')
        _build_frames(post_data,bg,tmp)
        audio=_prepare_audio(tmp,post_data)
        out=os.path.join(tmp,'reel.mp4')
        log.info('Encoding...')
        subprocess.run([
            imageio_ffmpeg.get_ffmpeg_exe(),'-y',
            '-framerate',str(FPS),
            '-i',os.path.join(tmp,'f%05d.jpg'),
            '-i',audio,
            '-c:v','libx264','-preset','ultrafast','-crf','26',
            '-pix_fmt','yuv420p','-t',str(DURATION),
            '-c:a','aac','-b:a','64k','-shortest',
            out
        ],check=True,capture_output=True,timeout=180)
        log.info('Encoded.')
        log.info('Uploading...')
        r=cloudinary.uploader.upload_large(out,resource_type='video',
            public_id='wbg_daily_reel',overwrite=True,timeout=120)
        url=r['secure_url']
        log.info(f'Done: {url}')
        return url
    finally:
        shutil.rmtree(tmp,ignore_errors=True)
