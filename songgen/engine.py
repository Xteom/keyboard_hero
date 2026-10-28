"""Synthesis engine for the keyboard_hero power-metal tracks.

Every sound is generated here from oscillators and noise: Karplus-Strong strings run
through an amp/cab simulation for guitars and bass, analog-style drum synthesis, square/saw
synth leads, supersaw pads and FM bells. No samples or third-party audio are used.
"""
import numpy as np
from scipy import signal
from scipy.ndimage import maximum_filter1d, uniform_filter1d

SR = 44100
_SOS = {}


# ---------------------------------------------------------------- basic DSP helpers

def mtof(m):
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=float) - 69.0) / 12.0)


def _sos(kind, f, order):
    key = (kind, f if np.isscalar(f) else tuple(f), order)
    if key not in _SOS:
        _SOS[key] = signal.butter(order, f, btype=kind, fs=SR, output='sos')
    return _SOS[key]


def hp(x, f, order=2):
    return signal.sosfilt(_sos('highpass', f, order), x, axis=-1)


def lp(x, f, order=2):
    return signal.sosfilt(_sos('lowpass', f, order), x, axis=-1)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(_sos('bandpass', (lo, hi), order), x, axis=-1)


def peq(x, f0, gain_db, q=1.0):
    """RBJ peaking EQ."""
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / SR
    al = np.sin(w0) / (2 * q)
    b = np.array([1 + al * A, -2 * np.cos(w0), 1 - al * A])
    a = np.array([1 + al / A, -2 * np.cos(w0), 1 - al / A])
    return signal.lfilter(b / a[0], a / a[0], x, axis=-1)


def add(buf, x, start):
    """Mix x into buf (mono or stereo) at sample index start, clipped to bounds."""
    if start >= buf.shape[-1]:
        return
    if start < 0:
        x = x[..., -start:]
        start = 0
    n = min(x.shape[-1], buf.shape[-1] - start)
    if n > 0:
        buf[..., start:start + n] += x[..., :n]


def pan(x, p):
    """Constant-power pan of a mono signal, p in [-1, 1]."""
    a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)])


def _blep(ph, dt):
    out = np.zeros_like(ph)
    m = ph < dt
    x = ph[m] / dt[m]
    out[m] = x + x - x * x - 1.0
    m = ph > 1.0 - dt
    x = (ph[m] - 1.0) / dt[m]
    out[m] = x * x + x + x + 1.0
    return out


def saw(f, ph0=0.0):
    dt = f / SR
    ph = (ph0 + np.cumsum(dt)) % 1.0
    return 2.0 * ph - 1.0 - _blep(ph, dt)


def square(f, pw=0.5, ph0=0.0):
    dt = f / SR
    ph = (ph0 + np.cumsum(dt)) % 1.0
    y = np.where(ph < pw, 1.0, -1.0)
    y += _blep(ph, dt)
    y -= _blep((ph + 1.0 - pw) % 1.0, dt)
    return y


# ---------------------------------------------------------------- strings

def pluck(freq, dur, t60, bright, rng, rel=0.02, pick_pos=0.12):
    """Karplus-Strong string, vectorised one period at a time.

    The loop filter is a 3-tap lowpass whose weights also provide the fractional delay,
    so pitch is accurate. t60 is the decay time; bright in (0, 1] filters the excitation.
    """
    n = int((dur + rel) * SR)
    P = SR / freq
    N = int(np.floor(P - 0.5))
    w = N + 1.5 - P
    g = 10 ** (-3.0 / (t60 * freq))
    exc = rng.uniform(-1, 1, N)
    exc = signal.lfilter([bright], [1, bright - 1], exc)
    d = max(1, int(pick_pos * N))
    exc[d:] = exc[d:] - exc[:-d]
    O = 2
    buf = np.zeros(n + O)
    m = min(N, n)
    buf[O:O + m] = exc[:m]
    a0, a1, a2 = 0.5 * w * g, 0.5 * g, 0.5 * (1 - w) * g
    s = N
    while s < n:
        e = min(s + N, n)
        buf[O + s:O + e] = (a0 * buf[O + s - N:O + e - N] + a1 * buf[O + s - N - 1:O + e - N - 1]
                            + a2 * buf[O + s - N - 2:O + e - N - 2])
        s = e
    y = buf[O:]
    r = min(int(rel * SR), n)
    if r > 0:
        y[-r:] *= np.linspace(1, 0, r)
    return y


def amp(di, gain_db=36, pre_hp=90, mid_f=700, mid_db=3, bias=0.2, cab_lp=6000, presence=3000):
    """High-gain amp: tight boost -> asymmetric tanh (2x oversampled) -> 4x12 cab EQ."""
    x = hp(di, pre_hp)
    x = peq(x, mid_f, mid_db, 0.7)
    x = lp(x, 6500)
    up = signal.resample_poly(x, 2, 1)
    g = 10 ** (gain_db / 20)
    y = np.tanh(g * up + bias) - np.tanh(bias)
    y = signal.resample_poly(y, 1, 2)[:len(di)]
    y = hp(y, 75)
    y = peq(y, 150, 5, 0.7)
    y = peq(y, 450, -4, 1.0)
    y = peq(y, 950, -4, 0.9)
    y = peq(y, presence, 5, 1.0)
    y = lp(y, cab_lp, 4)
    y = peq(y, 7000, -6, 0.8)
    return y


def render_rhythm(events, total, seed):
    """One rhythm-guitar take (DI). events: (t, dur, [midi], muted, vel)."""
    rng = np.random.default_rng(seed)
    di = np.zeros(total)
    for t, dur, notes, mute, vel in events:
        t0 = t + rng.normal(0, 0.004)
        for k, m in enumerate(notes):
            f = mtof(m) * 2 ** (rng.normal(0, 4) / 1200)
            if mute:
                x = lp(pluck(f, min(dur, 0.22), 0.12, 0.3, rng, rel=0.01), 1300)
            else:
                x = pluck(f, dur, 4.0, 0.7, rng, rel=0.03)
            add(di, x * vel * (1.0 if k == 0 else 0.85), int((t0 + 0.0025 * k) * SR))
    return di


def render_bass(events, total, seed):
    """events: (t, dur, midi, muted, vel)."""
    rng = np.random.default_rng(seed)
    di = np.zeros(total)
    for t, dur, m, mute, vel in events:
        f = mtof(m)
        if mute:
            x = pluck(f, min(dur, 0.3), 0.6, 0.45, rng, rel=0.015)
        else:
            x = pluck(f, dur, 2.5, 0.55, rng, rel=0.03)
        add(di, x * vel, int((t + rng.normal(0, 0.002)) * SR))
    y = np.tanh(1.6 * di)
    y = lp(y, 1600)
    y = hp(y, 35)
    y = peq(y, 900, 1.5, 1.0)
    y = peq(y, 80, 4, 0.7)
    return y


# ---------------------------------------------------------------- mono lead voices

def curves(events, total, kind='guitar'):
    """Pitch (semitones), amplitude and pluck envelopes for a monophonic voice.

    events: (t, dur, midi, flags) where flags may hold vib, bend (semitones), dive,
    pinch, legato and vel.
    """
    semis = np.full(total, np.nan)
    env = np.zeros(total)
    pk = np.zeros(total)
    picks = []
    for t, dur, m, fl in sorted(events, key=lambda e: e[0]):
        i0 = int(t * SR)
        if i0 >= total:
            continue
        i1 = min(total, i0 + max(2, int(dur * SR)))
        L = i1 - i0
        tt = np.arange(L) / SR
        D = L / SR
        c = np.full(L, float(m))
        if fl.get('pinch'):
            c += 19
        if fl.get('bend'):
            bt = min(0.11, 0.45 * D)
            r = np.clip(tt / bt, 0, 1)
            c -= fl['bend'] * (1 - r) ** 2
        if fl.get('dive'):
            c -= fl['dive'] * (tt / D) ** 1.3
        if fl.get('vib') or fl.get('pinch'):
            depth = 0.9 if fl.get('pinch') else 0.45
            on = min(0.12, 0.3 * D)
            ramp = np.clip((tt - on) / 0.18, 0, 1)
            c += depth * ramp * 0.5 * (1 - np.cos(2 * np.pi * 6.2 * tt))
        semis[i0:i1] = c
        vel = fl.get('vel', 1.0)
        leg = fl.get('legato', False)
        if kind == 'guitar':
            e = (0.72 + 0.28 * np.exp(-tt / 0.09)) * (0.85 if leg else 1.0)
        else:
            e = 0.8 + 0.2 * np.exp(-tt / 0.06)
        att = min(L, int((0.0005 if leg else 0.002) * SR))
        if att > 0:
            e[:att] *= np.linspace(0, 1, att, endpoint=False)
        rel = min(L, int(0.006 * SR))
        e[L - rel:] *= np.linspace(1, 0, rel)
        env[i0:i1] = np.maximum(env[i0:i1], e * vel)
        if not leg:
            pk[i0:i1] = np.maximum(pk[i0:i1], np.exp(-tt / 0.04))
            picks.append((i0, vel))
    valid = ~np.isnan(semis)
    if not valid.any():
        semis[:] = 60.0
    else:
        idx = np.where(valid, np.arange(total), 0)
        np.maximum.accumulate(idx, out=idx)
        idx[:np.argmax(valid)] = np.argmax(valid)
        semis = semis[idx]
    semis = uniform_filter1d(semis, int(0.003 * SR))
    return semis, env, pk, picks


def render_lead_guitar(events, total, seed, gain_db=30):
    rng = np.random.default_rng(seed)
    semis, env, pk, picks = curves(events, total, 'guitar')
    f = mtof(semis)
    osc = 0.65 * saw(f, rng.random()) + 0.35 * square(f * 1.002, 0.3, rng.random())
    dark = lp(osc, 1600)
    bright = lp(osc, 4500)
    x = (dark + (bright - dark) * pk) * env
    nb = int(0.004 * SR)
    burst = hp(rng.uniform(-1, 1, nb), 2000) * np.linspace(1, 0, nb)
    for i0, v in picks:
        add(x, burst * 0.25 * v, i0)
    y = amp(x, gain_db=gain_db, pre_hp=350, mid_f=1500, mid_db=4, bias=0.1, cab_lp=6500, presence=3200)
    gate = uniform_filter1d((env > 1e-4).astype(float), int(0.01 * SR))
    return y * gate


def render_synth(events, total, seed, wave='square'):
    rng = np.random.default_rng(seed)
    semis, env, pk, _ = curves(events, total, 'synth')
    f = mtof(semis)
    if wave == 'square':
        osc = 0.6 * square(f, 0.5, rng.random()) + 0.4 * square(f * 2 ** (8 / 1200), 0.25, rng.random())
    else:
        osc = 0.5 * saw(f, rng.random()) + 0.5 * saw(f * 2 ** (10 / 1200), rng.random())
    return lp(osc * env, 7500)


# ---------------------------------------------------------------- pads and bells

def render_pad(events, total, seed):
    """Supersaw chords. events: (t, dur, [midi], vel)."""
    rng = np.random.default_rng(seed)
    out = np.zeros((2, total))
    for t, dur, notes, vel in events:
        n = int((dur + 0.6) * SR)
        tt = np.arange(n) / SR
        e = np.minimum(1, tt / 0.25) * np.where(tt < dur, 1.0, np.clip(1 - (tt - dur) / 0.6, 0, 1))
        for m in notes:
            for k, det in enumerate((-12, -5, 0, 5, 12)):
                v = saw(np.full(n, mtof(m) * 2 ** (det / 1200)), rng.random()) * e * vel * 0.2
                add(out, pan(v, (k - 2) / 2.5), int(t * SR))
    return hp(lp(out, 2600), 140)


def render_bells(events, total):
    """FM bells. events: (t, dur, midi, vel)."""
    out = np.zeros(total)
    for t, dur, m, vel in events:
        n = int(min(dur + 1.5, 3.0) * SR)
        tt = np.arange(n) / SR
        f = mtof(m)
        mod = np.sin(2 * np.pi * f * 3.5 * tt) * 1.8 * np.exp(-tt / 0.25)
        y = np.sin(2 * np.pi * f * tt + mod) * np.exp(-tt / 1.0) + 0.3 * np.sin(4 * np.pi * f * tt) * np.exp(-tt / 0.3)
        a = int(0.002 * SR)
        y[:a] *= np.linspace(0, 1, a)
        add(out, y * vel, int(t * SR))
    return out


# ---------------------------------------------------------------- drums and fx

def _metal(n, rng):
    t = np.arange(n) / SR
    fs = np.array([205.3, 304.4, 369.6, 522.7, 540.0, 800.0]) * 1.9
    return sum(np.sign(np.sin(2 * np.pi * f * t + rng.random() * 6.28)) for f in fs) / 6


def drum_kit(seed):
    """Returns {name: [variants]} of synthesized one-shots."""
    rng = np.random.default_rng(seed)
    kit = {}

    def dec(n, tau):
        return np.exp(-np.arange(n) / SR / tau)

    def norm(x):
        return x / np.max(np.abs(x))

    for name in ('kick', 'snare', 'tom1', 'tom2', 'tom3', 'hat', 'hato', 'ride', 'crash', 'china'):
        kit[name] = []
    for _ in range(4):
        n = int(0.22 * SR)
        t = np.arange(n) / SR
        f = 55 + 130 * np.exp(-t / 0.015)
        body = np.sin(2 * np.pi * np.cumsum(f) / SR) * dec(n, 0.055)
        click = bp(rng.uniform(-1, 1, n), 2000, 7000) * dec(n, 0.005)
        kit['kick'].append(norm(hp(np.tanh(2.0 * (body + 1.1 * click)), 40)))

        n = int(0.35 * SR)
        t = np.arange(n) / SR
        tone = (0.7 * np.sin(2 * np.pi * 185 * t) + 0.4 * np.sin(2 * np.pi * 330 * t)) * dec(n, 0.07)
        nz = bp(rng.uniform(-1, 1, n), 1200, 9000) * dec(n, 0.14)
        crack = hp(rng.uniform(-1, 1, n), 3500) * dec(n, 0.012)
        kit['snare'].append(norm(np.tanh(1.6 * (0.8 * tone + 1.6 * nz + 0.8 * crack))))

        for nm, f0 in (('tom1', 210), ('tom2', 150), ('tom3', 100)):
            n = int(0.5 * SR)
            t = np.arange(n) / SR
            f = f0 * (1 + 0.5 * np.exp(-t / 0.03))
            body = np.sin(2 * np.pi * np.cumsum(f) / SR) * dec(n, 0.22)
            nz = bp(rng.uniform(-1, 1, n), 800, 5000) * dec(n, 0.03) * 0.5
            kit[nm].append(norm(np.tanh(1.5 * (body + nz))))

        n = int(0.12 * SR)
        kit['hat'].append(norm((hp(_metal(n, rng), 7000) * 0.7 + hp(rng.uniform(-1, 1, n), 8000) * 0.5) * dec(n, 0.035)))
        n = int(0.6 * SR)
        kit['hato'].append(norm((hp(_metal(n, rng), 7000) * 0.7 + hp(rng.uniform(-1, 1, n), 8000) * 0.5) * dec(n, 0.3)))

        n = int(2.0 * SR)
        t = np.arange(n) / SR
        ping = (np.sin(2 * np.pi * 2450 * t) + 0.6 * np.sin(2 * np.pi * 3720 * t)) * dec(n, 0.35)
        ride = hp(_metal(n, rng), 3000) * dec(n, 0.9) * 0.6 + 0.25 * ping + hp(rng.uniform(-1, 1, n), 5000) * dec(n, 0.8) * 0.4
        kit['ride'].append(norm(ride))

        n = int(3.0 * SR)
        crash = (hp(rng.uniform(-1, 1, n), 3000) * 0.8 + hp(_metal(n, rng), 4000) * 0.5) * dec(n, 1.3)
        kit['crash'].append(norm(lp(crash, 12000)))
        n = int(1.5 * SR)
        china = np.tanh(2.5 * (bp(rng.uniform(-1, 1, n), 2000, 9000) + 0.6 * _metal(n, rng))) * dec(n, 0.6)
        kit['china'].append(norm(hp(china, 1500)))
    kit['crash2'] = kit['crash'][::-1]
    return kit


DRUM_GAIN = {'kick': 1.0, 'snare': 0.95, 'hat': 0.28, 'hato': 0.3, 'ride': 0.3, 'crash': 0.45,
             'crash2': 0.45, 'china': 0.4, 'tom1': 0.85, 'tom2': 0.85, 'tom3': 0.9}
DRUM_PAN = {'kick': 0.0, 'snare': 0.0, 'hat': 0.35, 'hato': 0.35, 'ride': -0.35, 'crash': -0.55,
            'crash2': 0.55, 'china': 0.4, 'tom1': 0.35, 'tom2': 0.0, 'tom3': -0.4}


def render_drums(hits, total, seed):
    """hits: (t, name, vel). Returns (kick_bus, kit_bus) stereo arrays."""
    rng = np.random.default_rng(seed)
    kit = drum_kit(seed)
    kick = np.zeros((2, total))
    rest = np.zeros((2, total))
    for t, name, vel in hits:
        smp = kit[name][rng.integers(len(kit[name]))]
        v = vel * DRUM_GAIN[name] * (1 + rng.normal(0, 0.05))
        i = int((t + rng.normal(0, 0.0015)) * SR)
        add(kick if name == 'kick' else rest, pan(smp * v, DRUM_PAN[name]), i)
    return kick, rest, kit


def render_fx(events, total, kit, seed):
    """events: (kind, t, dur, vel) with kind riser / revcrash / boom."""
    rng = np.random.default_rng(seed)
    out = np.zeros((2, total))
    for kind, t, dur, vel in events:
        if kind == 'riser':
            n = int(dur * SR)
            K = max(1, n // 2205)
            for ch in range(2):
                nz = rng.standard_normal(n)
                y = np.zeros(n)
                for k in range(K):
                    a, b = k * n // K, (k + 1) * n // K
                    fc = 300 * 30 ** (k / K)
                    y[a:b] = bp(nz[a:b], fc * 0.7, min(fc * 1.4, 18000))
                y *= np.linspace(0, 1, n) ** 2
                add(out[ch], y * vel, int(t * SR))
        elif kind == 'revcrash':
            c = kit['crash'][0][:int(1.6 * SR)][::-1].copy()
            c *= np.linspace(0, 1, len(c)) ** 1.5
            add(out, np.stack([c, c]) * vel, int(t * SR) - len(c))
        elif kind == 'boom':
            n = int(1.8 * SR)
            tt = np.arange(n) / SR
            f = 32 + 60 * np.exp(-tt / 0.15)
            y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.6)
            y += lp(rng.standard_normal(n), 400) * np.exp(-tt / 0.25) * 0.3
            add(out, np.stack([y, y]) * vel, int(t * SR))
    return out


# ---------------------------------------------------------------- effects and mastering

def make_ir(t60, seed, lp_f=6000, predelay=0.015):
    rng = np.random.default_rng(seed)
    L = int(min(t60 * 1.1, 3.0) * SR)
    t = np.arange(L) / SR
    ir = rng.standard_normal((2, L)) * np.exp(-6.91 * t / t60)
    ir = lp(ir, lp_f)
    ir = np.concatenate([np.zeros((2, int(predelay * SR))), ir], axis=1)
    return ir / np.sqrt((ir ** 2).sum(axis=1, keepdims=True))


def reverb(x, ir):
    if x.ndim == 1:
        x = np.stack([x, x])
    return np.stack([signal.oaconvolve(x[c], ir[c])[:x.shape[1]] for c in range(2)])


def delay(x, dt, fb=0.32, taps=5):
    """Ping-pong delay of a mono signal; each repeat gets darker."""
    d = int(dt * SR)
    out = np.zeros((2, len(x)))
    tap = x
    for k in range(1, taps + 1):
        if k * d >= len(x):
            break
        tap = lp(tap, 3500)
        out[k % 2, k * d:] += fb ** k * tap[:len(x) - k * d]
    return out


def active_rms(x):
    m = np.max(np.abs(x), axis=0) if x.ndim == 2 else np.abs(x)
    e = uniform_filter1d(m ** 2, 4410)
    act = e > e.max() * 1e-3
    if not act.any():
        return 1.0
    sq = (x ** 2).sum(axis=0) / x.shape[0] if x.ndim == 2 else x ** 2
    return float(np.sqrt(sq[act].mean())) + 1e-12


def compress(x, thresh_db=-16, ratio=2.5, attack=0.008, release=0.15):
    m = np.max(np.abs(x), axis=0)
    a = np.exp(-1 / (release * SR))
    env = signal.lfilter([1 - a], [1, -a], maximum_filter1d(m, int(attack * SR) * 2 + 1))
    lvl = 20 * np.log10(env + 1e-9)
    gr = np.minimum(0, (thresh_db - lvl) * (1 - 1 / ratio))
    return x * 10 ** (gr / 20)


def limit(x, ceiling=0.89, look=0.003, release=0.06):
    """Look-ahead peak limiter: attack via min/average windows, release via one-pole."""
    peak = np.max(np.abs(x), axis=0)
    att = 1 - np.minimum(1.0, ceiling / np.maximum(peak, 1e-9))
    w = int(look * SR) * 2 + 1
    att = uniform_filter1d(maximum_filter1d(att, w), w)
    a = np.exp(-1 / (release * SR))
    att = np.maximum(att, signal.lfilter([1 - a], [1, -a], att))
    return np.clip(x * (1 - att), -ceiling, ceiling)
