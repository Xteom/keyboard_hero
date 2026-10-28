# keyboard_hero: design

*Date: 2026-10-26 · Status: draft for approval*

## 1. Intent

keyboard_hero is a retro rhythm game the user is building for themself, to play on their own PC. It's in the note-highway genre: notes rush down a glowing road toward a hit line, and you hit them in time with the music. What makes it different:

- **Any song becomes playable.** You load an audio file from your computer, and the game listens to it, finds the beat and the song's structure, and builds the note charts itself.
- **The whole keyboard is the controller.** Difficulty sets how many *sections* the keyboard is split into. At level 1 there are two sections: any key on the left half is one button and any key on the right half is the other. Higher levels cut the keyboard into more slices.
- **The look follows the music.** Neon synthwave is the home style. Calm parts of a song turn into green phosphor wireframe, and loud, fast parts turn into chunky 8-bit pixels.

It should feel like the excitement of a rock-concert rhythm game, but with an original retro look. Fun matters more than features.

**Success looks like this:** the user drops in a song they like, picks a level, and plays a chart that clearly follows the music, with hits that feel tight and fair.

## 2. Goals, non-goals, anti-goals

**Goals**
- One self-contained HTML file. It uses no external assets of any kind: no images, web fonts, libraries, CDNs or network calls. Everything is drawn and synthesized in code, and the file should stay light (aim for under about 150 KB of source).
- It loads any audio file Chrome can decode, analyzes it, and generates charts for all 5 levels.
- It remembers loaded songs (and their analysis and best scores) between sessions.
- Neon Highway look, with the style changing as the song's energy changes.
- Keyboard calibration (lining the drawing up with the real keyboard, testing lanes, switching keys off) and timing calibration, reachable from the start menu at any time.

**Non-goals for this version** (decided by the user: "first make the game work")
- Shipping, distribution, credits or licensing screens. It's personal use only, for now.
- Support for other keyboards or layouts. The game targets **the user's own keyboard: a full-size keyboard with a numpad**. There are no shape or layout pickers.
- Mobile, touch, gamepads, multiplayer, online leaderboards, a chart editor, or songs bundled inside the file.
- Hold or sustain notes (only tap notes and 2-note chords).

**Anti-goals** (would count as failure even if everything technically works)
- Charts that feel random or off the beat.
- Input that feels laggy, or hits that are judged unfairly.
- Style switches that disturb reading the notes. The road, lanes and hit line must **never** move or resize when the style changes.
- Browser shortcuts or page scrolling firing mid-song from a game key.
- The game needing the network to work.

## 3. Constraints

- **Runtime:** desktop Google Chrome on the user's Linux PC. The game is opened as a local file (`file://`). Firefox would be nice but isn't required.
- **Storage under `file://`: verified on 2026-10-26.** In a page opened via `file://` in Chrome, localStorage and IndexedDB (including a 1 MB Blob) both persisted across a full browser restart with the same profile, so no local server is needed.
- **Tech:** only browser APIs: Canvas 2D, Web Audio, IndexedDB, localStorage, Web Workers (a worker created from inline code via a Blob URL is fine), the File API, and drag-and-drop.
- **Keys:** matched by `KeyboardEvent.code` (physical position). Only the main letter/number block plays.

## 4. Screens

Visual reference mockups are in `docs/mockups/`. They're HTML fragments made for a browser preview frame, so open them for look and feel, not code:
- `play-screen-style.html`: the three styles side by side. The user picked A (Neon Highway).
- `style-follows-music-v2.html`: a live animated preview of style switching across calm, groove and peak sections. The user loved this.
- `keyboard-setup-v4.html`: the working calibration prototype, with its key layout, lane-split math, line-up sliders and timing check. Reuse its logic.
- `songs-and-results.html`: the Songs tab and Results screen.

### 4.1 Start menu (title screen)
- The neon title "KEYBOARD HERO" over the animated neon road (no notes, slow scroll).
- Menu: **PLAY** (opens Songs), **SONGS**, **CALIBRATE**. The user asked for this so they can recalibrate whenever needed.
- It works by keyboard (↑ ↓ Enter, Esc to go back) and also by mouse.
- **First launch:** if no calibration is saved, the game goes straight into CALIBRATE and then on to SONGS.

### 4.2 CALIBRATE (3 steps; BACK and NEXT buttons; DONE saves)
This is prototyped in `keyboard-setup-v4.html`.
1. **Line up your keyboard.** The screen shows a drawing of the user's full-size keyboard: F-key row, main block, nav cluster with arrows, and numpad. Everything outside the main block is drawn dimmed and marked "not used". Two sliders, **POSITION** and **SIZE**, move and scale the drawing until each drawn key sits directly above the matching real key under the monitor. Keyboard control: ← → move, ↑ ↓ resize, holding Shift takes bigger steps, and pressing a key lights it up so you can line up the two ends (` and ⌫). Values are stored as fractions of the screen width. The game runs full screen, so calibration happens full screen too.
2. **Test your lanes.** Pick a level from L1 to L5, then press keys: each key lights in its lane's color and the lane flashes. Clicking a key switches it off or back on (saved). A counter shows how many keys have been tested.
3. **Timing.** 4 count-in clicks, then 12 clicks at 100 BPM. The player taps any play key, and the game takes the median offset (tap time minus click time, both measured on the audio output clock) as a global offset applied to all judging. It also shows the spread. *(Builder's call: a manual ±5 ms fine-tune.)*

### 4.3 SONGS
This is mocked up in `songs-and-results.html` (screen 1).
- **Adding songs:** drag and drop, or press **O** for a file picker; multiple files are allowed. Each file is stored in IndexedDB and then analyzed in a background worker, with a progress display ("ANALYZING… 62%"). The analysis result is stored too, so a song is analyzed only once.
- **Song list:** title (from the filename, with underscores turned into spaces; reading tags is out of scope), length, detected BPM, a thin **mood strip** (calm/groove/peak segments across the song's timeline), and best grade per level (L1 to L5).
- **Detail panel:** title, BPM, length, the large mood strip, a **level selector L1 to L5** (2 to 6 lanes, drawn as lane icons), **SPEED** (how long notes take to travel; for example 0.75x, 1.0x, 1.25x, 1.5x), best score for the chosen level, and PRESS ENTER TO PLAY.
- **Keys:** ↑ ↓ choose a song, ← → choose a level, Enter plays, Del removes (with a confirmation).

### 4.4 PLAY
- **Road:** the Neon Highway perspective road, with the hit line at about 86% of the screen height and notes traveling from the horizon to the hit line.
- **Lanes are lined up with the real keyboard (decided by the user).** At the hit line, lane *i* spans the screen x-range that sits directly above keyboard section *i*, worked out from the line-up calibration. The bottom of the road matches the width of the main key block, and lanes may be unequal in width because the split follows the keyboard. A thin strip of keycap silhouettes under the hit line shows the sections in lane colors *(my call)*. The road still converges toward a vanishing point at the horizon.
- **Style follows the song's sections:** calm parts use **Phosphor Vector** (green wireframe on black), groove parts use **Neon Highway**, and peak parts use **8-bit Arcade** (drawn at low resolution and scaled up with nearest-neighbor). Switches happen on a downbeat at section boundaries, with a quick CRT glitch of about 0.35 s and the section name flashing. The road, lanes, hit line and HUD positions are identical in every style. **The glitch affects only the background and scenery layers.** Notes, lanes and the hit line are drawn on top and are never displaced, unlike in the preview mockup, where the glitch shifts everything.
- **Hits** (my calls): any key in a lane's section hits the nearest unhit note in that lane. Judgement windows are **PERFECT ±45 ms, GREAT ±90 ms, OK ±135 ms**; anything further out is a MISS once a note passes. Pressing a lane with no note nearby costs nothing (no penalty). Judging uses `event.timeStamp` converted to song time, not the frame time.
- **Feedback:** a lane flash and rating text on each hit. On a miss, the song goes briefly muffled (a lowpass filter for about 300 ms) and the lane flashes red.
- **Score** (my call): PERFECT = 100, GREAT = 70, OK = 40, times a combo multiplier that steps up every 10 hits to a maximum of x4 and resets on a miss.
- **HUD:** score, combo, multiplier, song progress, and the level and lane count.
- **No fail:** the song always plays to the end.
- **Pause:** Esc pauses with Resume / Restart / Quit to songs. Losing window focus also pauses, and so does leaving full screen. Resuming shows a 3-2-1 countdown. *(Builder's call: in full screen, use Chrome's Keyboard Lock API `navigator.keyboard.lock(['Escape'])` so Esc pauses instead of leaving full screen. If that isn't available, leaving full screen just counts as a pause.)*
- **Lead-in:** the road scrolls for about 2 s before the audio starts, so the first notes can be reached.
- Every main-block key calls `preventDefault()` during play, so the page never scrolls, finds or navigates. F-keys stay alone.

### 4.5 RESULTS
This is mocked up in `songs-and-results.html` (screen 2). **The user approved this design ("I liked the second option for the results"), so build it as mocked.**
- **Grade:** S 97%+, A 90%+, B 80%+, C 70%+, else D. Accuracy = (PERFECT + 0.75·GREAT + 0.4·OK) / total notes.
- Score, accuracy, max combo, and PERFECT/GREAT/OK/MISS counts. "NEW BEST!" appears when the result beats the stored best for that song and level.
- An "accuracy over the song" graph drawn over the mood bands.
- Enter retries, Esc goes back to SONGS.

## 5. Keyboard model and lanes
This is implemented and tested in `keyboard-setup-v4.html`.
- **Drawing:** full-size ANSI layout in key units. The F-row is at y=0. The main block covers 5 rows at y=1.5 to 5.5 and is 15 units wide. The nav cluster starts at x=15.5 and the numpad at x=19, for 23 units in total.
- **Playable keys:** the main-block rows from the number row to the bottom letter row, including Tab, Backspace, `\`, Enter and both Shifts. **Caps Lock, Space, Ctrl, Alt, Win and Menu are never used**, and neither is anything outside the main block. Esc pauses the game. If the `IntlBackslash` key ever fires, treat it as a left-edge key; no ISO UI is needed.
- **Section split:** each key's centre x (in units) goes through a two-piece mapping that is split at the hand gap between **G and H** (x = 6.9; main block width 15):
  `u = x < 6.9 ? 0.5·x/6.9 : 0.5 + 0.5·(x−6.9)/(15−6.9)`, and `lane = floor(u · lanes)`.
  At level 1 this gives the touch-typing split (6|7, T|Y, G|H, B|N).
- **Levels:** L1 = 2 lanes, L2 = 3, L3 = 4, L4 = 5, L5 = 6.
- **Lane edges on screen:** invert the same mapping for u = k/lanes, then apply the line-up calibration to turn units into screen x.

## 6. Song analysis and chart generation (the core)

This runs in a Web Worker on a decoded, mono, downsampled signal (for example 22,050 Hz mixed down with an OfflineAudioContext). The exact DSP parameters are the builder's call. Required outputs and behavior:
- **Onsets:** spectral-flux onset detection in at least 3 bands (low, mid, high), with an adaptive threshold and peak picking. Each onset records its time, strength and dominant band or brightness.
- **Tempo and beats:** a tempo estimate (autocorrelation or similar, 60 to 200 BPM, favoring 80 to 160) and beat tracking (dynamic programming or similar) that can cope with gradual drift. Bars are 4 beats, with the downbeat phase chosen by low-band energy. A song with a clear tempo change should keep the beats on track (for example by re-estimating tempo per window).
- **Sections (moods):** loudness and onset density per bar, smoothed, split into segments of at least 8 bars, each labeled **calm, groove or peak** relative to the song itself (calm = its quietest and sparsest stretches, peak = its loudest and busiest). Use hysteresis so the label doesn't flicker. Boundaries snap to downbeats. These drive both the style switching and the mood strip. A song with little dynamic contrast can be mostly or entirely "groove"; don't force calm or peak sections that aren't really there.
- **Charts, one per level, deterministic** (seeded from a hash of the file):
  - Candidate note times come from onsets snapped to the beat grid (½-beat grid at low levels, ¼-beat at high levels), keeping the strongest ones.
  - **Note density rises gently with level and follows the music's energy** *(my call; see section 10)*. Targets are roughly 1.2 notes/s at L1, 1.8 at L2, 2.5 at L3, 3.2 at L4 and 4.0 at L5, with fewer notes in calm sections and more in peak sections. **These targets are soft caps, not quotas.** Notes are placed only where there's a detected onset (snapped to the grid); the generator never invents notes on silent grid points to reach a number. Slow or sparse songs simply get fewer notes. A chart that follows the music beats one that hits the density target.
  - **Lane choice follows pitch:** low or bass-heavy sounds go left and bright or high sounds go right, with pattern rules that break up long same-lane runs and avoid jarring jumps.
  - **Chords:** from L3 up, 2-note chords on strong accents (especially peak downbeats), at most 2 at once.
  - At least 100 ms (and at least ¼ beat) between notes in the same lane. No notes in the first 2 s.
- **Speed:** a 4-minute song should analyze in under about 10 s on a normal desktop PC. Show progress.
- **Storage:** save `duration, bpm, beats, sections, charts[5]` with an `analysisVersion`, and re-analyze automatically when the version changes.

## 7. Audio and timing
- **Playback chain:** AudioBufferSourceNode → lowpass BiquadFilter (normally fully open; used for the miss muffle) → GainNode → destination.
- **Song clock:** from the AudioContext, using `getOutputTimestamp()` to line up audio-output time with `performance.now()` and key `event.timeStamp`, plus the calibrated offset.
- **Rendering:** a requestAnimationFrame Canvas 2D loop that respects devicePixelRatio, aiming for a smooth 60 fps or more.
- **Sound effects:** synthesized only (a menu blip, the calibration clicks). There are no hit sounds.

## 8. Persistence
- **localStorage `keyboard_hero.settings`:** the line-up calibration (position and size), switched-off keys, timing offset, speed, volume, last level and last song.
- **IndexedDB `keyboard_hero`:**
  - `songs`: id (content hash), name, size, addedAt, the audio Blob.
  - `analysis`: id, version, plus the outputs in section 6.
  - `scores`: songId plus level → best score, grade, accuracy and date.

## 9. Testing and acceptance
- **The user's explicit requirement:** test in a real browser. Drive headless Chrome over the DevTools protocol (a working driver exists at `/tmp/kh-test/cdp-check.mjs`; move it to `tools/`). Load the game, send real key events, take screenshots of each screen, read them, and report the console errors.
- **Synthetic tests:** generate click and drum tracks in code at known BPMs, including one with a tempo change. Detected BPM must be within ±1%, and beats within ±20 ms.
- **Real tracks:** the music-downloader session is putting CC0 and CC-BY tracks in `./songs/`, with BPMs listed in `songs/CREDITS.md`. Detected BPM must be within ±2% on tracks with a published BPM (a half or double result counts as a failure). Tracks with obvious calm and loud parts should get at least one calm and one peak section. Load them into the game during tests through DevTools (`DOM.setFileInputFiles`).
- **Chart sanity:** every note lies within ±30 ms of a detected onset; same-lane spacing is respected; no song-wide density *exceeds* its level's target by more than 30%; and on songs between 90 and 170 BPM with steady drums, each level reaches at least 60% of its target. Densities rise strictly from L1 to L5.
- **Test tracks are delivered:** 14 mp3s (79 MB) are in `songs/`, with notes in `songs/CREDITS.md`. BPM ground truth uses only the 7 tracks whose published BPM was confirmed against the audio (Windswept 79, Speedier than Photons 94, Devastation and Revenge 114, Notanico Merengue 120, Drama 130, Opportunity Walks 156, Ripped Apart 174). Drama and Ripped Apart also have strong 87 BPM periodicity, so they're good traps for octave and triplet errors. **Furious Freak's published 160 is wrong (the audio measures about 128); don't use it as ground truth.** Tracks for testing calm/peak sections: Furious Freak, Devastation and Revenge, and Hall of the Mountain King. Tracks for testing tempo change: Invariance (switches from slow to fast at about 1:50–2:05) and Hall of the Mountain King (gradual accelerando).
- **Last check:** the user plays it.

## 10. Calls I made (for the user to check)
1. Note density rises gently with level. Difficulty is mainly lane count (as the user specified), but more lanes with the same sparse notes would feel empty.
2. Judgement windows of ±45/90/135 ms, no penalty for pressing an empty lane, and no fail.
3. Scoring: 100/70/40 points times a combo multiplier up to x4; grade cutoffs S 97%, A 90%, B 80%, C 70%.
4. A miss muffles the song briefly. There are no hit sounds.
5. A thin keycap strip under the hit line shows the sections.
6. Song titles come from filenames; tag reading is out of scope.
7. Hold notes are out of scope for v1.

## 11. Left to the builder
The DSP details and parameters, worker and message structure, how code is organized inside the single file, exact visuals beyond the mockups, menu animation, and the pause menu's look.
