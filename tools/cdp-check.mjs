// Drive headless Chrome over the DevTools protocol: load a URL, run steps, collect errors.
// usage: node tools/cdp-check.mjs <url> <outdir> <step>...
//   step = <ms>                       wait until <ms> after navigation, then screenshot to <outdir>/t<ms>.png
//   step = js:<code>                  evaluate <code> in the page (promises awaited) and print the result
//   step = key:<code>[:<key>[:<vk>]]  trusted keyDown/keyUp via the Input domain
//   step = files:<selector>:<paths>   set comma-separated files (or one folder) on an <input type=file>
// env KH_PROFILE=<dir> reuses a Chrome profile (to test persistence across runs).
import { spawn } from 'node:child_process';
import fs from 'node:fs';

const [url, out, ...steps] = process.argv.slice(2);
const port = 9333 + Math.floor(Math.random() * 500);
const chrome = spawn('google-chrome', [
  '--headless=new', '--disable-gpu', '--no-sandbox', `--remote-debugging-port=${port}`,
  `--user-data-dir=${process.env.KH_PROFILE || `/tmp/kh-cdp-prof-${port}`}`, '--window-size=1200,900', '--hide-scrollbars',
  '--autoplay-policy=no-user-gesture-required', 'about:blank',
], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));

let targets = [];
for (let i = 0; i < 50 && !targets.length; i++) {
  try { targets = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).filter(t => t.type === 'page'); } catch {}
  if (!targets.length) await sleep(200);
}
const ws = new WebSocket(targets[0].webSocketDebuggerUrl);
await new Promise(r => (ws.onopen = r));

let id = 0;
const pending = new Map();
const errors = [];
ws.onmessage = ev => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); return; }
  if (m.method === 'Runtime.exceptionThrown') {
    const d = m.params.exceptionDetails;
    errors.push(`exception: ${d.exception?.description || d.text} (line ${d.lineNumber})`);
  } else if (m.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(m.params.type)) {
    errors.push(`console.${m.params.type}: ` + m.params.args.map(a => a.value ?? a.description).join(' '));
  } else if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') {
    errors.push(`log: ${m.params.entry.text}`);
  }
};
const send = (method, params = {}) => new Promise(r => {
  const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params }));
});

await send('Runtime.enable'); await send('Log.enable'); await send('Page.enable');
await send('Page.navigate', { url });
const start = Date.now();
fs.mkdirSync(out, { recursive: true });
for (const step of steps) {
  if (step.startsWith('files:')) {
    const [, sel, paths] = step.match(/^files:([^:]+):(.+)$/);
    const doc = await send('DOM.getDocument', {});
    const q = await send('DOM.querySelector', { nodeId: doc.result.root.nodeId, selector: sel });
    await send('DOM.setFileInputFiles', { nodeId: q.result.nodeId, files: paths.split(',') });
    console.log('files set', paths.split(',').length);
  } else if (step.startsWith('key:')) {
    const [, code, key = code.replace(/^(Key|Digit)/, '').toLowerCase(), vk] = step.split(':');
    const vkc = vk ? +vk : (key.length === 1 ? key.toUpperCase().charCodeAt(0) : 0);
    await send('Input.dispatchKeyEvent', { type: 'keyDown', code, key, windowsVirtualKeyCode: vkc });
    await send('Input.dispatchKeyEvent', { type: 'keyUp', code, key, windowsVirtualKeyCode: vkc });
    console.log('key', code);
  } else if (step.startsWith('js:')) {
    const r = await send('Runtime.evaluate', { expression: step.slice(3), returnByValue: true, awaitPromise: true });
    console.log('eval', step.slice(3, 60).replace(/\n/g, ' '), '=>', JSON.stringify(r.result?.result?.value ?? r.result?.exceptionDetails?.exception?.description ?? r.result?.exceptionDetails?.text));
  } else {
    const ms = +step;
    await sleep(Math.max(0, ms - (Date.now() - start)));
    const r = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(`${out}/t${ms}.png`, Buffer.from(r.result.data, 'base64'));
    console.log('screenshot', `${out}/t${ms}.png`);
  }
}
console.log(JSON.stringify({ errors }, null, 1));
ws.close();
chrome.kill();
process.exit(0);
