"""gen_audio.py [out dir] -> synthesises Brinewake's own sound set as 44.1 kHz 16-bit WAV files.
Nothing is sampled or copied: ambience and effects are filtered noise and decaying partials, the music is four
original tunes played on simple additive instruments. Loops wrap seamlessly (tails are folded back to the start)."""
import os
import sys
import wave

import numpy as np
from scipy.signal import butter, lfilter

SR = 44100
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Art", "Audio")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)


def tt(sec):
    return np.arange(int(sec * SR)) / SR


def noise(sec, seed=None):
    r = np.random.default_rng(seed) if seed is not None else rng
    return r.standard_normal(int(sec * SR))


def lp(x, fc, order=2):
    b, a = butter(order, min(fc, SR * 0.49) / (SR / 2))
    return lfilter(b, a, x)


def hp(x, fc, order=2):
    b, a = butter(order, fc / (SR / 2), btype='high')
    return lfilter(b, a, x)


def bp(x, lo, hi, order=2):
    b, a = butter(order, [lo / (SR / 2), min(hi, SR * 0.49) / (SR / 2)], btype='band')
    return lfilter(b, a, x)


def norm(x, peak=0.89):
    return x / max(1e-9, np.abs(x).max()) * peak


def loopify(x, fade=1.5):
    """Fold the tail over the head so the end runs into the start without a seam."""
    n = int(fade * SR)
    w = np.linspace(0.0, 1.0, n) ** 0.5
    body = x[:-n].copy()
    body[:n] = x[:n] * w + x[-n:] * (1.0 - w ** 2) ** 0.5
    return body


def decay(sec, tau):
    return np.exp(-tt(sec) / tau)


def fade(x, a=0.004, r=0.02):
    n, m = int(a * SR), int(r * SR)
    x = x.copy()
    x[:n] *= np.linspace(0, 1, n)
    x[-m:] *= np.linspace(1, 0, m)
    return x


def save(name, x, peak=0.89):
    x = np.asarray(x)
    x = norm(x, peak)
    data = (np.clip(x, -1, 1) * 32767).astype('<i2')
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1 if x.ndim == 1 else 2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print("%-28s %5.1fs %s" % (name, len(x) / SR, "stereo" if x.ndim == 2 else "mono"))


def stereo(l, r):
    n = min(len(l), len(r))
    return np.stack([l[:n], r[:n]], axis=1)


def put(buf, x, at, gain=1.0, wrap=True):
    """Add x into buf at time `at` (seconds); a loop buffer takes the overhang at its start."""
    i = int(at * SR) % len(buf) if wrap else int(at * SR)
    n = len(x)
    if i + n <= len(buf):
        buf[i:i + n] += x * gain
    elif wrap:
        k = len(buf) - i
        buf[i:] += x[:k] * gain
        rest = x[k:]
        while len(rest) > 0:
            m = min(len(rest), len(buf))
            buf[:m] += rest[:m] * gain
            rest = rest[m:]
    else:
        buf[i:] += x[:len(buf) - i] * gain


def room(x, sec=1.1, mix=0.22, seed=3, bright=3500):
    """Circular convolution with a decaying noise tail: a soft hall that also wraps round the loop."""
    ir = lp(noise(sec, seed) * decay(sec, sec / 4.5), bright)
    ir[0] = 0
    wet = np.fft.irfft(np.fft.rfft(x) * np.fft.rfft(ir, len(x)), len(x))
    return x + wet * mix * (np.abs(x).max() / max(1e-9, np.abs(wet).max()))


# ---------------------------------------------------------------- ambience
def ocean(sec=24.0):
    def side(seed, shift):
        n = noise(sec + 1.5, seed)
        t = tt(sec + 1.5)
        swell = (0.5 + 0.5 * np.sin(2 * np.pi * (t + shift) / 8.0)) ** 2.2 * 0.7 + (0.5 + 0.5 * np.sin(2 * np.pi * (t + shift) / 6.0 + 1.7)) ** 3.0 * 0.5
        low = lp(n, 420) * (0.55 + 0.45 * swell) * 1.6
        wash = bp(n, 700, 5200) * (0.10 + swell ** 1.6) * 0.75
        return loopify(low + wash)
    return stereo(side(1, 0.0), side(2, 0.45))


def shore(sec=16.0):
    def side(seed, shift):
        n = noise(sec + 1.5, seed)
        t = (tt(sec + 1.5) + shift) % 8.0
        rise = np.clip(t / 1.6, 0, 1) ** 2 * np.exp(-np.clip(t - 1.6, 0, None) / 2.2)
        fizz = np.clip((t - 1.4) / 0.5, 0, 1) * np.exp(-np.clip(t - 1.9, 0, None) / 2.8)
        return loopify(lp(n, 600) * (0.25 + rise) * 1.4 + bp(n, 1500, 7000) * rise * 0.7 + hp(n, 4000) * fizz * 0.35)
    return stereo(side(11, 0.0), side(12, 0.3))


def wind(sec=20.0):
    def side(seed, ph):
        n = noise(sec + 1.5, seed)
        t = tt(sec + 1.5)
        out = np.zeros_like(n)
        for (lo, hi), per, p0 in (((180, 420), 10.0, 0.0), ((420, 900), 5.0, 1.3), ((900, 1700), 4.0, 2.6)):
            out += bp(n, lo, hi) * (0.5 + 0.5 * np.sin(2 * np.pi * t / per + p0 + ph)) ** 1.5
        return loopify(out * (0.7 + 0.3 * np.sin(2 * np.pi * t / 20.0 + ph)))
    return stereo(side(21, 0.0), side(22, 0.9))


def fire(sec=12.0):
    n = int((sec + 1.5) * SR)
    imp = np.zeros(n)
    for i in rng.integers(0, n, int(22 * sec)):
        imp[i] += rng.uniform(0.2, 1.0) ** 2.5
    crack = np.convolve(imp, bp(noise(0.03, 5), 1200, 7000) * decay(0.03, 0.006), mode='same')
    roar = lp(noise(sec + 1.5, 31), 260) * (1.0 + 0.3 * np.sin(2 * np.pi * tt(sec + 1.5) / 3.0)) * 0.9
    hiss = bp(noise(sec + 1.5, 32), 2500, 6000) * 0.05
    return loopify(crack * 1.8 + roar + hiss)


def chirp(f0, f1, sec, harm=(1.0, 0.4, 0.15), vib=0.0):
    t = tt(sec)
    f = f0 * (f1 / f0) ** (t / sec) * (1.0 + vib * np.sin(2 * np.pi * 28 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = sum(a * np.sin(ph * (k + 1)) for k, a in enumerate(harm))
    return x * np.sin(np.pi * t / sec) ** 0.6


def jungle(sec=20.0):
    n = int(sec * SR)
    t = tt(sec)
    crick = np.sin(2 * np.pi * 4300 * t) * (np.sin(2 * np.pi * 38 * t) > 0.3) * (np.sin(2 * np.pi * t / 2.5) > -0.2) * 0.10
    trill = np.sin(2 * np.pi * 6100 * t + 2.5 * np.sin(2 * np.pi * 55 * t)) * (0.5 + 0.5 * np.sin(2 * np.pi * t / 10.0)) * 0.04
    out = crick + trill + lp(noise(sec, 41), 300) * 0.05
    for at, f0, f1, d, reps in ((1.6, 2600, 3400, 0.12, 3), (6.3, 3800, 2300, 0.20, 2), (9.8, 1900, 2900, 0.09, 5), (14.2, 3100, 4200, 0.14, 3), (17.0, 2200, 1500, 0.3, 1)):
        for k in range(reps):
            put(out, chirp(f0, f1, d, vib=0.01), at + k * d * 1.6, 0.16)
    return room(out, 0.9, 0.3, bright=6000)


def creak_event(sec, f0, f1, res=(420, 950, 1750)):
    t = tt(sec)
    f = f0 + (f1 - f0) * (t / sec) ** 1.5 + 6 * np.sin(2 * np.pi * 3.1 * t)
    saw = 2 * ((np.cumsum(f) / SR) % 1.0) - 1
    saw = np.sign(saw) * np.abs(saw) ** 3
    x = sum(bp(saw, r * 0.85, r * 1.18) * a for r, a in zip(res, (1.0, 0.7, 0.4)))
    return x * np.sin(np.pi * t / sec) ** 1.4


def creak(sec=16.0):
    out = lp(noise(sec, 51), 180) * 0.18
    for at, d, f0, f1 in ((0.8, 1.3, 46, 70), (4.4, 0.9, 80, 58), (7.3, 1.7, 40, 64), (11.0, 0.7, 95, 72), (12.6, 1.4, 52, 44)):
        put(out, creak_event(d, f0, f1), at, 0.5)
    t = tt(sec)
    out += bp(noise(sec, 52), 300, 1400) * (0.5 + 0.5 * np.sin(2 * np.pi * t / 4.0)) ** 3 * 0.10                                    # water slapping the hull
    return room(out, 0.7, 0.25)


def bubbles(sec, count, seed=0, lo=350, hi=1100):
    r = np.random.default_rng(seed)
    out = np.zeros(int(sec * SR))
    for _ in range(count):
        d = r.uniform(0.03, 0.09)
        f = r.uniform(lo, hi)
        put(out, chirp(f, f * r.uniform(1.4, 2.2), d, harm=(1.0,)) * r.uniform(0.3, 1.0), r.uniform(0, sec - d), 1.0, wrap=False)
    return out


def underwater(sec=12.0):
    n = noise(sec + 1.5, 61)
    t = tt(sec + 1.5)
    body = lp(n, 170, 3) * (1.0 + 0.4 * np.sin(2 * np.pi * t / 6.0)) * 2.0 + bp(n, 300, 700) * 0.08
    return loopify(body) + bubbles(sec, 26, 62) * 0.22


def rain(sec=12.0):
    n = noise(sec + 1.5, 71)
    drops = np.zeros(len(n))
    for i in rng.integers(0, len(n), int(260 * sec)):
        drops[i] += rng.uniform(0.2, 1.0)
    return loopify(hp(n, 1800) * 0.5 + bp(n, 400, 1500) * 0.25 + np.convolve(drops, bp(noise(0.01, 72), 2500, 9000) * decay(0.01, 0.002), mode='same') * 0.8)


def thunder(sec=6.0):
    t = tt(sec)
    n = noise(sec, 81)
    rumble = lp(n, 110, 3) * np.exp(-t / 1.8) * (1.0 + 0.6 * np.sin(2 * np.pi * 2.3 * t) * np.exp(-t / 1.2)) * 4.0
    crack = bp(n, 900, 3500) * np.exp(-t / 0.10) * 1.2 + bp(noise(sec, 82), 300, 1200) * np.exp(-np.clip(t - 0.15, 0, None) / 0.5) * (t > 0.15) * 0.9
    return fade(np.tanh((rumble + crack) * 1.3), 0.002, 0.5)


# ---------------------------------------------------------------- one-shots
def gull(kind=0):
    out = np.zeros(int(2.2 * SR))
    notes = ((0.0, 2500, 1700, 0.34), (0.42, 2650, 1750, 0.30), (0.80, 2700, 1700, 0.27), (1.14, 2600, 1600, 0.25), (1.44, 2400, 1500, 0.30)) if kind == 0 else \
            ((0.0, 1900, 2700, 0.16), (0.2, 2800, 1800, 0.5), (0.85, 2700, 1650, 0.55)) if kind == 1 else ((0.0, 2300, 2000, 0.6), (0.7, 2500, 1500, 0.8))
    for at, f0, f1, d in notes:
        put(out, chirp(f0, f1, d, harm=(1.0, 0.55, 0.3, 0.12), vib=0.025), at, 1.0, wrap=False)
    return fade(room(out, 0.8, 0.25, bright=5000), 0.002, 0.2)


def cannon():
    sec = 2.6
    t = tt(sec)
    f = 34 + 85 * np.exp(-t / 0.10)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.45) * 1.6
    n = noise(sec, 91)
    blast = lp(n, 1400) * np.exp(-t / 0.07) * 1.5 + bp(n, 2000, 6000) * np.exp(-t / 0.02) * 0.6
    tail = lp(noise(sec, 92), 240) * np.exp(-t / 0.7) * 1.2 * (1 - np.exp(-t / 0.05))
    return fade(np.tanh((boom + blast + tail) * 1.5), 0.001, 0.4)


def splash(big=True):
    sec = 1.8 if big else 0.8
    t = tt(sec)
    n = noise(sec, 101 if big else 102)
    body = bp(n, 350, 4500) * (1 - np.exp(-t / 0.012)) * np.exp(-t / (0.38 if big else 0.14))
    thump = np.sin(2 * np.pi * (70 if big else 110) * t) * np.exp(-t / 0.09) * (1.2 if big else 0.5)
    spray = hp(noise(sec, 103), 3500) * np.clip((t - 0.08) / 0.1, 0, 1) * np.exp(-np.clip(t - 0.18, 0, None) / (0.5 if big else 0.18)) * 0.35
    return fade(body + thump + spray + bubbles(sec, 14 if big else 5, 104) * 0.25 * np.clip(t / 0.2, 0, 1), 0.001, 0.2)


def step(kind, k):
    r = np.random.default_rng(110 + k)
    if kind == 'sand':
        sec = 0.26
        t = tt(sec)
        x = bp(noise(sec, 120 + k), 250, 2600 + 300 * k) * (1 - np.exp(-t / 0.008)) * np.exp(-t / 0.055) * (1 + 0.5 * r.standard_normal(len(t)) * np.exp(-t / 0.03))
        return fade(x + np.sin(2 * np.pi * 85 * t) * np.exp(-t / 0.03) * 0.5)
    sec = 0.22
    t = tt(sec)
    return fade(np.sin(2 * np.pi * (115 + 14 * k) * t) * np.exp(-t / 0.045) + np.sin(2 * np.pi * (310 + 40 * k) * t) * np.exp(-t / 0.02) * 0.4 + bp(noise(sec, 130 + k), 900, 3500) * np.exp(-t / 0.012) * 0.5)


def swing():
    sec = 0.38
    t = tt(sec)
    n = noise(sec, 141)
    x = sum(bp(n, c * 0.7, c * 1.4) * np.exp(-((t - at) / 0.06) ** 2) for c, at in ((700, 0.08), (1500, 0.14), (2800, 0.19), (1600, 0.25), (800, 0.30)))
    return fade(x)


def clang():
    sec = 1.1
    t = tt(sec)
    x = sum(a * np.sin(2 * np.pi * 1180 * r * t + p) * np.exp(-t / d) for r, a, d, p in ((1, 1.0, 0.30, 0), (2.76, 0.7, 0.22, 1), (5.40, 0.5, 0.15, 2), (8.93, 0.35, 0.09, 3), (1.51, 0.4, 0.26, 4)))
    return fade(x + bp(noise(sec, 151), 2000, 9000) * np.exp(-t / 0.012) * 1.2, 0.0005, 0.1)


def ping(f, sec=0.22):
    t = tt(sec)
    return (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.41 * t) + 0.25 * np.sin(2 * np.pi * f * 3.9 * t)) * np.exp(-t / (sec / 4.5))


def coins():
    out = np.zeros(int(0.9 * SR))
    r = np.random.default_rng(161)
    for k in range(8):
        put(out, ping(r.uniform(3200, 6400)), 0.02 + k * 0.055 + r.uniform(0, 0.03), r.uniform(0.4, 1.0), wrap=False)
    return fade(out, 0.001, 0.1)


def chest_open():
    out = np.zeros(int(1.5 * SR))
    put(out, creak_event(0.55, 150, 240, (700, 1500, 2600)), 0.0, 0.6, wrap=False)
    put(out, step('wood', 0) * 1.4, 0.55, 1.0, wrap=False)
    put(out, coins() * 0.35, 0.60, 1.0, wrap=False)
    return fade(out, 0.002, 0.15)


def blip(freqs, each=0.07, tail=0.12):
    out = np.zeros(int((each * len(freqs) + tail) * SR))
    for k, f in enumerate(freqs):
        t = tt(each + tail)
        put(out, (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t / 0.05) * (1 - np.exp(-t / 0.003)), k * each, 1.0, wrap=False)
    return fade(out, 0.001, 0.02)


def bell():
    sec = 3.5
    t = tt(sec)
    x = sum(a * np.sin(2 * np.pi * 640 * r * t + p) * np.exp(-t / d) for r, a, d, p in ((0.5, 0.5, 2.2, 0), (1.0, 1.0, 1.6, 1), (1.19, 0.6, 1.2, 2), (1.5, 0.45, 0.9, 3), (2.0, 0.5, 0.7, 4), (2.51, 0.3, 0.45, 5),
                                                                                    (3.01, 0.2, 0.3, 6)))
    return fade(x + bp(noise(sec, 171), 1500, 6000) * np.exp(-t / 0.01) * 0.8, 0.0005, 0.6)


def stroke(k):
    sec = 0.9
    t = tt(sec)
    n = noise(sec, 181 + k)
    x = bp(n, 300 + 80 * k, 2600) * np.sin(np.pi * np.clip(t / 0.7, 0, 1)) ** 1.5 * (1 + 0.4 * np.sin(2 * np.pi * 9 * t))
    return fade(x * 0.9 + bubbles(sec, 7, 190 + k) * 0.3, 0.01, 0.15)


def dig():
    sec = 0.6
    t = tt(sec)
    scrape = bp(noise(sec, 201), 900, 4500) * np.clip(t / 0.05, 0, 1) * np.exp(-np.clip(t - 0.22, 0, None) / 0.06) * (1 + 0.6 * np.sin(2 * np.pi * 60 * t))
    return fade(scrape + np.sin(2 * np.pi * 75 * t) * np.exp(-t / 0.05) * 0.9)


def gulp():
    out = np.zeros(int(0.9 * SR))
    for k in range(3):
        put(out, chirp(170, 85, 0.11, harm=(1.0, 0.3)) + bp(noise(0.11, 210 + k), 300, 900) * decay(0.11, 0.03) * 0.3, 0.05 + 0.26 * k, 1.0, wrap=False)
    return fade(out)


def thud():
    sec = 0.35
    t = tt(sec)
    return fade(np.sin(2 * np.pi * (60 + 50 * np.exp(-t / 0.03)) * t) * np.exp(-t / 0.08) + bp(noise(sec, 221), 200, 1500) * np.exp(-t / 0.03) * 0.6)


# ---------------------------------------------------------------- instruments and tunes
def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def pluck(m, sec=1.6, bright=1.0):
    t = tt(sec)
    f = hz(m)
    return sum(np.sin(2 * np.pi * f * k * t) * np.exp(-t * (2.2 + 1.1 * k / bright)) / k for k in range(1, 9)) * (1 - np.exp(-t / 0.002))


def bassn(m, sec=0.7):
    t = tt(sec)
    f = hz(m)
    return (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(4 * np.pi * f * t) * np.exp(-t * 6) + 0.25 * np.sin(6 * np.pi * f * t) * np.exp(-t * 10)) * np.exp(-t * 3.2) * (1 - np.exp(-t / 0.004))


def reed(m, sec, vib=0.004, bright=1.25, att=0.04):
    """Concertina-like: two slightly detuned reeds, vibrato that arrives late."""
    t = tt(sec + 0.12)
    out = np.zeros(len(t))
    for det in (-0.0025, 0.0025):
        f = hz(m) * (1 + det) * (1 + vib * np.sin(2 * np.pi * 5.4 * t) * np.clip((t - 0.18) / 0.2, 0, 1))
        ph = 2 * np.pi * np.cumsum(f) / SR
        out += sum(np.sin(ph * k) / k ** bright for k in range(1, 11) if hz(m) * k < 9000)
    env = np.clip(t / att, 0, 1) * np.clip((sec + 0.12 - t) / 0.12, 0, 1)
    return out * env


def whistle(m, sec):
    t = tt(sec + 0.08)
    f = hz(m) * (1 - 0.03 * np.exp(-t / 0.035)) * (1 + 0.006 * np.sin(2 * np.pi * 5.2 * t) * np.clip((t - 0.15) / 0.2, 0, 1))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.22 * np.sin(2 * ph) + 0.07 * np.sin(3 * ph) + bp(noise(sec + 0.08), hz(m) * 0.8, hz(m) * 1.6) * 0.05
    return x * np.clip(t / 0.03, 0, 1) * np.clip((sec + 0.08 - t) / 0.08, 0, 1)


def fiddle(m, sec):
    t = tt(sec + 0.06)
    f = hz(m) * (1 + 0.006 * np.sin(2 * np.pi * 6.1 * t) * np.clip((t - 0.1) / 0.15, 0, 1))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = sum(np.sin(ph * k) / k * (1.25 if k in (3, 4) else 1.0) for k in range(1, 14) if hz(m) * k < 10000) + bp(noise(sec + 0.06), 2000, 6000) * 0.02
    return x * np.clip(t / 0.045, 0, 1) * np.clip((sec + 0.06 - t) / 0.06, 0, 1)


def drum(kind='low'):
    if kind == 'low':
        t = tt(0.5)
        return np.sin(2 * np.pi * (52 + 40 * np.exp(-t / 0.035)) * t) * np.exp(-t / 0.13) + lp(noise(0.5), 500) * np.exp(-t / 0.03) * 0.35
    if kind == 'tick':
        t = tt(0.08)
        return bp(noise(0.08), 1500, 5000) * np.exp(-t / 0.012)
    if kind == 'clap':
        t = tt(0.25)
        return bp(noise(0.25), 800, 3200) * (np.exp(-t / 0.012) + np.exp(-np.clip(t - 0.012, 0, None) / 0.012) * (t > 0.012) + np.exp(-np.clip(t - 0.026, 0, None) / 0.06) * (t > 0.026))
    t = tt(0.9)                                                      # war drum
    return np.tanh((np.sin(2 * np.pi * (38 + 34 * np.exp(-t / 0.05)) * t) * np.exp(-t / 0.28) + lp(noise(0.9), 300) * np.exp(-t / 0.06) * 0.5) * 1.6)


CH = {'Dm': (50, 53, 57), 'C': (48, 52, 55), 'F': (53, 57, 60), 'Am': (45, 48, 52), 'G': (43, 47, 50), 'Em': (40, 43, 47), 'D': (50, 54, 57), 'Bb': (46, 50, 53), 'Gm': (43, 46, 50)}


def tune(bars, chords, e, lead, passes=2, pad=0.0, strum=True, drums=True, lead2=None, swing_claps=False):
    """bars: list of bars, each a list of (midi, eighths); chords: one name per bar; e = seconds per eighth, six to the bar."""
    bar = 6 * e
    total = bar * len(bars) * passes
    L, R = np.zeros(int(total * SR)), np.zeros(int(total * SR))

    def add(x, at, gain, pan):
        put(L, x, at, gain * (1 - pan) ** 0.5)
        put(R, x, at, gain * pan ** 0.5)

    for ps in range(passes):
        for b, (notes, ch) in enumerate(zip(bars, chords)):
            t0 = (ps * len(bars) + b) * bar
            root = CH[ch]
            at = 0.0
            for m, n in notes:
                add(lead(m, n * e * 0.94), t0 + at, 0.55, 0.46)
                if lead2 is not None and ps >= 1:
                    add(lead2(m + 12, n * e * 0.94), t0 + at, 0.20, 0.64)
                at += n * e
            add(bassn(root[0] - 12, e * 3.2), t0, 0.60, 0.5)
            add(bassn(root[2] - 12 if b % 2 else root[0] - 12, e * 2.6), t0 + 3 * e, 0.48, 0.5)
            if strum:
                for k, (step_, vel) in enumerate(((0, 0.9), (2, 0.5), (3, 0.8), (5, 0.55))):
                    for j, m in enumerate(root):
                        add(pluck(m + 12, 1.1), t0 + step_ * e + j * 0.012, 0.11 * vel, 0.25 + 0.1 * j)
            if pad:
                for m in root:
                    add(reed(m + 12, bar * 0.97, vib=0.002, bright=1.7, att=0.25), t0, pad, 0.72)
            if drums:
                add(drum('low'), t0, 0.50, 0.5)
                add(drum('low'), t0 + 3 * e, 0.36, 0.5)
                for s_ in (2, 5):
                    add(drum('tick'), t0 + s_ * e, 0.16, 0.62)
                if swing_claps and ps >= 1:
                    add(drum('clap'), t0 + 3 * e, 0.22, 0.4)
    return stereo(room(L, 1.2, 0.20, 5), room(R, 1.2, 0.20, 6))


THEME = [[(62, 2), (65, 1), (69, 2), (74, 1)], [(72, 1), (74, 1), (72, 1), (69, 3)], [(67, 2), (64, 1), (67, 2), (72, 1)], [(69, 3), (65, 2), (62, 1)],
         [(62, 2), (65, 1), (69, 2), (74, 1)], [(77, 2), (76, 1), (74, 2), (72, 1)], [(72, 1), (74, 1), (72, 1), (67, 2), (64, 1)], [(62, 5), (69, 1)],
         [(77, 3), (72, 2), (69, 1)], [(76, 3), (72, 2), (67, 1)], [(74, 2), (77, 1), (74, 2), (69, 1)], [(72, 3), (69, 3)],
         [(65, 1), (69, 1), (72, 1), (77, 2), (72, 1)], [(64, 1), (67, 1), (72, 1), (76, 2), (72, 1)], [(74, 1), (72, 1), (69, 1), (67, 1), (64, 1), (60, 1)], [(62, 6)]]
THEME_CH = ['Dm', 'Dm', 'C', 'Dm', 'Dm', 'F', 'C', 'Dm', 'F', 'C', 'Dm', 'Am', 'F', 'C', 'C', 'Dm']
JIG = [[(67, 1), (71, 1), (74, 1), (79, 2), (74, 1)], [(76, 1), (74, 1), (71, 1), (74, 3)], [(72, 1), (76, 1), (79, 1), (76, 2), (72, 1)], [(74, 1), (78, 1), (74, 1), (69, 3)],
       [(67, 1), (71, 1), (74, 1), (79, 2), (74, 1)], [(76, 2), (79, 1), (76, 2), (71, 1)], [(72, 1), (76, 1), (72, 1), (74, 1), (78, 1), (74, 1)], [(79, 3), (67, 3)],
       [(76, 2), (71, 1), (76, 2), (79, 1)], [(76, 1), (72, 1), (76, 1), (79, 2), (76, 1)], [(74, 1), (71, 1), (74, 1), (79, 2), (74, 1)], [(78, 2), (74, 1), (69, 3)],
       [(76, 2), (71, 1), (76, 2), (79, 1)], [(84, 2), (79, 1), (76, 2), (72, 1)], [(74, 1), (76, 1), (78, 1), (81, 2), (78, 1)], [(79, 6)]]
JIG_CH = ['G', 'G', 'C', 'D', 'G', 'Em', 'C', 'G', 'Em', 'C', 'G', 'D', 'Em', 'C', 'D', 'G']


def calm(sec=64.0):
    L, R = np.zeros(int(sec * SR)), np.zeros(int(sec * SR))
    prog = ['Dm', 'Bb', 'F', 'C', 'Dm', 'Gm', 'Bb', 'C']
    r = np.random.default_rng(301)
    for i, ch in enumerate(prog):
        t0 = i * 8.0
        for j, m in enumerate(CH[ch]):
            x = reed(m + 12, 8.4, vib=0.0015, bright=2.2, att=2.2)
            put(L, x, t0, 0.10 * (1.2 - 0.2 * j))
            put(R, np.roll(x, 300), t0, 0.10 * (0.8 + 0.2 * j))
        put(L, bassn(CH[ch][0] - 12, 5.0), t0, 0.35)
        put(R, bassn(CH[ch][0] - 12, 5.0), t0, 0.35)
        tones = [CH[ch][k % 3] + 24 + 12 * (k // 3) for k in range(5)]
        for k in range(7):
            m = tones[int(r.integers(0, 5))]
            at = t0 + 0.6 + k * 1.05 + r.uniform(-0.05, 0.05)
            pan = r.uniform(0.2, 0.8)
            x = pluck(m, 3.5, 0.7)
            put(L, x, at, 0.12 * (1 - pan))
            put(R, x, at, 0.12 * pan)
    for at, m, d in ((16.0, 81, 3.5), (20.0, 77, 3.0), (24.0, 79, 5.5), (48.0, 74, 3.5), (52.0, 77, 3.0), (56.0, 76, 5.5)):
        x = whistle(m, d)
        put(L, x, at, 0.07)
        put(R, x, at + 0.01, 0.06)
    return stereo(room(L, 2.4, 0.45, 7, 3000), room(R, 2.4, 0.45, 8, 3000))


def battle(e=0.17):
    bar = 8 * e
    prog = ['Dm', 'Dm', 'Bb', 'C', 'Dm', 'Dm', 'Gm', 'C']
    total = bar * len(prog) * 2
    L, R = np.zeros(int(total * SR)), np.zeros(int(total * SR))
    for ps in range(2):
        for b, ch in enumerate(prog):
            t0 = (ps * len(prog) + b) * bar
            for s_, g in ((0, 1.0), (3, 0.7), (4, 0.5), (6, 0.85), (7, 0.4)):
                x = drum('war')
                put(L, x, t0 + s_ * e, 0.55 * g)
                put(R, x, t0 + s_ * e, 0.55 * g)
            for s_ in range(8):
                x = fiddle(CH[ch][0] + (0 if s_ % 4 else 12), e * 0.6)
                put(L, x, t0 + s_ * e, 0.14)
                put(R, x, t0 + s_ * e, 0.09)
                if s_ % 2 == 1:
                    put(R, drum('tick'), t0 + s_ * e, 0.14)
            for m in CH[ch]:
                x = reed(m, bar * 0.9, vib=0.0, bright=1.1, att=0.02)
                put(L, x, t0, 0.07)
                put(R, x, t0, 0.10)
            if ps == 1:
                for k, m in enumerate((CH[ch][2] + 24, CH[ch][1] + 24, CH[ch][0] + 24, CH[ch][1] + 24)):
                    x = reed(m, e * 1.9, bright=1.0)
                    put(L, x, t0 + k * 2 * e, 0.12)
                    put(R, x, t0 + k * 2 * e, 0.10)
    return stereo(room(L, 1.4, 0.25, 9), room(R, 1.4, 0.25, 10))


def sting():
    L = np.zeros(int(4.2 * SR))
    for k, m in enumerate((62, 65, 69, 74, 77, 81)):
        put(L, pluck(m + 12, 2.5, 1.4), 0.09 * k, 0.5, wrap=False)
        put(L, whistle(m + 12, 0.25), 0.09 * k, 0.25, wrap=False)
    for m in (62, 66, 69, 74):
        put(L, reed(m, 2.6, bright=1.4, att=0.05), 0.6, 0.20, wrap=False)
    put(L, coins() * 0.5, 0.55, 1.0, wrap=False)
    x = L + np.convolve(L, lp(noise(1.2, 3) * decay(1.2, 0.3), 4000), mode='full')[:len(L)] * 0.004
    return fade(x, 0.002, 0.6)


save("A_BW_Ocean_Loop", ocean())
save("A_BW_Shore_Loop", shore())
save("A_BW_Wind_Loop", wind(), 0.7)
save("A_BW_Fire_Loop", fire())
save("A_BW_Jungle_Loop", jungle(), 0.6)
save("A_BW_Ship_Creak_Loop", creak(), 0.8)
save("A_BW_Underwater_Loop", underwater())
save("A_BW_Rain_Loop", rain(), 0.7)
save("A_BW_Thunder", thunder())
for k in range(3):
    save("A_BW_Gull_%02d" % (k + 1), gull(k), 0.7)
save("A_BW_Cannon_Fire", cannon(), 0.97)
save("A_BW_Splash_Big", splash(True))
save("A_BW_Splash_Small", splash(False), 0.7)
for k in range(3):
    save("A_BW_Step_Sand_%02d" % (k + 1), step('sand', k), 0.6)
    save("A_BW_Step_Wood_%02d" % (k + 1), step('wood', k), 0.7)
save("A_BW_Sword_Swing", swing(), 0.7)
save("A_BW_Sword_Clang", clang())
save("A_BW_Coins", coins(), 0.7)
save("A_BW_Chest_Open", chest_open())
save("A_BW_UI_Click", blip((1250,), 0.03, 0.06), 0.5)
save("A_BW_UI_Hover", blip((900,), 0.02, 0.04), 0.3)
save("A_BW_Pickup", blip((660, 990, 1320)), 0.6)
save("A_BW_Bell", bell())
save("A_BW_Swim_Stroke_01", stroke(0), 0.7)
save("A_BW_Swim_Stroke_02", stroke(1), 0.7)
save("A_BW_Dig", dig(), 0.8)
save("A_BW_Drink", gulp(), 0.6)
save("A_BW_Land", thud(), 0.8)
save("M_BW_Theme", tune(THEME, THEME_CH, 0.21, lambda m, d: reed(m, d), passes=2, pad=0.035, lead2=whistle))
save("M_BW_Tavern", tune(JIG, JIG_CH, 0.16, fiddle, passes=2, lead2=whistle, swing_claps=True))
save("M_BW_Calm", calm(), 0.8)
save("M_BW_Battle", battle())
save("M_BW_Sting_Treasure", sting(), 0.8)
