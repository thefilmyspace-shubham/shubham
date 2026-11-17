// House of Strength: WhatsApp sender.
// Links one WhatsApp number as a "linked device" (scan the QR once from the gym app),
// then sends the messages the Python app asks for. Listens on 127.0.0.1 only, so
// nothing outside this server can use it.
//   GET  /status  -> {state, qr, me, optouts}
//   POST /send    {to: "91XXXXXXXXXX", text, doc_b64?, doc_name?} -> {ok, id} | {ok:false, error}
//   POST /logout  -> unlink this number (a new QR appears)
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import makeWASocket, { useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion, Browsers } from '@whiskeysockets/baileys';
import pino from 'pino';

const PORT = Number(process.env.WA_PORT || 8091);
const AUTH_DIR = process.env.WA_AUTH_DIR || path.resolve('wa-auth');
const OPTOUT_FILE = path.join(AUTH_DIR, '..', 'wa-optouts.json');
const STOP_WORDS = /^\s*(stop|unsubscribe|band karo|mat bhejo|no more)\s*[.!]*\s*$/i;

const st = { state: 'starting', qr: '', me: '', since: Date.now(), lastError: '' };
let sock = null;
let starting = false;

function loadOptouts() {
  try { return JSON.parse(fs.readFileSync(OPTOUT_FILE, 'utf8')); } catch { return []; }
}
function addOptout(num) {
  const list = loadOptouts();
  if (!list.includes(num)) { list.push(num); fs.writeFileSync(OPTOUT_FILE, JSON.stringify(list)); }
}
const digits = (jid) => (jid || '').split('@')[0].split(':')[0].replace(/\D/g, '');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function start() {
  if (starting) return;
  starting = true;
  try {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
    let version;
    try { ({ version } = await fetchLatestBaileysVersion()); } catch { /* use the built-in version */ }
    sock = makeWASocket({
      auth: state,
      logger: pino({ level: 'warn' }),
      browser: Browsers.ubuntu('HOS Gym'),
      markOnlineOnConnect: false,
      syncFullHistory: false,
      ...(version ? { version } : {}),
    });
    sock.ev.on('creds.update', saveCreds);
    sock.ev.on('connection.update', (u) => {
      if (u.qr) { st.state = 'qr'; st.qr = u.qr; st.since = Date.now(); }
      if (u.connection === 'open') {
        st.state = 'connected'; st.qr = ''; st.me = digits(sock.user?.id); st.since = Date.now(); st.lastError = '';
        console.log('whatsapp connected as', st.me);
      }
      if (u.connection === 'close') {
        const code = u.lastDisconnect?.error?.output?.statusCode;
        st.lastError = String(u.lastDisconnect?.error?.message || code || '');
        sock = null;
        if (code === DisconnectReason.loggedOut) {
          // Unlinked from the phone (or banned): forget the login and show a fresh QR.
          console.log('whatsapp logged out');
          st.state = 'logged_out'; st.me = '';
          fs.rmSync(AUTH_DIR, { recursive: true, force: true });
          setTimeout(start, 3000);
        } else {
          st.state = 'connecting';
          setTimeout(start, code === DisconnectReason.restartRequired ? 500 : 5000);
        }
      }
    });
    sock.ev.on('messages.upsert', ({ messages, type }) => {
      if (type !== 'notify') return;
      for (const m of messages) {
        if (m.key.fromMe) continue;
        const text = m.message?.conversation || m.message?.extendedTextMessage?.text || '';
        if (!STOP_WORDS.test(text)) continue;
        // Newer WhatsApp hides numbers behind "lid" ids; the real number is in remoteJidAlt when present.
        const jid = [m.key.remoteJid, m.key.remoteJidAlt, m.key.senderPn].find((j) => j && j.endsWith('@s.whatsapp.net'));
        if (jid) { addOptout(digits(jid)); console.log('opt-out', digits(jid)); }
      }
    });
  } catch (err) {
    st.state = 'error'; st.lastError = String(err?.message || err);
    console.error('start failed', err);
    setTimeout(start, 15000);
  } finally {
    starting = false;
  }
}

async function send(body) {
  if (!sock || st.state !== 'connected') return { ok: false, error: 'not connected' };
  const to = String(body.to || '').replace(/\D/g, '');
  if (to.length < 11 || to.length > 15) return { ok: false, error: 'bad number' };
  if (loadOptouts().includes(to)) return { ok: false, error: 'opted out' };
  const found = await sock.onWhatsApp(to);
  const hit = Array.isArray(found) ? found.find((r) => r.exists) : null;
  if (!hit) return { ok: false, error: 'not on whatsapp' };
  const jid = hit.jid || `${to}@s.whatsapp.net`;
  // Look like a person: show "typing…" for a moment before each message.
  try { await sock.sendPresenceUpdate('composing', jid); } catch { /* ignore */ }
  await sleep(1500 + Math.floor(Math.random() * 2500));
  try { await sock.sendPresenceUpdate('paused', jid); } catch { /* ignore */ }
  let msg;
  if (body.doc_b64) {
    msg = await sock.sendMessage(jid, {
      document: Buffer.from(body.doc_b64, 'base64'), mimetype: 'application/pdf',
      fileName: body.doc_name || 'form.pdf', caption: body.text || '',
    });
  } else {
    msg = await sock.sendMessage(jid, { text: String(body.text || '') });
  }
  return { ok: true, id: msg?.key?.id || '' };
}

function reply(res, code, obj) {
  const data = JSON.stringify(obj);
  res.writeHead(code, { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) });
  res.end(data);
}

const server = http.createServer((req, res) => {
  if (req.method === 'GET' && req.url === '/status') {
    return reply(res, 200, { ...st, optouts: loadOptouts() });
  }
  if (req.method !== 'POST') return reply(res, 404, { ok: false, error: 'not found' });
  let raw = '';
  req.on('data', (c) => { raw += c; if (raw.length > 12e6) req.destroy(); });
  req.on('end', async () => {
    try {
      const body = raw ? JSON.parse(raw) : {};
      if (req.url === '/send') return reply(res, 200, await send(body));
      if (req.url === '/logout') {
        if (sock) { try { await sock.logout(); } catch { /* ignore */ } }
        else { fs.rmSync(AUTH_DIR, { recursive: true, force: true }); setTimeout(start, 500); }
        return reply(res, 200, { ok: true });
      }
      return reply(res, 404, { ok: false, error: 'not found' });
    } catch (err) {
      return reply(res, 200, { ok: false, error: String(err?.message || err).slice(0, 200) });
    }
  });
});

server.listen(PORT, '127.0.0.1', () => console.log('hos-wa listening on 127.0.0.1:' + PORT));
start();
