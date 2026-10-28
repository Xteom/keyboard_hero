"""Arrangement layer: turns section descriptions into note/hit events, then mixes them.

Pitches are written as scale degrees of the song's minor key (0 = tonic, 7 = octave up).
Bars over a 'V' chord automatically use harmonic minor (raised 7th) for the neoclassical
sound. Melody strings use tokens like `7b~/4`: degree 7, bend up, vibrato, four 16ths.
Flags: b bend (whole step), h half-step bend, ~ vibrato, ^ legato, d dive, p pinch
harmonic, # raise a semitone. `r/8` is a rest.
"""
import re

import numpy as np
from scipy.io import wavfile

import engine as E

MINOR = [0, 2, 3, 5, 7, 8, 10]
HARM = [0, 2, 3, 5, 7, 8, 11]
CHORDS = {'i': 0, 'ii': 1, 'III': 2, 'iv': 3, 'v': 4, 'V': 4, 'VI': 5, 'VII': 6}
TOK = re.compile(r'^(r|-?\d+)([#bh~^dp]*)/([\d.]+)$')
VOICES = ('rhythm', 'bass', 'drums', 'lead', 'lead2', 'synth', 'synth2', 'pad', 'bell', 'fx')


def scale_of(ch):
    return HARM if ch == 'V' else MINOR


def dsemi(deg, scale=MINOR):
    o, d = divmod(deg, 7)
    return 12 * o + scale[d]


def segments(spec, bars):
    """'style' or [('style', n), ...] -> [(offset, style, n)]."""
    if spec is None:
        return []
    if isinstance(spec, str):
        return [(0, spec, bars)]
    out, off = [], 0
    for style, n in spec:
        out.append((off, style, n))
        off += n
    return out


class Song:
    def __init__(self, title, bpm, tonic, rroot, seed):
        self.title, self.bpm, self.spb = title, bpm, 60.0 / bpm
        self.tonic, self.rroot = tonic, rroot
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.ev = {k: [] for k in VOICES}
        self.sections = []
        self.bars = 0

    def sec(self, bar, pos16=0.0):
        return (bar * 4 + pos16 / 4.0) * self.spb

    def length(self):
        return self.sec(self.bars)

    def croot(self, ch):
        """Low power-chord root for a chord, folded down when the lower octave is playable."""
        r = self.rroot + MINOR[CHORDS[ch]]
        return r - 12 if r - 12 >= self.rroot - 3 else r

    def lead_midi(self, deg, ch, tr=0):
        return self.tonic + dsemi(deg, scale_of(ch)) + tr

    def note(self, voice, bar, pos16, len16, midi, **fl):
        self.ev[voice].append((self.sec(bar, pos16), len16 * self.spb / 4, midi, fl))

    # ------------------------------------------------------------ section builder

    def section(self, name, bars, chords, rhythm=None, riff=None, drums=None, bass=None, fill=8,
                crash=True, pad=0.0, bells=0.0, arp=None, arp_vel=0.6, lead=None, harm=None,
                lead_vel=1.0, synth=None, synth_oct=7, synth_vel=0.8, synth_harm=None, solo=None,
                fx=(), tr=0):
        b0 = self.bars
        ch = [chords[i % len(chords)] for i in range(bars)]
        if riff:
            self.riff(b0, riff, bars, tr)
        for off, style, n in segments(rhythm, bars):
            self.rhythm(b0 + off, ch[off:off + n], style, tr)
        for off, style, n in segments(bass, bars):
            self.bass(b0 + off, ch[off:off + n], style, tr)
        for off, style, n in segments(drums, bars):
            self.drums(b0 + off, n, style, fill, crash)
        if pad:
            self.pad(b0, ch, tr, pad)
        if bells:
            self.bells(b0, ch, tr, bells)
        for off, style, n in segments(arp, bars):
            self.arp(b0 + off, ch[off:off + n], style, tr, arp_vel)
        if lead:
            self.melody(b0, lead, ch, 'lead', 0, harm, 'lead2', tr, lead_vel)
        if synth:
            self.melody(b0, synth, ch, 'synth', synth_oct, synth_harm, 'synth2', tr, synth_vel)
        if solo:
            for i, kind in enumerate(solo):
                if kind:
                    self.solo_bar(b0 + i, ch[i], kind, tr)
        for spec in fx:
            kind, at = spec[0], spec[1]
            if kind == 'riser':
                self.ev['fx'].append(('riser', self.sec(b0 + at), spec[2] * 4 * self.spb, 0.5))
            else:
                self.ev['fx'].append((kind, self.sec(b0 + at), 0, 0.8 if kind == 'boom' else 0.6))
        self.sections.append((name, b0, bars, tr))
        self.bars += bars

    # ------------------------------------------------------------ guitars and bass

    def rhythm(self, b0, chords, style, tr=0, vel=0.9):
        ev = self.ev['rhythm']
        if style in (None, 'none'):
            return
        if style == 'ring':
            r = self.croot(chords[0]) + tr
            ev.append((self.sec(b0), len(chords) * 4 * self.spb, [r, r + 7, r + 12], False, vel))
            return
        for i, ch in enumerate(chords):
            bar = b0 + i
            r = self.croot(ch) + tr
            full, mute = [r, r + 7, r + 12], [r, r + 7]

            def hit(pos, ln, muted, v=vel):
                ev.append((self.sec(bar, pos), ln * self.spb / 4, mute if muted else full, muted, v))

            if style == 'trem_mute':
                hit(0, 1, False, vel * 1.05)
                for p in range(1, 16):
                    hit(p, 1, True)
            elif style == 'trem_open':
                for p in range(16):
                    hit(p, 1, False, vel * (1.0 if p % 4 == 0 else 0.85))
            elif style == 'gallop':
                for b in range(4):
                    hit(4 * b, 2, b != 0, vel * 1.05)
                    hit(4 * b + 2, 1, True)
                    hit(4 * b + 3, 1, True)
            elif style == 'chords8':
                for p in range(0, 16, 2):
                    hit(p, 2, False, vel * (1.05 if p % 4 == 0 else 0.9))
            elif style == 'sustain':
                hit(0, 16, False)
            elif style == 'half':
                hit(0, 8, False)
                hit(8, 8, False)

    def riff(self, b0, text, bars, tr=0, vel=0.9):
        toks = text.split()
        n = len(toks)
        for i in range(bars * 16):
            tok = toks[i % n]
            if tok in ('r', '-'):
                continue
            ln, j = 1, i + 1
            while j < bars * 16 and toks[j % n] == '-':
                ln, j = ln + 1, j + 1
            muted = tok.endswith('m')
            r = self.rroot + dsemi(int(tok.rstrip('m'))) + tr
            bar, pos = divmod(i, 16)
            t, d = self.sec(b0 + bar, pos), ln * self.spb / 4
            self.ev['rhythm'].append((t, d, [r, r + 7] if muted else [r, r + 7, r + 12], muted, vel))
            self.ev['bass'].append((t, d, r - 12, muted, vel))

    def bass(self, b0, chords, style, tr=0, vel=0.9):
        if style in (None, 'none'):
            return
        ev = self.ev['bass']
        if style == 'ring':
            ev.append((self.sec(b0), len(chords) * 4 * self.spb, self.croot(chords[0]) + tr - 12, False, vel))
            return
        pats = {'8ths': [(p, 2, True) for p in range(0, 16, 2)],
                '16ths': [(p, 1, True) for p in range(16)],
                'whole': [(0, 16, False)],
                'half': [(0, 8, False), (8, 8, False)],
                'gallop': [(4 * b + o, l, True) for b in range(4) for o, l in ((0, 2), (2, 1), (3, 1))]}
        for i, ch in enumerate(chords):
            r = self.croot(ch) + tr - 12
            for pos, ln, muted in pats[style]:
                ev.append((self.sec(b0 + i, pos), ln * self.spb / 4, r, muted, vel))

    # ------------------------------------------------------------ drums

    def drums(self, b0, nbars, style, fill=8, crash=True, vel=1.0):
        if style in (None, 'none'):
            return

        def h(bar, p, name, v=1.0):
            self.ev['drums'].append((self.sec(bar, p), name, v * vel))

        if style == 'end':
            for name in ('crash', 'crash2', 'kick', 'china'):
                h(b0, 0, name)
            return
        for i in range(nbars):
            bar = b0 + i
            last = bool(fill) and (i + 1) % fill == 0 and style not in ('light', 'build')
            end = 8 if last else 16
            if style == 'double':
                for p in range(end):
                    h(bar, p, 'kick', 0.8 + (0.15 if p % 4 == 0 else 0))
                for p in (4, 12):
                    if p < end:
                        h(bar, p, 'snare')
                for p in range(0, end, 2):
                    h(bar, p, 'ride', 0.8 if p % 4 == 0 else 0.55)
            elif style == 'blast':
                for p in range(end):
                    h(bar, p, 'kick', 0.85)
                for p in range(2, end, 4):
                    h(bar, p, 'snare', 0.95)
                for p in range(4, end, 4):
                    h(bar, p, 'crash' if (p // 4) % 2 == 0 else 'crash2', 0.5)
            elif style == 'skank':
                for p in range(0, end, 4):
                    h(bar, p, 'kick')
                for p in range(2, end, 4):
                    h(bar, p, 'snare', 0.9)
                for p in range(0, end, 2):
                    h(bar, p, 'hat', 0.7)
            elif style == 'gallop':
                for p in range(end):
                    if p % 4 in (0, 2, 3):
                        h(bar, p, 'kick', 0.85)
                for p in (4, 12):
                    if p < end:
                        h(bar, p, 'snare')
                for p in range(4, end, 4):
                    h(bar, p, 'china', 0.6)
            elif style == 'halftime':
                for p in range(end):
                    h(bar, p, 'kick', 0.7)
                if 8 < end:
                    h(bar, 8, 'snare')
                for p in range(0, end, 2):
                    h(bar, p, 'ride', 0.6)
            elif style == 'light':
                for p in range(0, 16, 2):
                    h(bar, p, 'ride', 0.35 + (0.1 if p % 4 == 0 else 0))
                h(bar, 0, 'kick', 0.55)
                h(bar, 10, 'kick', 0.45)
                h(bar, 12, 'snare', 0.25)
            elif style == 'build':
                for p in range(0, 16, 4):
                    h(bar, p, 'kick', 0.7)
                for p in range(0, 8, 2):
                    h(bar, p, 'snare', 0.35 + 0.04 * p)
                for p in range(8, 16):
                    h(bar, p, 'snare', 0.55 + 0.04 * (p - 8))
            if crash and style not in ('light', 'build') and (i == 0 or (fill and i % fill == 0)):
                h(bar, 0, 'crash', 0.9)
                if style in ('skank', 'halftime'):
                    h(bar, 0, 'china', 0.5)
            if last:
                self.fill(bar, six=style in ('blast', 'double'))

    def fill(self, bar, six=False):
        def h(p, name, v):
            self.ev['drums'].append((self.sec(bar, p), name, v))

        if six:
            seq = ['snare'] * 3 + ['tom1'] * 3 + ['tom2'] * 3 + ['tom3'] * 3
            for k, name in enumerate(seq):
                h(8 + k * 2 / 3, name, 0.75 + 0.02 * k)
        else:
            for k, name in enumerate(['snare', 'snare', 'tom1', 'tom1', 'tom2', 'tom2', 'tom3', 'tom3']):
                h(8 + k, name, 0.8)
        for p in range(8, 16, 2):
            h(p, 'kick', 0.8)

    # ------------------------------------------------------------ keys and pads

    def pad(self, b0, chords, tr=0, vel=0.5):
        for i, ch in enumerate(chords):
            sc, r = scale_of(ch), CHORDS[ch]
            notes = [self.tonic - 12 + dsemi(d, sc) + tr for d in (r, r + 2, r + 4)]
            notes = [n - 12 if n > self.tonic + 4 + tr else n for n in notes]
            self.ev['pad'].append((self.sec(b0 + i), 4 * self.spb, notes, vel))

    def bells(self, b0, chords, tr=0, vel=0.5):
        for i, ch in enumerate(chords):
            sc, r = scale_of(ch), CHORDS[ch]
            tones = [r, r + 2, r + 4, r + 7, r + 4, r + 2, r + 4, r + 7]
            for k, d in enumerate(tones):
                self.ev['bell'].append((self.sec(b0 + i, 2 * k), 1.5 * self.spb, self.tonic + dsemi(d, sc) + tr, vel))

    def arp(self, b0, chords, kind, tr=0, vel=0.6, voice='synth'):
        for i, ch in enumerate(chords):
            r = CHORDS[ch]
            if kind == '16':
                degs, step = [r, r + 2, r + 4, r + 7, r + 9, r + 7, r + 4, r + 2] * 2, 1.0
            elif kind == '6':
                degs, step = [r, r + 2, r + 4, r + 7, r + 4, r + 2] * 4, 2 / 3
            else:  # '16up'
                degs, step = [r, r + 2, r + 4, r + 7] * 4, 1.0
            for k, d in enumerate(degs):
                self.note(voice, b0 + i, k * step, step, self.lead_midi(d + 7, ch, tr), vel=vel)

    # ------------------------------------------------------------ melodies

    def melody(self, b0, text, chords, voice, oct=0, harm=None, harm_voice='lead2', tr=0, vel=1.0):
        pos = 0.0
        for tok in text.split():
            mt = TOK.match(tok)
            if not mt:
                raise ValueError(f'bad melody token {tok!r}')
            d, fl, ln = mt.group(1), mt.group(2), float(mt.group(3))
            if d != 'r':
                ch = chords[int(pos // 16) % len(chords)]
                sc = scale_of(ch)
                deg = int(d) + oct
                flags = {'vel': vel}
                if '~' in fl:
                    flags['vib'] = True
                if 'b' in fl:
                    flags['bend'] = 2
                if 'h' in fl:
                    flags['bend'] = 1
                if '^' in fl:
                    flags['legato'] = True
                if 'd' in fl:
                    flags['dive'] = 12
                if 'p' in fl:
                    flags['pinch'] = True
                acc = 1 if '#' in fl else 0
                dur = ln * self.spb / 4 * (1.0 if ln <= 1 or '^' in fl else 0.92)
                t = self.sec(b0, pos)
                self.ev[voice].append((t, dur, self.tonic + dsemi(deg, sc) + acc + tr, flags))
                if harm is not None:
                    self.ev[harm_voice].append((t, dur, self.tonic + dsemi(deg + harm, sc) + acc + tr, dict(flags)))
            pos += ln

    # ------------------------------------------------------------ solo vocabulary

    def solo_bar(self, bar, ch, kind, tr=0):
        """One bar of generated shred. Guitar kinds go to 'lead'; k* kinds go to 'synth'."""
        r = CHORDS[ch]
        hi = r + 7 if r < 4 else r
        voice = 'synth' if kind.startswith('k') else 'lead'
        kind = kind[1:] if kind.startswith('k') else kind

        def put(degs, step, legato_every=0, start=0.0, vel=0.95):
            for k, d in enumerate(degs):
                leg = legato_every and k % legato_every != 0
                self.note(voice, bar, start + k * step, step, self.lead_midi(d, ch, tr), legato=bool(leg), vel=vel)

        if kind == 'seq_up':
            put([hi - 3 + g + j for g in range(4) for j in range(4)], 1)
        elif kind == 'seq_down':
            put([hi + 6 - g - j for g in range(4) for j in range(4)], 1)
        elif kind == 'six_down':
            put([hi + 7 - g - j for g in range(8) for j in range(3)], 2 / 3, legato_every=3)
        elif kind == 'six_up':
            put([hi - 5 + g + j for g in range(8) for j in range(3)], 2 / 3, legato_every=3)
        elif kind == 'pedal':
            mel = [hi + 6, hi + 5, hi + 4, hi + 3, hi + 4, hi + 5, hi + 6, hi + 4]
            put([x for m in mel for x in (hi + 7, m)], 1)
        elif kind == 'run_bend':
            put([hi - 4 + k for k in range(12)], 2 / 3, legato_every=3)
            self.note(voice, bar, 8, 8, self.lead_midi(hi + 9, ch, tr), bend=2, vib=True, vel=1.0)
        elif kind == 'sweep':
            base = r if r < 2 else r - 7
            upd = [base, base + 2, base + 4, base + 7, base + 9, base + 11, base + 14]
            put((upd + upd[-2:0:-1]) * 2, 2 / 3, legato_every=6)
        elif kind == 'tap':
            base = (r if r < 4 else r - 7) + 7
            degs = []
            for top in (base + 7, base + 9, base + 11, base + 9):
                degs += [top, base + 2, base + 4] * 2
            put(degs, 2 / 3, legato_every=3)
        elif kind == 'trill':
            put([hi + 4, hi + 5] * 9, 2 / 3, legato_every=2)
            self.note(voice, bar, 12, 4, self.lead_midi(hi + 4, ch, tr), dive=12, vel=1.0)
        elif kind in ('16', '6', '16up'):
            self.arp(bar, [ch], kind, tr, 0.8, voice)
        elif kind == 'run':
            put([hi - 5 + k for k in range(12)] + [hi + 7 - k for k in range(12)], 2 / 3)
        else:
            raise ValueError(kind)


# ---------------------------------------------------------------- mixdown

def db(x):
    return 10 ** (x / 20)


# Stem levels in dB after each stem is normalised to its own active RMS.
LEVELS = {'guitars': -5.0, 'bass': -8.0, 'drums': -5.5, 'lead': -4.5, 'lead2': -8.0, 'synth': -7.0,
          'synth2': -10.5, 'pad': -19.0, 'bell': -19.0, 'fx': -17.0}


def render_stems(song):
    """Render every instrument to a stereo stem, already level-balanced."""
    total = int((song.length() + 4.0) * E.SR)
    seed = song.seed
    ev = song.ev
    n = E.active_rms
    hall = E.make_ir(2.2, seed + 7)
    room = E.make_ir(0.7, seed + 8, lp_f=8000, predelay=0.005)
    st = {}

    gl = E.amp(E.render_rhythm(ev['rhythm'], total, seed + 1))
    gr = E.amp(E.render_rhythm(ev['rhythm'], total, seed + 2))
    gl, gr = gl / n(gl), gr / n(gr)
    st['guitars'] = np.stack([gl + 0.12 * gr, gr + 0.12 * gl])
    if ev['bass']:
        b = E.render_bass(ev['bass'], total, seed + 3)
        st['bass'] = np.stack([b, b]) / n(b)
    kick, kit, kitdata = E.render_drums(ev['drums'], total, seed + 4)
    st['drums'] = (kick + kit + 0.25 * E.reverb(kit.mean(axis=0), room)) / n(kick + kit)
    for voice, p in (('lead', -0.08), ('lead2', 0.25)):
        if ev[voice]:
            x = E.render_lead_guitar(ev[voice], total, seed + 10 + len(voice))
            x /= n(x)
            st[voice] = E.pan(x, p) + E.delay(x, 0.75 * song.spb) * db(-14) + E.reverb(x, hall) * db(-17)
    for voice, p in (('synth', 0.15), ('synth2', -0.3)):
        if ev[voice]:
            x = E.render_synth(ev[voice], total, seed + 20 + len(voice))
            x /= n(x)
            st[voice] = E.pan(x, p) + E.delay(x, 0.75 * song.spb, fb=0.28) * db(-12) + E.reverb(x, hall) * db(-15)
    if ev['pad']:
        x = E.render_pad(ev['pad'], total, seed + 30)
        x /= n(x)
        st['pad'] = x + E.reverb(x.mean(axis=0), hall) * db(-6)
    if ev['bell']:
        x = E.render_bells(ev['bell'], total)
        x /= n(x)
        st['bell'] = np.stack([x, x]) * 0.8 + E.reverb(x, hall) * db(-3)
    if ev['fx']:
        x = E.render_fx(ev['fx'], total, kitdata, seed + 40)
        st['fx'] = x / n(x)
    for k in st:
        st[k] *= db(LEVELS[k])
    return st


BANDS = [(20, 60), (60, 120), (120, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000), (8000, 16000)]


def stem_report(stems, t0, t1):
    """Per-stem RMS and per-octave band energy (dB re. the full mix) over [t0, t1)."""
    a, b = int(t0 * E.SR), int(t1 * E.SR)
    mix = sum(stems.values())[:, a:b].mean(axis=0)
    w = np.hanning(b - a)
    fr = np.fft.rfftfreq(b - a, 1 / E.SR)
    ref = (np.abs(np.fft.rfft(mix * w)) ** 2).sum()

    def prof(x):
        X = np.abs(np.fft.rfft(x * w)) ** 2
        return [10 * np.log10(X[(fr >= lo) & (fr < hi)].sum() / ref / np.log2(hi / lo) + 1e-12) for lo, hi in BANDS]

    print(f'{"stem":8s} {"rms":>6s} ' + ' '.join(f'{lo:>6d}' for lo, _ in BANDS))
    for k, x in list(stems.items()) + [('MIX', None)]:
        y = mix if x is None else x[:, a:b].mean(axis=0)
        rms = 20 * np.log10(np.sqrt(np.mean(y ** 2)) + 1e-12)
        print(f'{k:8s} {rms:6.1f} ' + ' '.join(f'{v:6.1f}' for v in prof(y)))


def master(stems, wav_path):
    mix = sum(stems.values())
    mix = E.hp(mix, 30, 4)
    mix = E.peq(mix, 90, 2, 0.7)
    mix = E.peq(mix, 700, -3, 0.7)
    mix = E.peq(mix, 11000, 2, 0.7)
    mix = E.compress(mix, thresh_db=20 * np.log10(np.max(np.abs(mix)) + 1e-9) - 8, ratio=1.6)
    mix *= db(-12.0) / E.active_rms(mix)
    mix = E.limit(mix, ceiling=db(-1.5))
    fade = int(3.0 * E.SR)
    mix[:, -fade:] *= np.linspace(1, 0, fade) ** 2
    wavfile.write(wav_path, E.SR, (mix.T * 32767).astype(np.int16))
    return mix


def render(song, wav_path):
    return master(render_stems(song), wav_path)
