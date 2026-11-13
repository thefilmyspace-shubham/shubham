"""Members, renewals and expiry -> door sync for the House of Strength server.

Kept apart from the device protocol in adms_server.py. Everything here works
on an open sqlite3 connection; the HTTP handler owns locking and auth.

Rules that protect people from being locked out by mistake:
  * Only IDs in the members table below STAFF_FROM are ever blocked
    (staff and admin IDs 10001+ never are).
  * A member is blocked only when the server holds their fingerprint backup.
  * Blocking waits GRACE days after expiry.
  * Automatic sync is OFF until someone switches it on.
"""
import csv
import datetime
import html
import io
import re

STAFF_FROM = 10000

SCHEMA = """
CREATE TABLE IF NOT EXISTS members (
    client_id INTEGER PRIMARY KEY, name TEXT, phone TEXT, gender TEXT,
    registration TEXT, package TEXT, expiry TEXT, notes TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY, client_id INTEGER, paid_on TEXT, amount REAL,
    mode TEXT, package TEXT, start TEXT, expiry TEXT, note TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS blocks (
    sn TEXT, pin TEXT, blocked_at TEXT, reason TEXT, PRIMARY KEY (sn, pin)
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
"""

PACKAGES = [  # label, days
    ("1 Week", 7), ("2 Week", 14), ("20 Days", 20), ("1 Month", 30), ("2 Months", 60),
    ("3 Months", 90), ("6 Months", 180), ("1 Year", 365),
    ("1 Month + PT", 30), ("3 Months + PT", 90),
]

e = html.escape


def today():
    return datetime.date.today()


def stamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_date(s):
    """'13-11-2026', '13/11/2026', '2026-11-13' -> date, else None."""
    s = (s or "").strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%y", "%d/%m/%y"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def iso(d):
    return d.isoformat() if d else ""


def show(d_iso):
    d = parse_date(d_iso)
    return d.strftime("%d-%m-%Y") if d else ""


def init(conn):
    conn.executescript(SCHEMA)
    conn.execute("INSERT OR IGNORE INTO settings VALUES ('grace_days', '3')")
    conn.execute("INSERT OR IGNORE INTO settings VALUES ('auto_sync', '0')")


def setting(conn, key, default=""):
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def set_setting(conn, key, value):
    conn.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (key, str(value)))


def default_sn(conn):
    row = conn.execute("SELECT sn FROM devices ORDER BY last_seen DESC LIMIT 1").fetchone()
    return row[0] if row else ""


# ---------------- import ----------------

def import_csv(conn, text):
    """Upsert members from the CSV made from the old software's client list."""
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    added = updated = skipped = 0
    for r in reader:
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        cid = r.get("client_id") or r.get("client id") or ""
        if not cid.isdigit():
            skipped += 1
            continue
        exp = parse_date(r.get("expiry") or r.get("expiration"))
        reg = parse_date(r.get("registration"))
        exists = conn.execute("SELECT 1 FROM members WHERE client_id=?", (int(cid),)).fetchone()
        conn.execute(
            "INSERT INTO members (client_id, name, phone, gender, registration, package, expiry, notes, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(client_id) DO UPDATE SET name=excluded.name, "
            "phone=excluded.phone, gender=excluded.gender, registration=excluded.registration, "
            "package=excluded.package, expiry=excluded.expiry, updated_at=excluded.updated_at",
            (int(cid), r.get("name") or r.get("client name", ""), r.get("phone") or r.get("number", ""),
             r.get("gender", ""), iso(reg), r.get("package", ""), iso(exp),
             r.get("all_packages", ""), stamp()),
        )
        if exists:
            updated += 1
        else:
            added += 1
    return added, updated, skipped


# ---------------- machine state ----------------

def machine_names(conn, sn):
    """pin -> name for every user the machine has reported."""
    out = {}
    for row in conn.execute("SELECT pin, payload FROM records WHERE sn=? AND kind='USER'", (sn,)):
        m = re.search(r"(?:^|\t)Name=([^\t]*)", row[1])
        out[row[0]] = m.group(1) if m else ""
    return out


def fp_pins(conn, sn):
    return {r[0] for r in conn.execute(
        "SELECT DISTINCT pin FROM records WHERE sn=? AND kind IN ('FP','BIODATA')", (sn,))}


def blocked_pins(conn, sn):
    return {r[0] for r in conn.execute("SELECT pin FROM blocks WHERE sn=?", (sn,))}


def queue(conn, sn, cmd):
    conn.execute("INSERT INTO commands (sn, cmd, created_at) VALUES (?,?,?)", (sn, cmd, stamp()))


def block(conn, sn, pin, reason="manual"):
    pin = str(pin)
    if int(pin) >= STAFF_FROM and reason != "manual":
        return False, "Staff ID %s is never blocked automatically." % pin
    has_user = conn.execute(
        "SELECT 1 FROM records WHERE sn=? AND pin=? AND kind='USER'", (sn, pin)).fetchone()
    has_fp = conn.execute(
        "SELECT 1 FROM records WHERE sn=? AND pin=? AND kind IN ('FP','BIODATA')", (sn, pin)).fetchone()
    if not has_user or not has_fp:
        return False, "Not blocked: no fingerprint backup of %s on the server." % pin
    if conn.execute("SELECT 1 FROM blocks WHERE sn=? AND pin=?", (sn, pin)).fetchone():
        return False, "%s is already blocked." % pin
    queue(conn, sn, "DATA DELETE USERINFO PIN=%s" % pin)
    conn.execute("INSERT OR REPLACE INTO blocks VALUES (?,?,?,?)", (sn, pin, stamp(), reason))
    return True, "Blocked %s (backup kept)." % pin


def unblock(conn, sn, pin):
    pin = str(pin)
    rows = conn.execute(
        "SELECT kind, payload FROM records WHERE sn=? AND pin=? AND kind IN ('USER','FP','BIODATA') "
        "ORDER BY CASE kind WHEN 'USER' THEN 0 ELSE 1 END", (sn, pin)).fetchall()
    if not rows:
        return False, "No backup for %s on the server." % pin
    table = {"USER": "USERINFO", "FP": "FINGERTMP", "BIODATA": "BIODATA"}
    for kind, payload in rows:
        queue(conn, sn, "DATA UPDATE %s %s" % (table[kind], payload))
    conn.execute("DELETE FROM blocks WHERE sn=? AND pin=?", (sn, pin))
    return True, "Restored %s to the machine (%d records)." % (pin, len(rows))


# ---------------- sync ----------------

def sync_plan(conn, sn):
    grace = int(setting(conn, "grace_days", "3") or 3)
    cutoff = today() - datetime.timedelta(days=grace)
    names = machine_names(conn, sn)
    fps = fp_pins(conn, sn)
    blocked = blocked_pins(conn, sn)
    to_block, no_backup, to_unblock = [], [], []
    for m in conn.execute("SELECT client_id, name, expiry FROM members WHERE client_id < ?", (STAFF_FROM,)):
        pin = str(m[0])
        exp = parse_date(m[2])
        if exp is None:
            continue
        if exp < cutoff and pin in names and pin not in blocked:
            (to_block if pin in fps else no_backup).append((m[0], m[1], m[2]))
        elif exp >= today() and pin in blocked:
            to_unblock.append((m[0], m[1], m[2]))
    return {"grace": grace, "cutoff": cutoff, "block": to_block, "no_backup": no_backup,
            "unblock": to_unblock}


def run_sync(conn, sn):
    plan = sync_plan(conn, sn)
    done_b = sum(1 for m in plan["block"] if block(conn, sn, m[0], "expired")[0])
    done_u = sum(1 for m in plan["unblock"] if unblock(conn, sn, m[0])[0])
    set_setting(conn, "last_sync", "%s: blocked %d, restored %d" % (stamp(), done_b, done_u))
    return done_b, done_u


# ---------------- add / renew ----------------

def save_member(conn, sn, f):
    cid = (f.get("client_id") or "").strip()
    if not cid.isdigit():
        return False, "Client ID must be a number (the Biometric ID)."
    cid = int(cid)
    old = conn.execute("SELECT * FROM members WHERE client_id=?", (cid,)).fetchone()
    name = (f.get("name") or (old["name"] if old else "")).strip()
    if not name:
        return False, "Name is required."
    phone = (f.get("phone") or (old["phone"] if old else "")).strip()
    gender = f.get("gender") or (old["gender"] if old else "")
    msg = []
    expiry = old["expiry"] if old else ""
    package = old["package"] if old else ""
    days = (f.get("days") or "").strip()
    if days.isdigit() and int(days) > 0:
        start = parse_date(f.get("start")) or today()
        old_exp = parse_date(expiry)
        # renewing before expiry continues from the old end date
        if old_exp and old_exp >= start and f.get("continue") == "1":
            start = old_exp + datetime.timedelta(days=1)
        new_exp = start + datetime.timedelta(days=int(days) - 1)
        package = f.get("package") or "%s days" % days
        expiry = iso(new_exp)
        amount = float(f.get("amount") or 0)
        conn.execute(
            "INSERT INTO payments (client_id, paid_on, amount, mode, package, start, expiry, note, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (cid, iso(today()), amount, f.get("mode", ""), package, iso(start), expiry,
             f.get("note", ""), stamp()))
        msg.append("Membership %s → %s." % (start.strftime("%d-%m-%Y"), new_exp.strftime("%d-%m-%Y")))
    conn.execute(
        "INSERT INTO members (client_id, name, phone, gender, registration, package, expiry, notes, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(client_id) DO UPDATE SET name=excluded.name, "
        "phone=excluded.phone, gender=excluded.gender, package=excluded.package, "
        "expiry=excluded.expiry, updated_at=excluded.updated_at",
        (cid, name, phone, gender, iso(today()) if not old else old["registration"], package, expiry,
         old["notes"] if old else "", stamp()))
    exp = parse_date(expiry)
    if sn and exp and exp >= today() and str(cid) in blocked_pins(conn, sn):
        ok, m = unblock(conn, sn, cid)
        msg.append("Door: " + m)
    return True, "Saved %s (%d). %s" % (name, cid, " ".join(msg))


# ---------------- pages ----------------

CSS = """body{font-family:system-ui,sans-serif;background:#0b0b0c;color:#f4f4f5;margin:0}
header{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:12px 16px;background:#111113;border-bottom:1px solid #26262a}
header b{color:#ff5a5a;margin-right:12px}nav a{color:#c4c4cc;text-decoration:none;padding:10px 12px;border-radius:8px}
nav a.on{background:#d90b16;color:#fff}main{padding:16px;max-width:1300px}
h1{font-size:22px;margin:4px 0 12px}h2{font-size:17px;margin:22px 0 8px}
table{border-collapse:collapse;width:100%;font-size:13px;display:block;overflow-x:auto}
td,th{border:1px solid #2a2a2e;padding:6px 8px;text-align:left;white-space:nowrap}th{background:#1d1d20}
form.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0}
input,select,button,textarea{min-height:40px;padding:0 10px;border-radius:8px;border:1px solid #333;background:#151517;color:#fff;font:inherit}
button{background:#d90b16;border:0;font-weight:600;cursor:pointer}button.ghost{background:#26262a}
a{color:#ff7a7a}.msg{background:#1f2a1a;padding:10px;border-radius:8px}.warn{background:#2a0a0c;padding:10px;border-radius:8px}
.tag{padding:2px 8px;border-radius:6px;font-size:12px;font-weight:700}.ok{background:#0f2a1a;color:#4ade80}
.bad{background:#2a0a0c;color:#ff7a7a}.mid{background:#2a220a;color:#f5c542}.dim{color:#a1a1aa}
.cards{display:flex;flex-wrap:wrap;gap:10px}.card{background:#151517;border:1px solid #26262a;border-radius:12px;padding:12px 16px;min-width:140px}
.card b{display:block;font-size:26px}label{display:flex;flex-direction:column;gap:4px;font-size:13px;color:#c4c4cc}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;max-width:900px}"""


def layout(title, active, body, msg=""):
    links = [("/", "Gate"), ("/members", "Members"), ("/member", "Add / Renew"), ("/sync", "Door sync")]
    nav = "".join('<a href="%s"%s>%s</a>' % (h, ' class="on"' if h == active else "", t) for h, t in links)
    return ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" '
            'content="width=device-width,initial-scale=1"><title>%s</title><style>%s</style></head>'
            '<body><header><b>HOUSE OF STRENGTH</b><nav>%s</nav></header><main>%s%s</main></body></html>'
            % (e(title), CSS, nav, '<p class="msg">%s</p>' % e(msg) if msg else "", body))


def status_of(exp_iso):
    exp = parse_date(exp_iso)
    if not exp:
        return "—", "dim"
    left = (exp - today()).days
    if left < 0:
        return "Expired %dd" % -left, "bad"
    if left <= 7:
        return "%dd left" % left, "mid"
    return "Active", "ok"


def members_page(conn, sn, q, msg=""):
    f = q.get("f", "all")
    term = (q.get("q") or "").strip().lower()
    names = machine_names(conn, sn)
    blocked = blocked_pins(conn, sn)
    fps = fp_pins(conn, sn)
    rows = conn.execute("SELECT * FROM members ORDER BY client_id DESC").fetchall()
    t = today()
    counts = {"all": len(rows), "active": 0, "soon": 0, "expired": 0,
              "expired_on_machine": 0, "active_missing": 0}
    out = []
    for m in rows:
        pin = str(m["client_id"])
        exp = parse_date(m["expiry"])
        active = bool(exp and exp >= t)
        soon = bool(exp and t <= exp <= t + datetime.timedelta(days=7))
        on_machine = pin in names and pin not in blocked
        counts["active"] += active
        counts["soon"] += soon
        counts["expired"] += not active
        counts["expired_on_machine"] += (not active) and on_machine
        counts["active_missing"] += active and pin not in names
        keep = {"all": True, "active": active, "soon": soon, "expired": not active,
                "expired_on_machine": (not active) and on_machine,
                "active_missing": active and pin not in names}.get(f, True)
        if term and term not in ("%s %s %s" % (pin, m["name"], m["phone"])).lower():
            keep = False
        if not keep:
            continue
        st, cls = status_of(m["expiry"])
        if pin in blocked:
            door = '<span class="tag bad">Blocked</span>'
        elif pin in names:
            door = '<span class="tag ok">On machine</span>' + ("" if pin in fps else ' <span class="tag mid">no FP backup</span>')
        else:
            door = '<span class="dim">Not on machine</span>'
        out.append("<tr><td>%s</td><td><a href=\"/member?id=%s\">%s</a>%s</td><td>%s</td><td>%s</td>"
                   "<td>%s</td><td><span class=\"tag %s\">%s</span></td><td>%s</td></tr>" % (
                       pin, pin, e(m["name"] or ""),
                       ('<br><span class="dim">machine: %s</span>' % e(names[pin])) if pin in names and names[pin] and names[pin].lower() != (m["name"] or "").lower() else "",
                       e(m["phone"] or ""), e(m["package"] or ""), show(m["expiry"]), cls, st, door))
    labels = [("all", "All"), ("active", "Active"), ("soon", "Expiring ≤7 days"), ("expired", "Expired"),
              ("expired_on_machine", "Expired but door opens"), ("active_missing", "Active, not on machine")]
    cards = "".join('<a class="card" style="text-decoration:none;color:inherit;%s" href="/members?f=%s"><span class="dim">%s</span><b>%d</b></a>'
                    % ("border-color:#d90b16" if k == f else "", k, t_, counts[k]) for k, t_ in labels)
    body = """<h1>Members</h1><div class="cards">%s</div>
<form class="row" method="get" action="/members"><input type="hidden" name="f" value="%s">
<input name="q" value="%s" placeholder="Search ID, name or phone" size="30"><button>Search</button>
<a href="/member">+ Add member</a></form>
<table><tr><th>ID</th><th>Name</th><th>Phone</th><th>Package</th><th>Expiry</th><th>Status</th><th>Door</th></tr>%s</table>
<h2>Import from old software</h2>
<p class="dim">CSV with columns client_id, name, phone, gender, registration, package, expiry. Existing IDs are updated.</p>
<input type="file" id="csv" accept=".csv,text/csv"> <button type="button" onclick="up()">Import</button> <span id="st"></span>
<script>function up(){var f=document.getElementById('csv').files[0];if(!f){return}
var s=document.getElementById('st');s.textContent='Uploading…';f.text().then(function(t){
return fetch('/members/import',{method:'POST',headers:{'Content-Type':'text/csv'},body:t})}).then(function(r){return r.text()})
.then(function(t){s.textContent=t;setTimeout(function(){location.href='/members'},1500)})}</script>""" % (
        cards, e(f), e(term), "".join(out) or '<tr><td colspan="7">No members</td></tr>')
    return layout("Members", "/members", body, msg)


def member_page(conn, sn, q, msg=""):
    cid = q.get("id", "")
    m = conn.execute("SELECT * FROM members WHERE client_id=?", (cid,)).fetchone() if cid.isdigit() else None
    names = machine_names(conn, sn)
    v = lambda k: e(str((m[k] if m else "") or ""))
    opts = "".join('<option value="%d" data-label="%s">%s (%d days)</option>' % (d, e(l), e(l), d) for l, d in PACKAGES)
    pays = ""
    if m:
        rows = conn.execute("SELECT * FROM payments WHERE client_id=? ORDER BY id DESC", (m["client_id"],)).fetchall()
        pays = "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s → %s</td><td>%s</td></tr>" % (
            show(p["paid_on"]), e(p["package"] or ""), "%g" % (p["amount"] or 0), show(p["start"]), show(p["expiry"]),
            e(p["mode"] or "")) for p in rows)
    st, cls = status_of(m["expiry"]) if m else ("New member", "dim")
    pin = cid
    door = ""
    if m and sn:
        blocked = pin in blocked_pins(conn, sn)
        state = "Blocked" if blocked else ("On machine" if pin in names else "Not on machine")
        door = """<h2>Door</h2><p>%s</p><form class="row" method="post" action="/member/door">
<input type="hidden" name="id" value="%s"><button name="do" value="%s">%s</button></form>""" % (
            e(state), e(pin), "unblock" if blocked else "block", "Unblock now" if blocked else "Block now")
    body = """<h1>%s</h1>%s
<form method="post" action="/member/save"><div class="grid">
<label>Client ID / Biometric ID<input name="client_id" value="%s" required %s></label>
<label>Name<input name="name" value="%s" required></label>
<label>Phone<input name="phone" value="%s"></label>
<label>Gender<select name="gender"><option>%s</option><option>Male</option><option>Female</option></select></label>
</div>
<h2>New / renew membership <span class="dim">(leave package empty to only edit details)</span></h2>
<div class="grid">
<label>Package<select name="days" onchange="this.form.package.value=this.options[this.selectedIndex].dataset.label||''">
<option value="">— no change —</option>%s</select></label>
<input type="hidden" name="package">
<label>Start date<input type="date" name="start" value="%s"></label>
<label>Amount (₹)<input name="amount" inputmode="decimal"></label>
<label>Paid by<select name="mode"><option>Cash</option><option>Online</option><option>UPI</option><option>Card</option></select></label>
<label style="flex-direction:row;align-items:center"><input type="checkbox" name="continue" value="1" checked style="min-height:auto"> Continue from current end date if renewing early</label>
</div><p><button>Save</button></p></form>
%s
<h2>Payments</h2><table><tr><th>Paid on</th><th>Package</th><th>Amount</th><th>Period</th><th>Mode</th></tr>%s</table>""" % (
        e(m["name"]) if m else "Add member",
        '<p>Status: <span class="tag %s">%s</span> · Expiry %s · Package %s</p>' % (cls, e(st), show(m["expiry"]), v("package")) if m else
        '<p class="dim">Enroll the finger on the gate machine first with the same ID, then save here.</p>',
        v("client_id"), "readonly" if m else "", v("name"), v("phone"), v("gender"), opts, iso(today()),
        door, pays or '<tr><td colspan="5">—</td></tr>')
    return layout("Member", "/member", body, msg)


def sync_page(conn, sn, msg=""):
    p = sync_plan(conn, sn)
    auto = setting(conn, "auto_sync", "0") == "1"
    rows = lambda lst: "".join("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (m[0], e(m[1] or ""), show(m[2])) for m in lst) or '<tr><td colspan="3">—</td></tr>'
    body = """<h1>Door sync</h1>
<p>Members whose membership ended more than <b>%d days</b> ago (before %s) are removed from the gate machine; their
fingerprint stays on the server and is put back the moment they renew. Staff IDs %d+ are never touched.</p>
<p>Automatic sync (every 30 min): <span class="tag %s">%s</span> · Last run: %s</p>
<form class="row" method="post" action="/sync"><label>Grace days<input name="grace" value="%d" size="3"></label>
<button name="do" value="save" class="ghost">Save grace</button>
<button name="do" value="run">Run sync now</button>
<button name="do" value="%s" class="ghost">%s automatic sync</button></form>
%s
<h2>Will be blocked (%d)</h2><table><tr><th>ID</th><th>Name</th><th>Expired</th></tr>%s</table>
<h2>Expired but no fingerprint backup — not blocked (%d)</h2><table><tr><th>ID</th><th>Name</th><th>Expired</th></tr>%s</table>
<h2>Will be restored, renewed (%d)</h2><table><tr><th>ID</th><th>Name</th><th>Expiry</th></tr>%s</table>""" % (
        p["grace"], p["cutoff"].strftime("%d-%m-%Y"), STAFF_FROM, "ok" if auto else "bad",
        "ON" if auto else "OFF", e(setting(conn, "last_sync", "never")), p["grace"],
        "auto_off" if auto else "auto_on", "Turn off" if auto else "Turn on",
        "" if sn else '<p class="warn">No gate machine connected yet.</p>',
        len(p["block"]), rows(p["block"]), len(p["no_backup"]), rows(p["no_backup"]),
        len(p["unblock"]), rows(p["unblock"]))
    return layout("Door sync", "/sync", body, msg)
