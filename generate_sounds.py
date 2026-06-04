
"""
WBG Sound Design Generator
Run this once locally or on Railway to generate all sound effect files.
Creates assets/sounds/ folder with .wav files for each sound type.
"""
import numpy as np
import wave, os, struct, math

SAMPLE_RATE = 44100
ASSETS_DIR  = os.path.join(os.path.dirname(__file__), 'assets', 'sounds')
os.makedirs(ASSETS_DIR, exist_ok=True)

def save_wav(filename, samples, sr=SAMPLE_RATE):
    path = os.path.join(ASSETS_DIR, filename)
    samples = np.clip(samples, -1.0, 1.0)
    data    = (samples * 32767).astype(np.int16)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(data.tobytes())
    print(f'✅ {filename} ({len(samples)/sr:.2f}s)')
    return path

def envelope(samples, attack=0.01, decay=0.1, sustain=0.7, release=0.3):
    n     = len(samples)
    env   = np.ones(n)
    a     = int(attack * SAMPLE_RATE)
    d     = int(decay  * SAMPLE_RATE)
    r     = int(release* SAMPLE_RATE)
    s_end = n - r
    if a > 0:   env[:a]    = np.linspace(0, 1, a)
    if d > 0:   env[a:a+d] = np.linspace(1, sustain, min(d, n-a))
    if r > 0 and s_end > 0: env[s_end:] = np.linspace(sustain, 0, n-s_end)
    return samples * env

def sine(freq, duration, amplitude=0.5):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    return amplitude * np.sin(2 * np.pi * freq * t)

def noise(duration, amplitude=0.3):
    n = int(SAMPLE_RATE * duration)
    return amplitude * (np.random.random(n) * 2 - 1)

def sweep(f_start, f_end, duration, amplitude=0.4):
    t   = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    f_t = np.linspace(f_start, f_end, len(t))
    phase = np.cumsum(2 * np.pi * f_t / SAMPLE_RATE)
    return amplitude * np.sin(phase)

# ── 1. LUXURY CHIME (home tour price reveal) ─────────────────────────────────
# Soft bell-like tone — elegant, aspirational
def make_luxury_chime():
    dur   = 1.8
    t     = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
    # Fundamental + harmonics for bell character
    s  = 0.5  * np.sin(2*np.pi*880*t)   * np.exp(-3.5*t)
    s += 0.25 * np.sin(2*np.pi*1760*t)  * np.exp(-5.0*t)
    s += 0.12 * np.sin(2*np.pi*2640*t)  * np.exp(-7.0*t)
    s += 0.06 * np.sin(2*np.pi*3520*t)  * np.exp(-9.0*t)
    # Soft attack
    attack = int(0.005 * SAMPLE_RATE)
    s[:attack] *= np.linspace(0, 1, attack)
    save_wav('chime_luxury.wav', s * 0.7)

# ── 2. CINEMATIC WHOOSH (neighborhood name reveal) ───────────────────────────
# Upward sweep with air texture — builds anticipation
def make_cinematic_whoosh():
    dur = 0.6
    # Frequency sweep 80Hz → 3000Hz
    sw  = sweep(80, 3000, dur, amplitude=0.35)
    # Add air/noise texture
    n   = noise(dur, amplitude=0.15)
    # High-pass character on noise
    from numpy.fft import fft, ifft, fftfreq
    N    = len(n)
    freq = fftfreq(N, 1/SAMPLE_RATE)
    F    = fft(n)
    F[np.abs(freq) < 500] *= 0.1
    n_hp = np.real(ifft(F))
    s    = sw + n_hp * 0.3
    # Fast attack, quick decay
    env  = np.exp(-3.5 * np.linspace(0, 1, len(s)) ** 0.5)
    env[:int(0.02*SAMPLE_RATE)] = np.linspace(0, 1, int(0.02*SAMPLE_RATE))
    save_wav('whoosh_cinematic.wav', s * env * 0.8)

# ── 3. STAT REVEAL PING (data/stat number appears) ───────────────────────────
# Sharp metallic ping — confident, authoritative
def make_stat_ping():
    dur = 1.2
    t   = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
    # Metallic tone with inharmonic partials
    s  = 0.5  * np.sin(2*np.pi*1200*t) * np.exp(-4.0*t)
    s += 0.3  * np.sin(2*np.pi*1847*t) * np.exp(-6.0*t)
    s += 0.15 * np.sin(2*np.pi*2531*t) * np.exp(-8.0*t)
    # Very sharp attack
    attack = int(0.003 * SAMPLE_RATE)
    s[:attack] *= np.linspace(0, 1, attack)
    save_wav('ping_stat.wav', s * 0.65)

# ── 4. DEEP BASS PULSE (dark post opener) ────────────────────────────────────
# Low cinematic thud — gravitas, sets serious tone
def make_bass_pulse():
    dur = 1.5
    t   = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
    # Sub-bass fundamental
    s  = 0.6  * np.sin(2*np.pi*60*t)  * np.exp(-2.5*t)
    s += 0.3  * np.sin(2*np.pi*120*t) * np.exp(-4.0*t)
    s += 0.1  * np.sin(2*np.pi*180*t) * np.exp(-6.0*t)
    # Soft noise layer for texture
    n  = noise(dur, 0.08)
    s  = s + n
    attack = int(0.008 * SAMPLE_RATE)
    s[:attack] *= np.linspace(0, 1, attack)
    save_wav('bass_pulse.wav', s * 0.75)

# ── 5. AMBIENT WAVE (lifestyle posts) ────────────────────────────────────────
# Soft ocean-like wash — warm, inviting, San Diego
def make_ambient_wave():
    dur = 3.0
    sr  = SAMPLE_RATE
    n   = int(sr * dur)
    # Layered filtered noise to simulate waves
    raw = np.random.random(n) * 2 - 1
    # Low-pass filter (simple moving average)
    window = int(sr * 0.015)
    padded = np.pad(raw, (window//2, window//2), mode='edge')
    filtered = np.convolve(padded, np.ones(window)/window, mode='valid')[:n]
    # Wave rhythm - slow swell
    t     = np.linspace(0, dur, n)
    swell = 0.4 + 0.6 * (0.5 + 0.5 * np.sin(2*np.pi*0.3*t))
    s     = filtered * swell * 0.5
    # Fade in/out
    fade  = int(sr * 0.4)
    s[:fade]  *= np.linspace(0, 1, fade)
    s[-fade:] *= np.linspace(1, 0, fade)
    save_wav('ambient_wave.wav', s)

# ── 6. SOFT REVEAL (light posts - text appearing) ────────────────────────────
# Gentle airy swoosh — clean, modern, approachable
def make_soft_reveal():
    dur = 0.4
    sw  = sweep(200, 1800, dur, amplitude=0.25)
    n   = noise(dur, 0.08)
    s   = sw + n
    env = np.linspace(1, 0, len(s)) ** 1.5
    env[:int(0.01*SAMPLE_RATE)] = np.linspace(0, 1, int(0.01*SAMPLE_RATE))
    save_wav('reveal_soft.wav', s * env * 0.6)

# ── 7. MARKET DATA TENSION BUILD ─────────────────────────────────────────────
# Low drone that builds — signals important data incoming
def make_tension_build():
    dur = 2.0
    t   = np.linspace(0, dur, int(SAMPLE_RATE * dur), False)
    # Rising drone
    f_t = 80 + 40 * (t/dur)**2
    phase = np.cumsum(2 * np.pi * f_t / SAMPLE_RATE)
    s   = 0.4 * np.sin(phase)
    s  += 0.2 * np.sin(phase * 2)
    # Crescendo envelope
    env = (t/dur) ** 0.7
    s   = s * env
    fade_out = int(0.1 * SAMPLE_RATE)
    s[-fade_out:] *= np.linspace(1, 0, fade_out)
    save_wav('tension_build.wav', s * 0.6)

# Generate all sounds
print('Generating WBG sound design assets...')
make_luxury_chime()
make_cinematic_whoosh()
make_stat_ping()
make_bass_pulse()
make_ambient_wave()
make_soft_reveal()
make_tension_build()
print(f'\nAll sounds generated in {ASSETS_DIR}')
