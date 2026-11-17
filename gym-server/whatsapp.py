"""Automatic WhatsApp messages from the gym's own (separate) WhatsApp number.

The number is linked like WhatsApp Web, by scanning a QR on the WhatsApp page; the small
Node service in wa/ (systemd unit hos-wa) holds that login and sends. This module decides
what to send and when, and keeps every message in the wa_queue table:

  - every morning it plans the day's reminders (expiring soon, expired yesterday, dues on
    Mondays, birthdays from joining forms);
  - a sender thread sends one message at a time with a random 1-3 minute gap, only in
    the allowed hours and up to a daily limit, so the number behaves like a person;
  - receipts after a bill and joining-form links go first.

This is not the official WhatsApp API, so WhatsApp can block the number. Use a separate SIM,
keep the daily limit low, and members who reply STOP are never messaged again.
"""
import base64
import datetime
import json
import os
import random
import re
import sqlite3
import threading
import time
import urllib.error
import urllib.request

import members as M
import messages as MSG

WA_URL = os.environ.get("HOS_WA_URL", "http://127.0.0.1:8091")
HERE = os.path.dirname(os.path.abspath(__file__))
_wake = threading.Event()

KINDS = [  # key, label, default template (versions joined by ---), default on
    ("receipt", "Receipt after a bill", "", "1"),
    ("form", "Joining form link", MSG.joined("form"), "1"),
    ("expiring", "Membership ending soon", MSG.joined("expiring"), "1"),
    ("expired", "Membership ended yesterday", MSG.joined("expired"), "1"),
    ("due", "Pending payment (Mondays)", MSG.joined("due"), "1"),
    ("birthday", "Birthday wish", MSG.joined("birthday"), "1"),
]
MANUAL = [  # texts used by buttons, not sent on their own
    ("absent", "Absent members (Absent page, Remind selected)"),
    ("greet", "WhatsApp button on a member's page"),
    ("inquiry", "Inquiry follow-up button"),
]
STAFF_TEMPLATES = [  # late rule messages to staff; {n} = which late day this month
    ("notice", "1st late in the month: Notice", MSG.joined("staff_notice")),
    ("warning", "2nd late: Warning", MSG.joined("staff_warning")),
    ("deduct", "3rd and later: Pay cut", MSG.joined("staff_deduct")),
]
TEMPLATE_VERSION = "2"  # 2: English, several versions each
TPL = {}  # kind -> text from settings (kept in memory so buttons need no database)
LABEL = dict({k: l for k, l, _, _ in KINDS}, staff="Staff late notice", test="Test", remind_renew="Renewal reminder (selected)",
             remind_due="Due reminder (selected)", remind_absent="Absent reminder (selected)")
FIRST = ("test", "receipt", "form", "staff")  # sent before the daily reminders


def init(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS wa_queue (
        id INTEGER PRIMARY KEY, kind TEXT, client_id INTEGER, phone TEXT, ref TEXT, text TEXT, doc TEXT,
        status TEXT DEFAULT 'queued', created_at TEXT, sent_at TEXT, error TEXT, UNIQUE (kind, client_id, ref))""")
    defaults = {"wa_auto": "0", "wa_cap": "40", "wa_from": "9", "wa_to": "20", "wa_plan_hour": "10", "wa_days_before": "3",
                "wa_planned": "", "wa_optout": "[]"}
    for k, l, t, on in KINDS:
        defaults["wa_on_" + k] = on
        if t:
            defaults["wa_t_" + k] = t
    defaults["wa_on_staff"] = "1"
    for k, _, t in STAFF_TEMPLATES:
        defaults["wa_t_staff_" + k] = t
    for k, _ in MANUAL:
        defaults["wa_t_" + k] = MSG.joined(k)
    for k, v in defaults.items():
        conn.execute("INSERT OR IGNORE INTO settings VALUES (?, ?)", (k, v))
    if M.setting(conn, "wa_tpl_v", "") != TEMPLATE_VERSION:
        # New message set: replace the earlier (Hinglish, single-version) texts.
        for k, _, t, _ in KINDS:
            if t:
                M.set_setting(conn, "wa_t_" + k, t)
        for k, _ in MANUAL:
            M.set_setting(conn, "wa_t_" + k, MSG.joined(k))
        for k, _, t in STAFF_TEMPLATES:
            M.set_setting(conn, "wa_t_staff_" + k, t)
        M.set_setting(conn, "wa_tpl_v", TEMPLATE_VERSION)
    load(conn)


def load(conn):
    """Refresh the in-memory copy of every message text."""
    for k, _, t, _ in KINDS:
        if t:
            TPL[k] = M.setting(conn, "wa_t_" + k, t) or t
    for k, _ in MANUAL:
        TPL[k] = M.setting(conn, "wa_t_" + k, "") or MSG.joined(k)
    for k, _, t in STAFF_TEMPLATES:
        TPL["staff_" + k] = M.setting(conn, "wa_t_staff_" + k, "") or t


# ---------------- talking to the Node service ----------------

def _call(path, payload=None, timeout=5):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(WA_URL + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode() or "{}")


def status():
    try:
        return _call("/status", timeout=3)
    except (urllib.error.URLError, OSError, ValueError):
        return {"state": "off"}


def ready(conn):
    """Automatic sending is on and the number is linked."""
    return M.setting(conn, "wa_auto", "0") == "1" and status().get("state") == "connected"


def logout():
    try:
        return _call("/logout", {}, timeout=15)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


# ---------------- queue ----------------

def norm(phone):
    d = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if len(d) == 10 and d[0] in "6789":
        return "91" + d
    if len(d) == 12 and d.startswith("91"):
        return d
    return ""


def optouts(conn):
    try:
        return set(json.loads(M.setting(conn, "wa_optout", "[]")))
    except ValueError:
        return set()


def enqueue(conn, kind, client_id, phone, text, ref="", doc=""):
    """Returns True when queued (False: bad number, opted out, or already queued for this ref)."""
    p = norm(phone)
    if not p or p in optouts(conn) or not text:
        return False
    cur = conn.execute("INSERT OR IGNORE INTO wa_queue (kind, client_id, phone, ref, text, doc, created_at) VALUES (?,?,?,?,?,?,?)",
                       (kind, client_id or 0, p, ref or M.stamp(), text, doc, M.stamp()))
    if cur.rowcount:
        _wake.set()
    return bool(cur.rowcount)


def versions(kind):
    raw = TPL.get(kind) or MSG.joined(kind)
    return [v.strip() for v in re.split(r"\n\s*-{3,}\s*\n", raw) if v.strip()]


def text(kind, turn=None, **kw):
    """One version of a message with the blanks filled. turn picks the version (by turn); None = random."""
    vs = versions(kind)
    if not vs:
        return ""
    t = vs[turn % len(vs)] if turn is not None else random.choice(vs)
    if not kw.get("name"):
        t = re.sub(r"[ ,]*\{name\}", "", t)  # "Hi {name}," -> "Hi,"
    for k, v in kw.items():
        t = t.replace("{%s}" % k, str(v))
    return t


def fill(conn, kind, key="", **kw):
    """Like text(), but each member gets the next version each time (counted from messages already queued)."""
    turn = None
    if key and conn is not None:
        turn = conn.execute("SELECT COUNT(*) FROM wa_queue WHERE phone=? AND (kind=? OR kind=?)",
                            (norm(key), kind, "remind_" + {"expiring": "renew"}.get(kind, kind))).fetchone()[0]
    return text(kind, turn, **kw)


def _nice(name):
    return " ".join(w.capitalize() for w in (name or "").split())


def _date(iso_):
    d = M.parse_date(iso_)
    return d.strftime("%d-%m-%Y") if d else ""


def plan(conn):
    """Queue today's reminders. Safe to run more than once a day (duplicates are ignored)."""
    t = M.today()
    staff_from = M.STAFF_FROM
    on = lambda k: M.setting(conn, "wa_on_" + k, "0") == "1"
    n = 0
    days = int(M.setting(conn, "wa_days_before", "3") or 3)
    rows = conn.execute("SELECT * FROM members WHERE client_id < ? AND phone != ''", (staff_from,)).fetchall()
    for m in rows:
        exp = M.parse_date(m["expiry"])
        if not exp:
            continue
        name = _nice(m["name"])
        if on("expiring") and exp == t + datetime.timedelta(days=days):
            n += enqueue(conn, "expiring", m["client_id"], m["phone"], fill(conn, "expiring", m["phone"], name=name, date=_date(m["expiry"])), m["expiry"])
        if on("expired") and exp == t - datetime.timedelta(days=1):
            n += enqueue(conn, "expired", m["client_id"], m["phone"], fill(conn, "expired", m["phone"], name=name, date=_date(m["expiry"])), m["expiry"])
        if on("due") and t.weekday() == 0 and (m["pending"] or 0) > 0 and exp >= t - datetime.timedelta(days=30):
            amt = "₹{:,.0f}".format(m["pending"])
            n += enqueue(conn, "due", m["client_id"], m["phone"], fill(conn, "due", m["phone"], name=name, amount=amt), "%d-W%02d" % t.isocalendar()[:2])
    if on("birthday"):
        try:
            jrows = conn.execute("SELECT j.client_id, j.data, m.name, m.phone FROM joinings j JOIN members m ON m.client_id=j.client_id "
                                 "WHERE j.status='added'").fetchall()
        except sqlite3.OperationalError:
            jrows = []
        for r in jrows:
            try:
                dob = M.parse_date(json.loads(r["data"] or "{}").get("dob", ""))
            except ValueError:
                dob = None
            if dob and (dob.month, dob.day) == (t.month, t.day):
                name = _nice(r["name"])
                n += enqueue(conn, "birthday", r["client_id"], r["phone"], fill(conn, "birthday", r["phone"], name=name), str(t.year))
    # Reminders that could not go out within two days are stale; drop them.
    old = (t - datetime.timedelta(days=2)).isoformat()
    conn.execute("UPDATE wa_queue SET status='skipped', error='too old' WHERE status='queued' AND (kind IN "
                 "('expiring','expired','due','birthday') OR kind LIKE 'remind_%') AND created_at < ?", (old,))
    M.set_setting(conn, "wa_planned", t.isoformat())
    return n


def sent_today(conn):
    return conn.execute("SELECT COUNT(*) FROM wa_queue WHERE status='sent' AND substr(sent_at,1,10)=?",
                        (M.today().isoformat(),)).fetchone()[0]


def _next(conn, kinds=None):
    order = " ".join("WHEN '%s' THEN %d" % (k, i) for i, k in enumerate(FIRST))
    where = (" AND kind IN (%s)" % ",".join("'%s'" % k for k in kinds)) if kinds else ""
    return conn.execute("SELECT * FROM wa_queue WHERE status='queued'%s ORDER BY CASE kind %s ELSE 9 END, id LIMIT 1"
                        % (where, order)).fetchone()


def _send_one(db_path, priority_only=False):
    """Send the next queued message if allowed now. Returns the kind sent (or tried), else "".

    Messages staff start themselves (test, receipt, joining form) go at once. The daily
    reminders go only when automatic sending is on, inside the hours and the daily limit.
    A test message goes even while automatic sending is off, so the link can be checked first.
    """
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        S = lambda k, d="": M.setting(conn, k, d)
        auto = S("wa_auto", "0") == "1"
        st = status()
        if st.get("optouts"):
            have = optouts(conn)
            new = set(st["optouts"]) - have
            if new:
                M.set_setting(conn, "wa_optout", json.dumps(sorted(have | new)))
                conn.execute("UPDATE wa_queue SET status='skipped', error='replied STOP' WHERE status='queued' AND phone IN (%s)"
                             % ",".join("?" * len(new)), tuple(new))
                conn.commit()
        if st.get("state") != "connected":
            return ""
        row = _next(conn, FIRST if auto else ("test",))
        if not row and auto and not priority_only:
            hour = datetime.datetime.now().hour
            if int(S("wa_from", "9")) <= hour < int(S("wa_to", "20")) and sent_today(conn) < int(S("wa_cap", "40") or 40):
                row = _next(conn)
        if not row:
            return ""
        payload = {"to": row["phone"], "text": row["text"]}
        if row["doc"]:
            path = os.path.join(HERE, os.path.basename(row["doc"]))
            try:
                with open(path, "rb") as fh:
                    payload["doc_b64"] = base64.b64encode(fh.read()).decode()
                payload["doc_name"] = "HOS-joining-form.pdf"
            except OSError:
                pass
    finally:
        conn.close()
    try:
        res = _call("/send", payload, timeout=60)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        res = {"ok": False, "error": "service: %s" % exc}
    conn = sqlite3.connect(db_path, timeout=10)
    try:
        if res.get("ok"):
            conn.execute("UPDATE wa_queue SET status='sent', sent_at=?, error='' WHERE id=?", (M.stamp(), row["id"]))
        elif res.get("error") == "not connected":
            return ""  # stays queued; try again when linked
        else:
            conn.execute("UPDATE wa_queue SET status='failed', sent_at=?, error=? WHERE id=?",
                         (M.stamp(), str(res.get("error", ""))[:200], row["id"]))
        conn.commit()
    finally:
        conn.close()
    return row["kind"]


def loop(db_path):
    next_reminder = 0.0  # reminders keep a 1-3 minute gap; staff messages never wait for it
    while True:
        _wake.clear()  # anything queued from now on wakes the wait below
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            conn.row_factory = sqlite3.Row
            try:
                now = datetime.datetime.now()
                if (M.setting(conn, "wa_auto", "0") == "1" and now.hour >= int(M.setting(conn, "wa_plan_hour", "10"))
                        and M.setting(conn, "wa_planned", "") != now.date().isoformat()):
                    print("whatsapp: planned %d reminders" % plan(conn), flush=True)
                    conn.commit()
            finally:
                conn.close()
            kind = _send_one(db_path, priority_only=time.time() < next_reminder)
            if kind in FIRST:
                continue  # more staff messages may be waiting: go again at once
            if kind:
                next_reminder = time.time() + random.randint(60, 180)
        except Exception as exc:
            print("whatsapp loop error: %s" % exc, flush=True)
        wait = 60 if time.time() >= next_reminder else min(60, max(1, next_reminder - time.time()))
        _wake.wait(wait)


# ---------------- page ----------------

def page(conn, sn, q):
    import html
    import ui as U
    e = html.escape
    st = status()
    S = lambda k, d="": M.setting(conn, k, d)
    state = st.get("state", "off")
    if state == "connected":
        conn_html = ('<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap"><span class="pill p-ok">Linked</span>'
                     '<b>+%s</b><form method="post" action="/whatsapp/save" onsubmit="return confirm(\'Unlink this number from the app?\')">'
                     '<button class="btn sm" name="do" value="logout">Unlink number</button></form></div>' % e(st.get("me", "")))
    elif state == "off":
        conn_html = ('<div class="warn" style="margin:0">The WhatsApp service is not running on the server. '
                     'Run the WhatsApp setup commands once (see README), then refresh.</div>')
    else:
        # Not linked yet: show the QR and keep it fresh without reloading the page, so a scan is never cut off.
        conn_html = """<div style="display:flex;gap:18px;align-items:center;flex-wrap:wrap">
<div style="display:flex;flex-direction:column;gap:8px;align-items:center"><div id="waqr" style="background:#fff;padding:10px;border-radius:12px;width:260px;height:260px;display:flex;align-items:center;justify-content:center;color:#555;font-size:13px">Getting QR…</div>
<span id="wast" class="dim" style="font-size:12px"></span></div>
<ol style="margin:0;padding-left:18px;line-height:1.9;flex:1;min-width:220px"><li>Open WhatsApp on the <b>gym's separate phone</b> (not the main number).</li>
<li>Tap <b>⋮ → Linked devices → Link a device</b>.</li><li>Scan this QR. It changes by itself every ~20 seconds; the page does not reload.</li>
<li>After the scan wait 10-20 seconds; this box turns into <b>Linked</b>.</li></ol></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<script>(function(){var last='',box=document.getElementById('waqr'),st=document.getElementById('wast');
function draw(q){if(q===last){return}last=q;box.innerHTML='';try{new QRCode(box,{text:q,width:240,height:240,correctLevel:QRCode.CorrectLevel.L})}catch(x){box.textContent='QR could not be drawn.'}}
function tick(){fetch('/whatsapp/status',{cache:'no-store'}).then(function(r){return r.json()}).then(function(d){
if(d.state==='connected'){st.textContent='Linked! Opening…';location.reload();return}
if(d.state==='qr'&&d.qr){draw(d.qr);st.textContent='Scan now'}else{st.textContent=(d.state||'').replace('_',' ')+'… new QR coming'}
setTimeout(tick,3000)}).catch(function(){setTimeout(tick,5000)})}
draw(%s);tick()})();</script>""" % json.dumps(st.get("qr", "") if state == "qr" else "")
    auto = S("wa_auto", "0") == "1"
    kinds = ""
    for k, label, t, _ in KINDS:
        tpl = ('<textarea name="wa_t_%s" rows="9" style="width:100%%;padding:10px 12px;line-height:1.45">%s</textarea>' % (k, e(S("wa_t_" + k, t)))) if t else (
            '<div class="dim" style="font-size:12px">Same text as the receipt page; goes when “Send receipt on WhatsApp” is ticked.</div>')
        kinds += '<div style="border-top:1px solid var(--line);padding-top:12px"><label class="chk"><input type="checkbox" name="wa_on_%s" value="1"%s><b>%s</b></label>%s</div>' % (
            k, " checked" if S("wa_on_" + k) == "1" else "", e(label), tpl)
    kinds += "".join('<div style="border-top:1px solid var(--line);padding-top:12px;display:flex;flex-direction:column;gap:8px"><b>%s</b>'
                     '<textarea name="wa_t_%s" rows="7" style="width:100%%;padding:10px 12px;line-height:1.45">%s</textarea></div>' % (
                         e(label), k, e(S("wa_t_" + k, MSG.joined(k)))) for k, label in MANUAL)
    kinds += ('<div style="border-top:1px solid var(--line);padding-top:12px;display:flex;flex-direction:column;gap:10px">'
              '<label class="chk"><input type="checkbox" name="wa_on_staff" value="1"%s><b>Staff late notice</b></label>'
              '<div class="dim" style="font-size:12px">Goes to the staff member (number on the Staff &amp; Trainers page) when they come late. '
              'In the texts: {name} first name, {date}, {minutes} late, {shift} start time, {n} which late this month, {hours} hours cut, {amount} rupees cut.</div>%s</div>') % (
        " checked" if S("wa_on_staff", "1") == "1" else "",
        "".join('<label>%s<textarea name="wa_t_staff_%s" rows="7" style="width:100%%;padding:10px 12px;line-height:1.45">%s</textarea></label>' % (e(l), k, e(S("wa_t_staff_" + k, t)))
                for k, l, t in STAFF_TEMPLATES))
    counts_ = dict(conn.execute("SELECT status, COUNT(*) FROM wa_queue WHERE substr(created_at,1,10)=? OR status='queued' GROUP BY status",
                                (M.today().isoformat(),)).fetchall())
    names = U.member_names(conn)
    rows = conn.execute("SELECT * FROM wa_queue ORDER BY status='queued' DESC, id DESC LIMIT 150").fetchall()
    pill = {"queued": "p-warn", "sent": "p-ok", "failed": "p-bad", "skipped": ""}
    trs = "".join('<tr><td class="dim">%s</td><td>%s</td><td>%s</td><td class="dim" style="white-space:normal;min-width:240px;max-width:420px">%s</td><td><span class="pill %s">%s</span> <span class="dim" style="font-size:12px">%s</span></td></tr>' % (
        e((r["sent_at"] or r["created_at"] or "")[:16]), e(LABEL.get(r["kind"], r["kind"].title())),
        ('<a href="/m?id=%d">%s</a>' % (r["client_id"], e(U.nice(names.get(str(r["client_id"]), ""))))) if r["client_id"] else "+" + e(r["phone"]),
        e(r["text"][:110] + ("…" if len(r["text"]) > 110 else "")), pill.get(r["status"], ""), r["status"].title(), e(r["error"] or ""))
        for r in rows)
    body = """<div class="two"><div class="panel" style="display:flex;flex-direction:column;gap:14px"><div class="ph" style="margin:0"><h2>Gym WhatsApp number</h2></div>%s
<div class="warn" style="margin:0">Use a <b>separate SIM</b>, never the gym's main number. This is not WhatsApp's official API, so WhatsApp can block a number
that sends too much. Keep the daily limit low. Members who reply <b>STOP</b> are never messaged again.</div></div>
<div class="panel" style="display:flex;flex-direction:column;gap:10px"><div class="ph" style="margin:0"><h2>Today</h2></div>
<div class="kpis" style="grid-template-columns:repeat(3,minmax(0,1fr))"><div class="kpi"><div class="l">Sent</div><div class="v">%d</div><div class="s">limit %s a day</div></div>
<div class="kpi"><div class="l">Waiting</div><div class="v">%d</div><div class="s">reminders: 1 every 1-3 min</div></div>
<div class="kpi"><div class="l">Failed</div><div class="v">%d</div><div class="s">see list</div></div></div>
<form method="post" action="/whatsapp/save" style="display:flex;gap:8px;flex-wrap:wrap;margin:0"><button class="btn sm" name="do" value="plan">Plan today's reminders now</button>
<button class="btn sm" name="do" value="clear" onclick="return confirm('Remove every waiting message?')">Remove waiting</button></form>
<form method="post" action="/whatsapp/save" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin:0"><label style="flex:1 1 160px">Test message to<input name="test_phone" inputmode="numeric" placeholder="your 10-digit number"></label>
<button class="btn sm" name="do" value="test">Send test</button></form></div></div>
<form class="panel" method="post" action="/whatsapp/save" style="display:flex;flex-direction:column;gap:12px"><div class="ph" style="margin:0"><h2>Automatic messages</h2>
<span class="pill %s">%s</span></div>
<label class="chk"><input type="checkbox" name="wa_auto" value="1"%s><b>Send automatically</b> (off = nothing is sent; the one-tap WhatsApp buttons still work)</label>
<div class="grid"><label>Messages a day (max)<input name="wa_cap" value="%s" inputmode="numeric"></label><label>Send from (hour, 24h)<input name="wa_from" value="%s" inputmode="numeric"></label>
<label>Until (hour, 24h)<input name="wa_to" value="%s" inputmode="numeric"></label><label>Plan reminders at (hour)<input name="wa_plan_hour" value="%s" inputmode="numeric"></label>
<label>“Ending soon” days before<input name="wa_days_before" value="%s" inputmode="numeric"></label></div>
<p class="dim" style="margin:0;font-size:12px">In the texts: {name} member's name, {date} end date, {amount} amount, {link} joining form link.
Each message has a few versions separated by a line with only <b>---</b>; a different one goes each time. Add or remove versions freely.</p>%s
<button class="btn red" name="do" value="save" style="align-self:flex-start">Save</button></form>
<div class="panel"><div class="ph"><h2>Messages</h2><span class="dim" style="font-size:12px">Replied STOP: %d</span></div><div class="tw"><table>
<tr><th>When</th><th>Type</th><th>To</th><th>Message</th><th>Status</th></tr>%s</table></div></div>""" % (
        conn_html, counts_.get("sent", 0), e(S("wa_cap", "40")), counts_.get("queued", 0), counts_.get("failed", 0),
        "p-ok" if auto else "", "ON" if auto else "OFF", " checked" if auto else "",
        e(S("wa_cap", "40")), e(S("wa_from", "9")), e(S("wa_to", "20")), e(S("wa_plan_hour", "10")), e(S("wa_days_before", "3")),
        kinds, len(optouts(conn)), trs or '<tr><td colspan="5" class="dim">No messages yet.</td></tr>')
    return U.shell("WhatsApp", "/whatsapp", body, sub="Automatic reminders from the gym's separate WhatsApp number",
                   msg=q.get("m", ""), cnt=U.counts(conn, sn))


def _int(v, lo, hi, dflt):
    try:
        return str(min(hi, max(lo, int(str(v).strip()))))
    except ValueError:
        return str(dflt)


def save(conn, f):
    do = f.get("do", "save")
    if do == "logout":
        res = logout()
        return "Number unlinked. A new QR will appear." if res.get("ok") else "Could not unlink: %s" % res.get("error", "")
    if do == "plan":
        n = plan(conn)
        return "%d reminders queued for today." % n
    if do == "clear":
        n = conn.execute("UPDATE wa_queue SET status='skipped', error='removed' WHERE status='queued'").rowcount
        return "%d waiting messages removed." % n
    if do == "test":
        ok = enqueue(conn, "test", 0, f.get("test_phone"), "Test message from the House of Strength app. ✅", M.stamp())
        return "Test is on its way; it reaches the phone in a few seconds." if ok else "Enter a valid 10-digit number."
    M.set_setting(conn, "wa_auto", "1" if f.get("wa_auto") == "1" else "0")
    M.set_setting(conn, "wa_cap", _int(f.get("wa_cap"), 1, 200, 40))
    M.set_setting(conn, "wa_from", _int(f.get("wa_from"), 0, 23, 9))
    M.set_setting(conn, "wa_to", _int(f.get("wa_to"), 1, 24, 20))
    M.set_setting(conn, "wa_plan_hour", _int(f.get("wa_plan_hour"), 0, 23, 10))
    M.set_setting(conn, "wa_days_before", _int(f.get("wa_days_before"), 1, 15, 3))
    for k, _, t, _ in KINDS:
        M.set_setting(conn, "wa_on_" + k, "1" if f.get("wa_on_" + k) == "1" else "0")
        if t and (f.get("wa_t_" + k) or "").strip():
            M.set_setting(conn, "wa_t_" + k, f["wa_t_" + k].strip()[:4000])
    M.set_setting(conn, "wa_on_staff", "1" if f.get("wa_on_staff") == "1" else "0")
    for k, _, _ in STAFF_TEMPLATES:
        if (f.get("wa_t_staff_" + k) or "").strip():
            M.set_setting(conn, "wa_t_staff_" + k, f["wa_t_staff_" + k].strip()[:4000])
    for k, _ in MANUAL:
        if (f.get("wa_t_" + k) or "").strip():
            M.set_setting(conn, "wa_t_" + k, f["wa_t_" + k].strip()[:4000])
    load(conn)
    _wake.set()
    return "WhatsApp settings saved. Automatic sending is %s." % ("ON" if f.get("wa_auto") == "1" else "OFF")
