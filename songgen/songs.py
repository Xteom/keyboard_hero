"""Three original extreme-power-metal instrumentals for keyboard_hero.

Usage: .venv/bin/python songs.py [1|2|3|all] [--out DIR]
Renders WAV to a temp dir, encodes MP3 into DIR (default ../songs) and prints a section map.
"""
import argparse
import os
import subprocess
import tempfile

from compose import Song, render

# ======================================================================= 1. Skyforge Inferno
# E minor, 200 BPM. Calm bell intro -> twin-lead theme -> verses/choruses -> calm breakdown
# -> 40-bar solo (melodic, shred runs, keyboard solo, sweeps/tapping, twin lead) -> key change.

SKY_INTRO_CH = ['i', 'VI', 'VII', 'i', 'i', 'VI', 'VII', 'V']
SKY_INTRO = ('7/4 6/2 7/2 4/4 2/4  5/4 4/2 5/2 2/4 0/4  6/4 5/2 6/2 3/4 1/4  4/6 2/2 4~/8 '
             '7/4 6/2 7/2 9/4 7/4  9/4 7/2 9/2 5/4 7/4  10/4 9/2 8/2 6/4 8/4  8/2 6/2 4/2 6/2 8~/8')
SKY_RIFF = ('0m 0m 4 0m 0m 5 0m 0m 6 0m 0m 5 0m 4 0m 2 '
            '0m 0m 4 0m 0m 5 0m 0m 6 0m 0m 7 6 5 4 2')
SKY_VERSE_CH = ['i', 'i', 'VI', 'VII', 'i', 'i', 'VI', 'V']
SKY_VERSE = ('r/2 0/2 0/2 2/2 4/4 2/4  3/4 2/4 0/8  r/2 0/2 0/2 2/2 4/4 5/4  6/4 5/4 4/8 '
             'r/2 4/2 4/2 5/2 7/4 5/4  4/4 2/4 4/8  r/2 2/2 2/2 4/2 5/4 4/4  3/4 6/4 4/8')
SKY_PRE_CH = ['VI', 'VII', 'VI', 'VII']
SKY_PRE = '7/8 9/8  8/8 10/8  9/8 11/8  10~/16'
SKY_CHORUS_CH = ['VI', 'VII', 'III', 'i', 'VI', 'VII', 'III', 'III']
SKY_CHORUS = ('7/4 7/2 9/2 7/4 5/4  6/4 6/2 8/2 10/8  9/6 8/2 9/4 11/4  11/4 9/4 7~/8 '
              '7/4 7/2 9/2 12/4 11/4  10/4 10/2 11/2 13/8  14/6 13/2 11/4 9/4  11~/16')
SKY_SOLO_CH = ['i', 'VI', 'VII', 'V']
SKY_SOLO1 = ('7b/4 7/2 9/2 11~/8  12/4 11/2 9/2 7/4 9/4  10b/4 10/2 11/2 13~/8  12/2 11/2 10/2 9/2 8/2 9/2 11/4 '
             '14b~/8 13/2 11/2 9/4  12/4 11/4 9/2 12/2 14/4  13/4 12/4 10/4 8/4  11p/16')
SKY_BREAK = 'r/64 7/8 4/8  5/8 2/8  6/8 3/8  4~/16'


def skyforge_inferno():
    s = Song('Skyforge Inferno', bpm=200, tonic=64, rroot=40, seed=101)
    pre = dict(rhythm='half', drums=[('halftime', 3), ('build', 1)], bass='half', pad=0.4,
               lead=SKY_PRE, harm=-2, fx=[('riser', 2, 2)])
    chorus = dict(rhythm='chords8', drums='blast', bass='8ths', pad=0.5, lead=SKY_CHORUS, harm=-2,
                  fx=[('boom', 0)])
    theme = dict(rhythm='chords8', drums='double', bass='8ths', pad=0.3, lead=SKY_INTRO, harm=2)
    riff = dict(riff=SKY_RIFF, drums='gallop', fill=4)

    s.section('intro (calm)', 8, ['i', 'i', 'VI', 'VI', 'VII', 'VII', 'V', 'V'], bells=0.55, pad=0.35,
              drums=[('none', 6), ('build', 2)], bass=[('none', 7), ('whole', 1)],
              fx=[('riser', 4, 4), ('revcrash', 8)])
    s.section('twin-lead theme', 8, SKY_INTRO_CH, fx=[('boom', 0)], **theme)
    s.section('riff', 4, ['i'], **riff)
    s.section('verse 1', 16, SKY_VERSE_CH, rhythm=[('trem_mute', 8), ('gallop', 8)],
              drums=[('skank', 8), ('double', 8)], bass='8ths', synth=SKY_VERSE + ' ' + SKY_VERSE)
    s.section('pre-chorus', 4, SKY_PRE_CH, **pre)
    s.section('chorus', 8, SKY_CHORUS_CH, **chorus)
    s.section('theme', 8, SKY_INTRO_CH, **theme)
    s.section('riff', 4, ['i'], **riff)
    s.section('verse 2', 8, SKY_VERSE_CH, rhythm='gallop', drums='double', bass='8ths', synth=SKY_VERSE)
    s.section('pre-chorus', 4, SKY_PRE_CH, **pre)
    s.section('chorus', 8, SKY_CHORUS_CH, **chorus)
    s.section('breakdown (calm)', 8, SKY_SOLO_CH, bells=0.5, pad=0.4, drums=[('none', 4), ('light', 3), ('build', 1)],
              bass=[('none', 7), ('whole', 1)], synth=SKY_BREAK, synth_oct=0, synth_vel=0.5,
              fx=[('riser', 6, 2), ('revcrash', 8)])
    s.section('solo: melodic', 8, SKY_SOLO_CH, rhythm='gallop', drums='double', bass='gallop', pad=0.25,
              lead=SKY_SOLO1, fx=[('boom', 0)])
    s.section('solo: shred runs', 8, SKY_SOLO_CH, rhythm='trem_mute', drums='skank', bass='8ths',
              solo=['seq_up', 'pedal', 'seq_down', 'six_down', 'pedal', 'seq_up', 'six_up', 'run_bend'])
    s.section('solo: keyboard', 8, SKY_SOLO_CH, rhythm='chords8', drums='blast', bass='8ths',
              solo=['k16', 'k16', 'k16', 'k16', 'k6', 'k6', 'k6', 'krun'])
    s.section('solo: sweeps + tapping', 8, SKY_SOLO_CH, rhythm='trem_open', drums='double', bass='16ths',
              solo=['sweep', 'sweep', 'sweep', 'sweep', 'tap', 'tap', 'trill', 'run_bend'])
    s.section('solo: twin lead', 8, SKY_INTRO_CH, rhythm='chords8', drums='blast', bass='8ths', pad=0.4,
              lead=SKY_INTRO, harm=2)
    s.section('pre-chorus', 4, SKY_PRE_CH, **pre)
    s.section('chorus', 8, SKY_CHORUS_CH, **chorus)
    s.section('chorus (key change +2)', 8, SKY_CHORUS_CH, tr=2, **chorus)
    s.section('outro theme', 8, SKY_INTRO_CH, tr=2, **theme)
    s.section('end', 2, ['i'], rhythm='ring', bass='ring', drums='end', pad=0.4, lead='7~/32', harm=2, tr=2,
              fx=[('boom', 0)])
    return s


# ======================================================================= 2. Starfall Overdrive
# F# minor, 184 BPM. Synth-arpeggio intro, synth doubles the guitar theme, guitar/keyboard
# trade-offs in the solo.

STAR_INTRO_CH = ['i', 'VII', 'VI', 'VII', 'i', 'VII', 'VI', 'V']
STAR_INTRO = ('7/3 7/3 7/2 9/2 11/2 9/2 7/2  6/3 6/3 6/2 8/2 10/2 8/2 6/2  5/3 5/3 5/2 7/2 9/2 7/2 5/2  6/4 8/4 10/4 13/4 '
              '14/3 13/3 11/2 9/2 11/2 13/2 14/2  13/3 11/3 10/2 8/2 10/2 11/2 13/2  '
              '12/3 11/3 9/2 7/2 9/2 11/2 12/2  11~/8 10/2 8/2 6/4')
STAR_RIFF = ('0m 0m 0 0m 0m 2 0m 0m 1 0m 0m 0 2 3 4 3 '
             '0m 0m 0 0m 0m 2 0m 0m 1 0m 0m 0 -1 -2 -1 0')
STAR_VERSE_CH = ['i', 'i', 'VII', 'VII', 'VI', 'VI', 'VII', 'V']
STAR_VERSE = ('0/2 0/2 2/2 4/4 2/2 0/4  1/2 0/2 1/2 2/8 r/2  -1/2 -1/2 1/2 3/4 1/2 -1/4  0/2 -1/2 0/2 1/8 r/2 '
              '-2/2 -2/2 0/2 2/4 0/2 -2/4  2/4 4/4 5/8  6/4 5/2 4/2 3/4 4/4  4~/8 6/4 4/4')
STAR_PRE_CH = ['VI', 'VII', 'VI', 'V']
STAR_PRE = '9/8 7/8  10/8 8/8  9/8 12/8  11~/16'
STAR_CHORUS_CH = ['III', 'VII', 'i', 'VI', 'III', 'VII', 'VI', 'V']
STAR_CHORUS = ('9/4 9/2 11/2 13/4 11/4  10/4 10/2 11/2 13/8  14/6 13/2 11/4 9/4  12/4 11/4 9/8 '
               '9/4 11/2 13/2 14/4 13/4  13/4 11/2 10/2 8/8  14/4 12/4 11/4 9/4  11~/16')
STAR_SOLO_CH = ['i', 'VII', 'VI', 'V']
STAR_SOLO1 = ('7b/4 9/4 11~/8  10/2 11/2 13/4 11/2 10/2 8/4  9b/4 9/2 7/2 5~/8  6/2 7/2 8/2 10/2 11~/8 '
              '14b~/8 11/4 9/4  13/4 11/4 10/4 8/4  12/2 11/2 9/2 7/2 9/2 11/2 12/4  11p/16')
STAR_BREAK = '9/8 7/8  10/8 8/8  7/8 4/8  4/16  9/8 7/8  10/8 8/8  9/8 12/8  11~/16'


def starfall_overdrive():
    s = Song('Starfall Overdrive', bpm=184, tonic=66, rroot=42, seed=202)
    pre = dict(rhythm='half', drums=[('halftime', 3), ('build', 1)], bass='half', pad=0.4,
               lead=STAR_PRE, harm=-2, fx=[('riser', 2, 2)])
    chorus = dict(rhythm='chords8', drums='blast', bass='8ths', pad=0.5, lead=STAR_CHORUS, harm=-2,
                  fx=[('boom', 0)])
    theme = dict(rhythm='chords8', drums='double', bass='8ths', pad=0.3, lead=STAR_INTRO, harm=2,
                 synth=STAR_INTRO, synth_oct=0, synth_vel=0.55)
    riff = dict(riff=STAR_RIFF, drums='gallop', fill=4)

    s.section('intro (calm synth arps)', 8, STAR_SOLO_CH, arp=[('16', 8)], arp_vel=0.35, pad=0.35,
              drums=[('none', 4), ('light', 3), ('build', 1)], bass=[('none', 7), ('whole', 1)],
              fx=[('riser', 6, 2), ('revcrash', 8)])
    s.section('theme (guitar + synth)', 8, STAR_INTRO_CH, fx=[('boom', 0)], **theme)
    s.section('riff', 4, ['i'], **riff)
    s.section('verse 1', 16, STAR_VERSE_CH, rhythm=[('trem_mute', 8), ('gallop', 8)],
              drums=[('skank', 8), ('double', 8)], bass='8ths', synth=STAR_VERSE + ' ' + STAR_VERSE)
    s.section('pre-chorus', 4, STAR_PRE_CH, **pre)
    s.section('chorus', 8, STAR_CHORUS_CH, **chorus)
    s.section('theme', 8, STAR_INTRO_CH, **theme)
    s.section('verse 2', 8, STAR_VERSE_CH, rhythm='gallop', drums='double', bass='8ths', synth=STAR_VERSE)
    s.section('pre-chorus', 4, STAR_PRE_CH, **pre)
    s.section('chorus', 8, STAR_CHORUS_CH, **chorus)
    s.section('breakdown (calm)', 8, ['VI', 'VII', 'i', 'i', 'VI', 'VII', 'VI', 'V'], bells=0.5, pad=0.4,
              drums=[('none', 4), ('light', 3), ('build', 1)], bass=[('none', 7), ('whole', 1)],
              synth=STAR_BREAK, synth_oct=0, synth_vel=0.45, fx=[('riser', 6, 2), ('revcrash', 8)])
    s.section('solo: melodic', 8, STAR_SOLO_CH, rhythm='gallop', drums='double', bass='gallop', pad=0.25,
              lead=STAR_SOLO1, fx=[('boom', 0)])
    s.section('solo: guitar vs keyboard', 8, STAR_SOLO_CH, rhythm='trem_mute', drums='skank', bass='8ths',
              solo=['seq_up', 'six_down', 'k16', 'k6', 'pedal', 'six_up', 'k6', 'krun'])
    s.section('solo: sweeps + tapping', 8, STAR_SOLO_CH, rhythm='trem_open', drums='blast', bass='16ths',
              solo=['sweep', 'sweep', 'sweep', 'sweep', 'tap', 'tap', 'trill', 'run_bend'])
    s.section('solo: twin lead', 8, STAR_INTRO_CH, rhythm='chords8', drums='double', bass='8ths', pad=0.4,
              lead=STAR_INTRO, harm=2, arp='16', arp_vel=0.3)
    s.section('chorus', 8, STAR_CHORUS_CH, **chorus)
    s.section('chorus (synth doubles)', 8, STAR_CHORUS_CH, synth=STAR_CHORUS, synth_oct=7, synth_vel=0.45, **chorus)
    s.section('outro riff', 4, ['i'], **riff)
    s.section('end', 2, ['i'], rhythm='ring', bass='ring', drums='end', pad=0.4, lead='7~/32', harm=2,
              fx=[('boom', 0)])
    return s


# ======================================================================= 3. Wyvern Reactor
# C# minor, 216 BPM. No calm intro (starts at full speed), calm interlude mid-song, 48-bar
# solo, final chorus modulates up a semitone.

WYV_INTRO_CH = ['i', 'VI', 'III', 'VII', 'i', 'VI', 'VII', 'V']
WYV_INTRO = ('7/2 8/2 9/2 11/2 9/2 8/2 7/2 4/2  5/2 7/2 9/2 12/2 9/2 7/2 5/2 2/2 '
             '9/2 11/2 13/2 16/2 13/2 11/2 9/2 6/2  6/2 8/2 10/2 13/2 12/2 10/2 8/2 6/2 '
             '14/4 11/4 9/2 11/2 14/4  12/4 9/4 7/2 9/2 12/4  13/4 10/4 8/2 10/2 13/4  11/2 13/2 15/2 13~/10')
WYV_RIFF = ('0m 0m 0m 0 0m 0m 0m 2 0m 0m 0m 3 0m 2 0m 0 '
            '0m 0m 0m 0 0m 0m 0m 5 0m 0m 0m 4 3 2 1 -1')
WYV_VERSE_CH = ['i', 'i', 'VI', 'VI', 'III', 'III', 'VII', 'V']
WYV_VERSE = ('0/2 2/2 4/4 4/2 3/2 2/4  3/4 2/4 0/8  0/2 2/2 5/4 5/2 4/2 2/4  4/4 2/4 5/8 '
             '2/2 4/2 6/4 6/2 5/2 4/4  5/4 4/4 2/8  1/2 3/2 6/4 5/2 4/2 3/4  4/4 6/4 4~/8')
WYV_PRE_CH = ['VI', 'VII', 'VI', 'VII']
WYV_PRE = '9/8 10/8  11/8 13/8  12/8 14/8  13~/16'
WYV_CHORUS_CH = ['VI', 'VII', 'i', 'i', 'VI', 'VII', 'III', 'V']
WYV_CHORUS = ('7/4 7/2 9/2 12/4 11/4  10/4 10/2 11/2 13/8  14/6 13/2 11/4 9/4  11/4 9/4 7~/8 '
              '12/4 12/2 11/2 12/4 14/4  13/4 13/2 14/2 15/8  16/6 15/2 13/4 11/4  13~/16')
WYV_SOLO_CH = ['i', 'VI', 'VII', 'V']
WYV_SOLO1 = ('14b~/8 11/4 9/4  12/4 11/2 9/2 7~/8  10b/4 10/2 12/2 13~/8  13/2 11/2 10/2 8/2 6/2 8/2 10/4 '
             '14b~/8 13/2 11/2 9/4  12/4 11/4 9/2 12/2 14/4  13/4 12/4 10/4 8/4  11p/16')


def wyvern_reactor():
    s = Song('Wyvern Reactor', bpm=216, tonic=61, rroot=37, seed=303)
    pre = dict(rhythm='half', drums=[('halftime', 3), ('build', 1)], bass='half', pad=0.4,
               lead=WYV_PRE, harm=-2, fx=[('riser', 2, 2)])
    chorus = dict(rhythm='chords8', drums='blast', bass='8ths', pad=0.5, lead=WYV_CHORUS, harm=-2,
                  fx=[('boom', 0)])
    theme = dict(rhythm='trem_open', drums='blast', bass='16ths', pad=0.3, lead=WYV_INTRO, harm=2,
                 synth=WYV_INTRO, synth_oct=0, synth_vel=0.45)
    riff = dict(riff=WYV_RIFF, drums='gallop', fill=4)

    s.section('count-in', 2, ['i'], rhythm='sustain', drums='build', bass='whole', fx=[('riser', 0, 2)])
    s.section('theme', 8, WYV_INTRO_CH, fx=[('boom', 0)], **theme)
    s.section('riff', 4, ['i'], **riff)
    s.section('verse 1', 8, WYV_VERSE_CH, rhythm='trem_mute', drums='skank', bass='8ths', synth=WYV_VERSE)
    s.section('pre-chorus', 4, WYV_PRE_CH, **pre)
    s.section('chorus', 8, WYV_CHORUS_CH, **chorus)
    s.section('riff', 4, ['i'], **riff)
    s.section('verse 2', 8, WYV_VERSE_CH, rhythm='gallop', drums='double', bass='8ths', synth=WYV_VERSE)
    s.section('pre-chorus', 4, WYV_PRE_CH, **pre)
    s.section('chorus', 8, WYV_CHORUS_CH, **chorus)
    s.section('interlude (calm)', 8, ['i', 'VI', 'III', 'VII', 'i', 'VI', 'VII', 'V'], bells=0.55, pad=0.45,
              drums=[('none', 6), ('build', 2)], bass=[('none', 7), ('whole', 1)],
              fx=[('riser', 4, 4), ('revcrash', 8)])
    s.section('solo: melodic', 8, WYV_SOLO_CH, rhythm='gallop', drums='double', bass='gallop', pad=0.25,
              lead=WYV_SOLO1, fx=[('boom', 0)])
    s.section('solo: shred runs', 8, WYV_SOLO_CH, rhythm='trem_mute', drums='skank', bass='8ths',
              solo=['six_down', 'pedal', 'six_up', 'seq_down', 'pedal', 'six_down', 'seq_up', 'run_bend'])
    s.section('solo: keyboard', 8, WYV_SOLO_CH, rhythm='chords8', drums='blast', bass='8ths',
              solo=['k16', 'k16', 'k6', 'k6', 'kseq_up', 'ksix_down', 'k6', 'krun'])
    s.section('solo: guitar vs keyboard', 8, WYV_SOLO_CH, rhythm='trem_open', drums='blast', bass='16ths',
              solo=['six_down', 'k6', 'six_up', 'k6', 'pedal', 'kpedal', 'six_down', 'ksix_up'])
    s.section('solo: sweeps + tapping', 8, WYV_SOLO_CH, rhythm='trem_open', drums='double', bass='16ths',
              solo=['sweep', 'sweep', 'sweep', 'sweep', 'tap', 'tap', 'trill', 'run_bend'])
    s.section('solo: twin lead', 8, WYV_INTRO_CH, rhythm='chords8', drums='blast', bass='8ths', pad=0.4,
              lead=WYV_INTRO, harm=2)
    s.section('chorus', 8, WYV_CHORUS_CH, **chorus)
    s.section('chorus (key change +1)', 8, WYV_CHORUS_CH, tr=1, **chorus)
    s.section('outro theme', 8, WYV_INTRO_CH, tr=1, **theme)
    s.section('end', 2, ['i'], rhythm='ring', bass='ring', drums='end', pad=0.4, lead='7~/32', harm=2, tr=1,
              fx=[('boom', 0)])
    return s


SONGS = {'1': (skyforge_inferno, 'powermetal_keyboard_hero_skyforge_inferno'),
         '2': (starfall_overdrive, 'powermetal_keyboard_hero_starfall_overdrive'),
         '3': (wyvern_reactor, 'powermetal_keyboard_hero_wyvern_reactor')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('which', nargs='?', default='all')
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'songs'))
    args = ap.parse_args()
    keys = SONGS if args.which == 'all' else [args.which]
    tmp = tempfile.mkdtemp(prefix='songgen_')
    for k in keys:
        build, fname = SONGS[k]
        song = build()
        wav = os.path.join(tmp, fname + '.wav')
        render(song, wav)
        mp3 = os.path.join(os.path.abspath(args.out), fname + '.mp3')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wav, '-codec:a', 'libmp3lame', '-q:a', '1',
                        '-metadata', f'title={song.title}', '-metadata', 'artist=keyboard_hero',
                        '-metadata', 'genre=Power Metal', mp3], check=True)
        L = song.length()
        print(f'{song.title}: {song.bpm} BPM, {int(L // 60)}:{int(L % 60):02d} (+tail) -> {mp3}')
        for name, b0, bars, tr in song.sections:
            t = song.sec(b0)
            print(f'  {int(t // 60)}:{t % 60:05.2f}  {name}')


if __name__ == '__main__':
    main()
