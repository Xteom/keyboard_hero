// Harness: node tools/tune.mjs [analyzer.js] [filter]
// Decodes songs/*.mp3 (cached in /tmp/kh-raw), runs analyze(), prints BPM/sections/notes/time table.
import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SRC = process.argv[2] || path.join(ROOT, 'tools/analyzer-dev.js');
const FILTER = process.argv[3] || '';
const RAW = '/tmp/kh-raw';
const GT = { windswept: 79, speedier: 94, devastation: 114, notanico: 120, drama: 130, opportunity: 156, ripped: 174 };
const SOFT = { furious: 128 }; // listed 160 is wrong; reported but not counted
const CAPS = [1.2, 1.8, 2.5, 3.2, 4.0], MOODF = { calm: 0.6, groove: 1, peak: 1.35 };

const src = fs.readFileSync(SRC, 'utf8');
if (src.includes('</script')) { console.error('ERROR: source contains </script'); process.exit(1); }
const analyze = new Function(src + ';return analyze;')();
analyze.__debug = true; // exposes onset times so the harness can check note/onset alignment

function load(file) {
  fs.mkdirSync(RAW, { recursive: true });
  const raw = path.join(RAW, path.basename(file, '.mp3') + '.f32');
  if (!fs.existsSync(raw) || fs.statSync(raw).size === 0) {
    const buf = execFileSync('ffmpeg', ['-v', 'error', '-i', file, '-ac', '1', '-ar', '22050', '-f', 'f32le', '-'], { maxBuffer: 1 << 30 });
    fs.writeFileSync(raw, buf);
  }
  const b = fs.readFileSync(raw);
  return new Float32Array(b.buffer, b.byteOffset, b.byteLength >> 2);
}
const mmss = t => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;

const files = fs.readdirSync(path.join(ROOT, 'songs')).filter(f => f.endsWith('.mp3') && f.includes(FILTER)).sort();
let pass = 0, total = 0;
const rows = [];
for (const f of files) {
  const x = load(path.join(ROOT, 'songs', f));
  const t0 = performance.now();
  const r = analyze(x, 1234);
  const ms = performance.now() - t0;
  const key = Object.keys({ ...GT, ...SOFT }).find(k => f.includes(k));
  const gt = GT[key] ?? SOFT[key];
  let st = '';
  if (gt) {
    const ok = Math.abs(r.bpm / gt - 1) <= 0.02;
    st = ok ? 'PASS' : 'FAIL';
    if (GT[key]) { total++; if (ok) pass++; } else st = '(' + st.toLowerCase() + ')';
  }
  // chart checks
  const issues = [];
  const ons = analyze.__dbg && analyze.__dbg.onsets;
  const dens = [];
  for (const c of r.charts) {
    const n = c.notes;
    dens.push(n.length);
    if (n.some(q => q.t < 2)) issues.push(`L${c.level}:<2s`);
    const lastL = {};
    let lg = 0;
    for (const q of n) { if (lastL[q.lane] !== undefined && q.t - lastL[q.lane] < 0.1 - 1e-6) lg++; lastL[q.lane] = q.t; }
    if (lg) issues.push(`L${c.level}:lanegap${lg}`);
    if (ons) {
      let far = 0;
      for (const q of n) { let lo = 0, hi = ons.length - 1; while (hi - lo > 1) { const m = (lo + hi) >> 1; if (ons[m] <= q.t) lo = m; else hi = m; } if (Math.min(Math.abs(ons[lo] - q.t), Math.abs(ons[hi] - q.t)) > 0.03) far++; }
      if (far) issues.push(`L${c.level}:far${far}`);
    }
    for (const s of r.sections) {
      const a = Math.max(2, s.start), b = s.end; if (b - a < 4) continue;
      const k = n.filter(q => q.t >= a && q.t < b).length / (b - a);
      if (k > CAPS[c.level - 1] * MOODF[s.mood] * 1.02) issues.push(`L${c.level}:${s.mood}@${mmss(s.start)}=${k.toFixed(2)}/s`);
    }
  }
  for (let i = 1; i < dens.length; i++) if (dens[i] <= dens[i - 1]) issues.push(`L${i + 1}<=L${i}`);
  const secs = r.sections.map(s => `${s.mood[0].toUpperCase()}${mmss(s.start)}`).join(' ');
  rows.push([f.replace('.mp3', '').slice(0, 34), r.bpm.toFixed(1), gt ?? '-', st, secs, dens.join('/'), (ms / 1000).toFixed(2) + 's', mmss(r.duration), issues.slice(0, 6).join(' ')]);
}
const hdr = ['file', 'bpm', 'gt', 'ok', 'sections (C=calm G=groove P=peak @start)', 'notes L1..L5', 'time', 'len', 'chart issues'];
const w = hdr.map((h, i) => Math.min(i === 4 ? 70 : 99, Math.max(h.length, ...rows.map(r => String(r[i]).length))));
const line = r => r.map((c, i) => String(c).padEnd(w[i])).join(' | ');
console.log(line(hdr)); console.log(w.map(n => '-'.repeat(n)).join('-|-'));
for (const r of rows) console.log(line(r));
console.log(`\nBPM ground truth: ${pass}/${total} pass`);
