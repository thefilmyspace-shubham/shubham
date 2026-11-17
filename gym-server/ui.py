"""House of Strength admin app: the screens from the approved design.

Part A: shell (sidebar + footer), Dashboard, Members, Member profile,
New bill, Receipt. Data helpers come from members.py (imported as M).
Every function takes an open sqlite3 connection; the HTTP handler owns
locking and auth.
"""
import csv
import datetime
import io
import re
from urllib.parse import quote, urlencode

import ai as AI
import auth as A
import gsheets as GS
import members as M
import staffhours as SH

e = M.e
STAFF_FROM = M.STAFF_FROM

PACKAGE_SEED = [  # name, days, price, kind, sessions
    ("1 Month", 30, 2500, "gym", 0), ("2 Months", 60, 4000, "gym", 0), ("3 Months", 90, 6500, "gym", 0),
    ("6 Months", 180, 10000, "gym", 0), ("1 Year", 365, 18000, "gym", 0), ("Couple", 365, 24000, "gym", 0),
    ("1 Week", 7, 700, "gym", 0), ("2 Week", 14, 1400, "gym", 0), ("3 Week", 21, 1250, "gym", 0),
    ("20 Day", 20, 1000, "gym", 0), ("1 Month PT", 30, 8000, "gym", 0), ("3 Months + PT", 90, 20000, "gym", 0),
    ("Monthly PT", 30, 8000, "pt", 30), ("3 Months PT", 90, 18000, "pt", 90), ("6 Months PT", 180, 48000, "pt", 180),
]
TRAINER_SEED = ("Abhishek Jat\nAbhishek Sharma\nArpit Sharma\nGoutam Panchal\nNav Sharma\nPratham Solanki\n"
                "Pratik Choudhary\nSaniya Khan\nShraddha Soni\nShubham Chourasia\nSuraj Singh Goud\nVijay Mali")
PAY_COLS = {"invoice": "TEXT", "list_price": "REAL", "discount": "REAL", "admission": "REAL", "gst": "REAL",
            "payable": "REAL", "balance": "REAL", "trainer": "TEXT", "kind": "TEXT", "created_by": "TEXT",
            "next_due": "TEXT"}


# ---------------- setup ----------------

def init(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS packages (
        id INTEGER PRIMARY KEY, name TEXT UNIQUE, days INTEGER, price REAL, kind TEXT,
        sessions INTEGER, active INTEGER DEFAULT 1, sort INTEGER)""")
    if not conn.execute("SELECT 1 FROM packages LIMIT 1").fetchone():
        for i, (n, d, p, k, s) in enumerate(PACKAGE_SEED):
            conn.execute("INSERT INTO packages (name, days, price, kind, sessions, sort) VALUES (?,?,?,?,?,?)",
                         (n, d, p, k, s, i))
    have = {r[1] for r in conn.execute("PRAGMA table_info(payments)")}
    for col, typ in PAY_COLS.items():
        if col not in have:
            conn.execute("ALTER TABLE payments ADD COLUMN %s %s" % (col, typ))
    conn.execute("INSERT OR IGNORE INTO settings VALUES ('next_invoice', '1242')")
    conn.execute("INSERT OR IGNORE INTO settings VALUES ('invoice_prefix', 'HOS-')")
    conn.execute("INSERT OR IGNORE INTO settings VALUES ('trainers', ?)", (TRAINER_SEED,))
    conn.execute("INSERT OR IGNORE INTO settings VALUES ('gym_phone', '')")
    conn.execute("INSERT OR IGNORE INTO settings VALUES ('gym_address', '4th Floor, Gayatri Mall, Subhash Marg, Ratlam')")


# ---------------- helpers ----------------

def inr(v):
    """Indian digit grouping: 123800 -> 1,23,800."""
    n = int(round(abs(v or 0)))
    s = str(n)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = ",".join([head[max(0, i - 2):i] for i in range(len(head), 0, -2)][::-1])
        s = head + "," + tail
    return ("-" if (v or 0) < 0 else "") + s


def money(v):
    return "₹" + inr(v)


def initials(name):
    parts = [p for p in re.split(r"\s+", (name or "").strip()) if p and p[0].isalpha()]
    return ((parts[0][0] + (parts[1][0] if len(parts) > 1 else "")) if parts else "?").upper()


def nice(name):
    return " ".join(w[:1].upper() + w[1:] for w in (name or "").split())


def short_date(d_iso):
    d = M.parse_date(d_iso)
    return d.strftime("%d %b %Y") if d else "—"


def member_id(cid):
    return "HOS-%04d" % int(cid)


def is_member(pin):
    return str(pin).isdigit() and int(pin) < STAFF_FROM


def trainers(conn):
    return [t.strip() for t in M.setting(conn, "trainers", "").splitlines() if t.strip()]


def last_visits(conn, sn):
    """pin -> last punch date (members only)."""
    out = {}
    for pin, ts in conn.execute("SELECT pin, MAX(substr(ts,1,10)) FROM punches WHERE sn=? GROUP BY pin", (sn,)):
        out[pin] = M.parse_date(ts)
    return out


def tracking_start(conn):
    row = conn.execute("SELECT MIN(substr(ts,1,10)) FROM punches").fetchone()
    return M.parse_date(row[0]) if row and row[0] else M.today()


def absent_list(conn, sn, min_days):
    t = M.today()
    lv = last_visits(conn, sn)
    start = tracking_start(conn)
    out = []
    for m in conn.execute("SELECT * FROM members WHERE expiry >= ?", (M.iso(t),)):
        last = lv.get(str(m["client_id"]))
        days = (t - last).days if last else (t - start).days
        if days >= min_days:
            out.append((days, last, m))
    out.sort(key=lambda x: -x[0])
    return out


def counts(conn, sn):
    t = M.today()
    c = {}
    c["renewals"] = conn.execute("SELECT COUNT(*) FROM members WHERE expiry BETWEEN ? AND ?",
                                 (M.iso(t), M.iso(t + datetime.timedelta(days=7)))).fetchone()[0]
    c["pending"] = conn.execute("SELECT COUNT(*) FROM members WHERE pending > 0").fetchone()[0]
    c["absent"] = len(absent_list(conn, sn, 7)) if sn else 0
    init_approvals(conn)
    c["approvals"] = conn.execute("SELECT COUNT(*) FROM approvals WHERE status='pending'%s" % (
        "" if A.is_admin() else " AND requested_by=?"), () if A.is_admin() else (staff_name(),)).fetchone()[0]
    try:
        c["joinings"] = conn.execute("SELECT COUNT(*) FROM joinings WHERE status='new'").fetchone()[0]
    except Exception:
        c["joinings"] = 0
    return c


def wa(phone, text):
    return M.wa_link(phone, text)


def phone_ok(m):
    """Admin sees every number; reception only members with a due (renewal soon/just missed, or money owed)."""
    if A.is_admin():
        return True
    if A.role() != "reception":
        return False
    if (m["pending"] or 0) > 0:
        return True
    d = M.parse_date(m["expiry"])
    return bool(d and -30 <= (d - M.today()).days <= 7)


def show_phone(m):
    p = m["phone"] or ""
    if phone_ok(m) or not p:
        return p
    return p[:2] + "XXX XXX" + p[-2:] if len(p) >= 6 else "hidden"


def call_btn(m):
    return ('<a class="ibtn" href="tel:%s" aria-label="Call">%s</a>' % (e(m["phone"] or ""), icon("phone", 16))
            if phone_ok(m) and m["phone"] else "")


def admin_only(html_):
    return html_ if A.is_admin() else ""


def staff_name():
    return A.me().get("name") or "Admin"


# ---------------- icons (inline stroke svg) ----------------

def icon(name, size=18):
    p = {
        "dash": '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
        "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6"/><path d="M16 4.5a3.5 3.5 0 010 7M18 14c2 .7 3.5 2.6 3.5 6"/>',
        "bill": '<path d="M6 2h9l4 4v16H6z"/><path d="M15 2v4h4M9 12h7M9 16h7M9 8h3"/>',
        "finger": '<path d="M12 11v3a8 8 0 01-1.5 4.7"/><path d="M8.5 9.5a3.5 3.5 0 017 0V14a12 12 0 01-.8 4.3"/><path d="M5.5 16.5A12 12 0 006 14V9.5a6 6 0 0110.2-4.3"/><path d="M18.5 9.5V13"/>',
        "renew": '<path d="M20 11a8 8 0 00-14.3-4.9L4 8"/><path d="M4 3v5h5"/><path d="M4 13a8 8 0 0014.3 4.9L20 16"/><path d="M20 21v-5h-5"/>',
        "rupee": '<path d="M6 4h12M6 9h12M6 4h3a5 5 0 010 10H6l8 7"/>',
        "alert": '<circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 16.5v.5"/>',
        "chat": '<path d="M21 12a8.5 8.5 0 01-12.6 7.4L3 21l1.6-5.2A8.5 8.5 0 1121 12z"/>',
        "box": '<path d="M12 2l9 5v10l-9 5-9-5V7z"/><path d="M3 7l9 5 9-5M12 12v10"/>',
        "staff": '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/>',
        "chart": '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 6-7"/>',
        "gear": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.6 1.6 0 00-1.8-.3 1.6 1.6 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.6 1.6 0 00-1-1.5 1.6 1.6 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.6 1.6 0 00.3-1.8 1.6 1.6 0 00-1.5-1H3a2 2 0 110-4h.1a1.6 1.6 0 001.5-1 1.6 1.6 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.6 1.6 0 001.8.3H9a1.6 1.6 0 001-1.5V3a2 2 0 114 0v.1a1.6 1.6 0 001 1.5 1.6 1.6 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.6 1.6 0 00-.3 1.8V9a1.6 1.6 0 001.5 1H21a2 2 0 110 4h-.1a1.6 1.6 0 00-1.5 1z"/>',
        "search": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
        "plus": '<path d="M12 5v14M5 12h14"/>',
        "phone": '<path d="M22 16.9v3a2 2 0 01-2.2 2 19.8 19.8 0 01-8.6-3.1 19.5 19.5 0 01-6-6A19.8 19.8 0 012.1 4.2 2 2 0 014.1 2h3a2 2 0 012 1.7c.1 1 .4 1.9.7 2.8a2 2 0 01-.5 2.1L8 9.9a16 16 0 006 6l1.3-1.3a2 2 0 012.1-.5c.9.3 1.8.6 2.8.7a2 2 0 011.7 2z"/>',
        "edit": '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4z"/>',
        "door": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 018 0v4"/>',
        "server": '<rect x="3" y="4" width="18" height="6" rx="1"/><rect x="3" y="14" width="18" height="6" rx="1"/><path d="M7 7h.01M7 17h.01"/>',
        "down": '<path d="M12 3v12M7 10l5 5 5-5M4 21h16"/>',
        "logout": '<path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/>',
        "print": '<path d="M6 9V2h12v7M6 18H4a2 2 0 01-2-2v-5a2 2 0 012-2h16a2 2 0 012 2v5a2 2 0 01-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
    }[name]
    return ('<svg width="%d" height="%d" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%s</svg>' % (size, size, p))


# ---------------- shell ----------------

CSS = """
:root{--bg:#0a0a0a;--side:#111113;--card:#151517;--card2:#1d1d20;--line:#26262a;--red:#e10600;--red2:#ff4d4d;
--text:#f4f4f5;--muted:#a1a1aa;--ok:#4ade80;--okbg:#0f2a1a;--warn:#f5c542;--warnbg:#2a220a;--bad:#ff7a7a;--badbg:#2a0a0c;--blue:#5ab0ff;--bluebg:#0c2233}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,system-ui,sans-serif;font-size:14px}
a{color:var(--red2);text-decoration:none}a:hover{text-decoration:underline}
.app{display:flex;flex-wrap:wrap;min-height:100vh}
.side{flex:1 1 230px;max-width:100%;background:var(--side);border-right:1px solid var(--line);padding:18px 14px;display:flex;flex-direction:column;gap:4px}
.brand{display:flex;align-items:center;gap:10px;margin:0 4px 18px}.brand img{width:44px;height:44px;border-radius:8px;object-fit:cover}
.brand b{font-family:Oswald,sans-serif;font-size:19px;line-height:1.05;letter-spacing:.02em}.brand b span{color:var(--red2)}
.nav a{display:flex;align-items:center;gap:12px;min-height:42px;padding:0 12px;border-radius:10px;color:#c4c4cc;font-weight:500}
.nav a:hover{background:var(--card2);text-decoration:none}.nav a.on{background:var(--red);color:#fff}
.nav .badge{margin-left:auto;background:var(--badbg);color:var(--bad);border-radius:999px;padding:2px 8px;font-size:12px;font-weight:700}
.nav a.on .badge{background:#ffffff33;color:#fff}.navsec{margin:16px 12px 4px;color:#71717a;font-size:11px;letter-spacing:.1em;text-transform:uppercase}
.who{margin-top:auto;border-top:1px solid var(--line);padding:14px 6px 0;display:flex;align-items:center;gap:10px}
.av{width:38px;height:38px;border-radius:50%;background:var(--card2);border:1px solid var(--line);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;flex:0 0 auto}
.main{flex:999 1 600px;min-width:0;display:flex;flex-direction:column}
.top{display:flex;flex-wrap:wrap;gap:14px;align-items:center;justify-content:space-between;padding:22px 28px;border-bottom:1px solid var(--line)}
.top h1{font-family:Oswald,sans-serif;font-size:32px;font-weight:600;letter-spacing:.02em;margin:0;text-transform:uppercase}
.top .sub{color:var(--muted);margin-top:2px}.acts{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.search{display:flex;align-items:center;gap:8px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:0 12px;min-height:44px;min-width:260px;color:var(--muted)}
.search input{background:transparent;border:0;color:var(--text);outline:none;flex:1;min-height:42px;font:inherit}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:44px;padding:0 18px;border-radius:12px;border:1px solid var(--line);background:var(--card);color:var(--text);font-weight:600;font:600 14px Inter,sans-serif;cursor:pointer}
.btn:hover{text-decoration:none;border-color:#3a3a40}.btn.red{background:var(--red);border-color:var(--red);color:#fff}.btn.sm{min-height:36px;padding:0 12px;border-radius:9px;font-size:13px}
.ibtn{width:36px;height:36px;border-radius:9px;border:1px solid var(--line);background:var(--card2);color:var(--text);display:inline-flex;align-items:center;justify-content:center}
.ibtn.wa{color:var(--blue)}.content{padding:24px 28px;display:flex;flex-direction:column;gap:20px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px 20px;color:var(--text)}
.kpi.hot{background:var(--red);border-color:var(--red)}.kpi .l{color:#d4d4d8;font-size:13px}.kpi.hot .l,.kpi.hot .s{color:#ffe1e1}
.kpi .v{font-family:Oswald,sans-serif;font-size:40px;font-weight:600;line-height:1.15;margin:4px 0}.kpi .s{color:var(--muted);font-size:12px}
a.kpi:hover{text-decoration:none;border-color:#3a3a40}
.panel{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px}
.ph{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px}
.ph h2,.panel h2{font-family:Oswald,sans-serif;font-size:19px;font-weight:600;letter-spacing:.03em;margin:0;text-transform:uppercase}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:20px}
table{border-collapse:collapse;width:100%}.tw{overflow-x:auto}
th{color:var(--muted);font-size:11px;letter-spacing:.08em;text-transform:uppercase;text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:11px 12px;border-bottom:1px solid #1f1f23;white-space:nowrap}tr:last-child td{border-bottom:0}
.mem{display:flex;align-items:center;gap:10px;font-weight:600;color:var(--text)}.mem .av{width:34px;height:34px;font-size:12px}
.pill{display:inline-block;padding:3px 10px;border-radius:7px;font-size:12px;font-weight:700}
.p-ok{background:var(--bluebg);color:var(--blue)}.p-warn{background:var(--warnbg);color:var(--warn)}.p-bad{background:var(--badbg);color:var(--bad)}
.p-dim{background:var(--card2);color:var(--muted)}.p-green{background:var(--okbg);color:var(--ok)}
.tabs{display:flex;flex-wrap:wrap;gap:8px}.tabs a{padding:8px 14px;border-radius:999px;border:1px solid var(--line);color:#c4c4cc;font-weight:600;font-size:13px}
.tabs a.on{background:#fff;color:#111;border-color:#fff}.tabs a:hover{text-decoration:none}
.bars{display:flex;align-items:flex-end;gap:10px;height:190px;padding-top:24px}
.bar{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:6px;height:100%;min-width:18px}
.bar i{display:block;width:100%;max-width:38px;background:#3a3a40;border-radius:4px 4px 0 0}.bar i.r{background:var(--red)}
.bar b{font-size:11px;color:#d4d4d8;font-weight:500}.bar span{font-size:11px;color:var(--muted)}
.qa{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.qa a{background:var(--card2);border:1px solid var(--line);border-radius:12px;padding:16px;color:var(--text);font-weight:600;display:flex;flex-direction:column;gap:12px}
.qa a svg{color:var(--red2)}.qa a:hover{text-decoration:none;border-color:#3a3a40}
.msg{background:var(--okbg);color:#d1fadf;padding:12px 14px;border-radius:12px}.warn{background:var(--badbg);color:#ffd6d6;padding:12px 14px;border-radius:12px}
.dim{color:var(--muted)}.foot{margin-top:auto;padding:18px 28px;border-top:1px solid var(--line);color:#71717a;font-size:12px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}
.foot b{color:#a1a1aa}
label{display:flex;flex-direction:column;gap:6px;color:#c4c4cc;font-size:13px}
input,select,textarea{min-height:44px;padding:0 12px;border-radius:10px;border:1px solid var(--line);background:var(--card2);color:var(--text);font:14px Inter,sans-serif}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px}
.pk{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:12px}
.pk label{position:relative;background:var(--card2);border:1px solid var(--line);border-radius:12px;padding:14px 16px;cursor:pointer;gap:2px}
.pk input{position:absolute;opacity:0;min-height:0}.pk b{font-family:Oswald,sans-serif;font-size:17px;color:var(--text);text-transform:uppercase}
.pk .pr{font-family:Oswald,sans-serif;font-size:26px;font-weight:600;color:var(--text);margin-top:6px}
.pk label:has(input:checked){background:var(--red);border-color:var(--red)}.pk label:has(input:checked) span{color:#ffe1e1}
.sum{display:flex;flex-direction:column;gap:12px}.sum div{display:flex;justify-content:space-between;gap:10px;color:#d4d4d8}
.sum .t{border-top:1px solid var(--line);padding-top:14px;font-weight:700;color:var(--text)}
.chk{flex-direction:row;align-items:center;gap:10px;color:var(--text)}.chk input{min-height:auto;width:18px;height:18px;accent-color:var(--red)}
.heat{display:grid;grid-template-columns:repeat(15,minmax(0,1fr));gap:6px}.heat i{aspect-ratio:1;border-radius:5px;background:var(--card2)}.heat i.on{background:var(--red)}
.prog{height:6px;background:var(--card2);border-radius:3px;overflow:hidden;margin-top:12px;max-width:440px}.prog i{display:block;height:100%;background:var(--red)}
.hero{display:flex;flex-wrap:wrap;gap:22px;align-items:center}.hero .big{width:110px;height:110px;border-radius:16px;border:2px solid var(--red);background:var(--card2);display:flex;align-items:center;justify-content:center;font:600 40px Oswald,sans-serif}
.hero h2{font:600 30px Oswald,sans-serif;margin:0;text-transform:uppercase;letter-spacing:.02em}
.kv{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px 24px}.kv span{display:block;color:var(--muted);font-size:12px}.kv b{font-weight:600}
.cards{display:flex;flex-wrap:wrap;gap:10px}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 16px;min-width:140px;color:var(--text)}
.card b{display:block;font-size:26px}.tag{padding:2px 8px;border-radius:6px;font-size:12px;font-weight:700}.ok{background:var(--okbg);color:var(--ok)}
.bad{background:var(--badbg);color:var(--bad)}.mid{background:var(--warnbg);color:var(--warn)}
form.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0}button{font:600 14px Inter,sans-serif;min-height:42px;padding:0 16px;border-radius:10px;border:0;background:var(--red);color:#fff;cursor:pointer}
button.ghost{background:var(--card2);border:1px solid var(--line)}h1{font-family:Oswald,sans-serif}
.legacy table{font-size:13px}.legacy td,.legacy th{border:1px solid var(--line)}
@media print{.side,.top,.foot,.noprint{display:none!important}body,html{background:#fff;color:#000}.panel{border:0}}
"""

NAV = [
    ("/", "Dashboard", "dash", None), ("/members", "Members", "users", None), ("/bill", "New Bill", "bill", None),
    ("/attendance", "Attendance", "finger", None), ("/door", "Open gate", "door", None), ("/renewals", "Renewals", "renew", "renewals"),
    ("/pending", "Pending Payments", "rupee", "pending"), ("/absent", "Absent Members", "alert", "absent"),
    ("/joinings", "Joining forms", "users", "joinings"), ("/inquiries", "Inquiries", "chat", None), ("/approvals", "Approvals", "alert", "approvals"), ("/packages", "Packages", "box", None),
    ("/staff", "Staff & Trainers", "staff", None), ("/reports", "Reports", "chart", None), ("/expenses", "Expenses", "rupee", None),
    ("/assistant", "AI assistant", "chat", None),
]
SYSTEM = [("/users", "Staff logins", "staff"), ("/activity", "Activity log", "chart"), ("/whatsapp", "WhatsApp", "chat"),
          ("/sync", "Door sync", "door"),
          ("/gate", "Gate machine", "server"), ("/settings", "Settings", "gear"), ("/backup", "Backup", "down")]
TRAINER_NAV = [("/trainer", "My PT clients", "users", None), ("/approvals", "Leave / requests", "alert", "approvals")]


def shell(title, active, body, sub="", actions="", msg="", cnt=None, warn=""):
    cnt = cnt or {}
    links = []
    user = A.me()
    nav = NAV if A.is_admin() else (TRAINER_NAV if A.role() == "trainer" else
                                    [n for n in NAV if n[0].split("?")[0] in A.RECEPTION_PATHS])
    for href, label, ic, key in nav:
        badge = '<span class="badge">%d</span>' % cnt[key] if key and cnt.get(key) else ""
        links.append('<a href="%s"%s>%s<span>%s</span>%s</a>' % (href, ' class="on"' if href == active else "",
                                                                  icon(ic), label, badge))
    sys_links = "".join('<a href="%s"%s>%s<span>%s</span></a>' % (h, ' class="on"' if h == active else "", icon(i), l)
                        for h, l, i in SYSTEM) if A.is_admin() else ""
    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>%s · House of Strength</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>%s</style></head><body><div class="app">
<aside class="side"><div class="brand"><img src="/logo.jpg" alt=""><b>HOUSE OF<br><span>STRENGTH</span></b></div>
<nav class="nav">%s%s%s</nav>
<div class="who"><div class="av">%s</div><div style="flex:1;min-width:0"><b>%s</b><div class="dim" style="font-size:12px">%s</div></div>
<a class="ibtn" href="/logout" aria-label="Log out">%s</a></div></aside>
<div class="main"><div class="top"><div><h1>%s</h1><div class="sub">%s</div></div>
<div class="acts"><form action="/members" method="get" class="search">%s<input name="q" placeholder="Search name, phone or member ID" aria-label="Search members"></form>%s</div></div>
<div class="content">%s%s%s</div>
<div class="foot"><span>House of Strength · Ratlam</span><span>Powered by <b>TFS · The First Solutions</b></span></div>
</div></div></body></html>""" % (
        e(title), CSS, "".join(links), '<div class="navsec">System</div>' if sys_links else "", sys_links,
        initials(user.get("name") or "?"), e(user.get("name") or ""), e((user.get("role") or "").title()), icon("logout", 16),
        e(title), sub, icon("search") if A.role() != "trainer" else "", actions,
        '<div class="msg">%s</div>' % e(msg) if msg else "", '<div class="warn">%s</div>' % warn if warn else "", body)


def legacy_layout(conn, sn):
    """Wrap the older pages (edit member, door sync, today) in the new shell."""
    def layout(title, active, body, msg=""):
        act = {"/member": "/members", "/today": "/today", "/sync": "/sync", "/": "/gate"}.get(active, active)
        return shell(title, act, '<div class="panel legacy">%s</div>' % body, msg=msg,
                     cnt=counts(conn, sn) if sn else {})
    return layout


# ---------------- dashboard ----------------

def bars(items, highlight):
    top = max([v for _, v in items] + [1])
    return '<div class="bars">%s</div>' % "".join(
        '<div class="bar"><b>%s</b><i class="%s" style="height:%d%%"></i><span>%s</span></div>' % (
            (("%g" % v) if v else ""), "r" if highlight(lbl, v) else "", max(2, int(78 * v / top)), lbl)
        for lbl, v in items)


def dashboard(conn, sn, q):
    t = M.today()
    ti = M.iso(t)
    cnt = counts(conn, sn)
    total = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM members WHERE expiry >= ?", (ti,)).fetchone()[0]
    hours = conn.execute("SELECT CAST(substr(ts,12,2) AS INT) h, COUNT(DISTINCT pin) FROM punches WHERE sn=? "
                         "AND substr(ts,1,10)=? AND CAST(pin AS INT) < ? GROUP BY h", (sn, ti, STAFF_FROM)).fetchall()
    hmap = dict(hours)
    today_in = conn.execute("SELECT COUNT(DISTINCT pin) FROM punches WHERE sn=? AND substr(ts,1,10)=? "
                            "AND CAST(pin AS INT) < ?", (sn, ti, STAFF_FROM)).fetchone()[0]
    peak = max(hmap.items(), key=lambda x: x[1])[0] if hmap else None
    col_m = conn.execute("SELECT COALESCE(SUM(amount),0), COUNT(*) FROM payments WHERE substr(paid_on,1,7)=?",
                         (ti[:7],)).fetchone()
    pend = conn.execute("SELECT COALESCE(SUM(pending),0), SUM(pending>0) FROM members").fetchone()
    months = []
    d = t.replace(day=1)
    for _ in range(6):
        months.append(d)
        d = (d - datetime.timedelta(days=1)).replace(day=1)
    months.reverse()
    col6 = []
    for mth in months:
        v = conn.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE substr(paid_on,1,7)=?",
                         (mth.strftime("%Y-%m"),)).fetchone()[0]
        col6.append((mth.strftime("%b"), round(v / 1000, 1)))
    hour_items = [(("%d%s" % ((h - 1) % 12 + 1, "a" if h < 12 else "p")), hmap.get(h, 0)) for h in range(6, 23)]
    ren = conn.execute("SELECT * FROM members WHERE expiry BETWEEN ? AND ? ORDER BY expiry LIMIT 8",
                       (ti, M.iso(t + datetime.timedelta(days=7)))).fetchall()
    ren_rows = "".join(
        '<tr><td><a class="mem" href="/m?id=%d"><span class="av">%s</span>%s</a></td><td>%s</td><td>%s</td>'
        '<td>%s</td><td><a class="btn red sm" href="/bill?id=%d">Renew</a></td></tr>' % (
            m["client_id"], initials(m["name"]), e(nice(m["name"])), e(m["package"] or ""),
            short_date(m["expiry"])[:6], due_pill(m["expiry"]), m["client_id"]) for m in ren
    ) or '<tr><td colspan="5" class="dim">No renewals due this week</td></tr>'
    absent = absent_list(conn, sn, 7)[:5]
    since = tracking_start(conn)
    abs_rows = "".join(
        '<tr><td><a class="mem" href="/m?id=%d"><span class="av">%s</span>%s</a></td><td class="dim">%s days</td>'
        '<td style="text-align:right">%s</td></tr>' % (
            m["client_id"], initials(m["name"]), e(nice(m["name"])), days, wa_btn(m, absent_msg(m)))
        for days, last, m in absent
    ) or '<tr><td class="dim">Nobody yet. Gate data is collected since %s, so this list fills up from %s.</td></tr>' % (
        since.strftime("%d %b"), (since + datetime.timedelta(days=7)).strftime("%d %b"))
    body = """<div class="kpis">
<a class="kpi hot" href="/members?f=active"><div class="l">Active members</div><div class="v">%d</div><div class="s">%d expired · %d total</div></a>
<div class="kpi"><div class="l">Today's check-ins</div><div class="v">%d</div><div class="s">%s</div></div>
%s
<a class="kpi" href="/members?f=pending"><div class="l">Pending dues</div><div class="v">%s</div><div class="s">%d members</div></a></div>
<div class="two"><div class="panel"><div class="ph"><h2>Check-ins by hour · today</h2><a href="/attendance">Open attendance</a></div>%s</div>
<div class="panel"><div class="ph"><h2>%s</h2><span class="dim">%s</span></div>%s</div></div>
<div class="two"><div class="panel"><div class="ph"><h2>Renewals due this week</h2><a href="/renewals">View all %d</a></div>
<div class="tw"><table><tr><th>Member</th><th>Package</th><th>Expiry</th><th>Due</th><th></th></tr>%s</table></div></div>
<div style="display:flex;flex-direction:column;gap:20px"><div class="panel"><div class="ph"><h2>Quick actions</h2></div><div class="qa">
<a href="/bill">%sNew membership bill</a><a href="/member">%sAdd member</a><a href="/inquiries#lead">%sAdd inquiry</a><a href="/renewals">%sSend reminders</a></div></div>
<div class="panel"><div class="ph"><h2>Not seen for 7+ days</h2><a href="/absent">View all %d</a></div><table>%s</table></div></div></div>""" % (
        active, total - active, total, today_in,
        "Peak %s" % ("%d %s" % ((peak - 1) % 12 + 1, "AM" if peak < 12 else "PM")) if peak is not None else "From the gate",
        money_kpi(conn, col_m, t), money(pend[0]), pend[1] or 0,
        bars(hour_items, lambda l, v: v and v >= max(hmap.values() or [1]) * 0.6),
        "Collection · last 6 months" if A.is_admin() else "My collection today", "₹ thousand" if A.is_admin() else "",
        bars(col6, lambda l, v: True) if A.is_admin() else my_collection_table(conn), cnt["renewals"], ren_rows,
        icon("bill", 22), icon("users", 22), icon("chat", 22), icon("chat", 22), cnt["absent"], abs_rows)
    actions = ('<a class="btn" href="/gate">%sGate</a><a class="btn red" href="/bill">%sNew bill</a>'
               % (icon("finger"), icon("plus")))
    return shell("Dashboard", "/", body, sub=t.strftime("%A, %d %B %Y"), actions=actions, msg=q.get("m", ""), cnt=cnt)


def money_kpi(conn, col_m, t):
    if A.is_admin():
        return ('<div class="kpi"><div class="l">Collection this month</div><div class="v">%s</div>'
                '<div class="s">%d bills since 1 %s</div></div>' % (money(col_m[0]), col_m[1], t.strftime("%b")))
    mine = conn.execute("SELECT COALESCE(SUM(amount),0), COUNT(*) FROM payments WHERE paid_on=? AND created_by=?",
                        (M.iso(t), staff_name())).fetchone()
    return ('<div class="kpi"><div class="l">My collection today</div><div class="v">%s</div>'
            '<div class="s">%d bills by you</div></div>' % (money(mine[0]), mine[1]))


def my_collection_table(conn):
    rows = conn.execute("SELECT * FROM payments WHERE paid_on=? AND created_by=? ORDER BY id DESC",
                        (M.iso(M.today()), staff_name())).fetchall()
    return '<table>%s</table>' % ("".join('<tr><td>%s</td><td>%s</td><td style="text-align:right">%s · %s</td></tr>' % (
        e(r["invoice"] or ""), e(r["package"] or ""), money(r["amount"]), e(r["mode"] or "")) for r in rows)
        or '<tr><td class="dim">No bills by you today.</td></tr>')


def due_pill(exp_iso):
    d = M.parse_date(exp_iso)
    if not d:
        return '<span class="pill p-dim">—</span>'
    n = (d - M.today()).days
    if n < 0:
        return '<span class="pill p-bad">Expired %dd</span>' % -n
    if n == 0:
        return '<span class="pill p-bad">Today</span>'
    if n == 1:
        return '<span class="pill p-warn">Tomorrow</span>'
    return '<span class="pill %s">%d days</span>' % ("p-warn" if n <= 3 else "p-dim", n)


def status_pill(exp_iso):
    d = M.parse_date(exp_iso)
    if not d:
        return '<span class="pill p-dim">—</span>'
    n = (d - M.today()).days
    if n < 0:
        return '<span class="pill p-bad">Expired</span>'
    if n <= 7:
        return '<span class="pill p-warn">Expiring</span>'
    return '<span class="pill p-ok">Active</span>'


def renew_msg(m):
    return ("Hi %s, House of Strength me aapki membership %s ko khatam ho rahi hai. Renew karwane ke liye "
            "reception pe milein. Thank you!") % (nice(m["name"]), short_date(m["expiry"]))


def absent_msg(m):
    return "Hi %s, kaafi din se aap gym nahi aaye. Sab theek? House of Strength me aapka intezaar hai!" % nice(m["name"])


def wa_btn(m, text):
    if not phone_ok(m):
        return ""
    link = wa(m["phone"], text)
    return ('<a class="ibtn wa" href="%s" target="_blank" rel="noopener" aria-label="WhatsApp %s">%s</a>'
            % (e(link), e(m["name"] or ""), icon("chat", 16))) if link else ""


# ---------------- members ----------------

TABS = [("all", "All"), ("active", "Active"), ("soon", "Expiring"), ("expired", "Expired"), ("pt", "PT clients"),
        ("pending", "Pending dues")]


def member_rows(conn, sn, f, term):
    t = M.today()
    names = M.machine_names(conn, sn)
    blocked = M.blocked_pins(conn, sn)
    out = []
    for m in conn.execute("SELECT * FROM members ORDER BY client_id DESC"):
        pin = str(m["client_id"])
        exp = M.parse_date(m["expiry"])
        active = bool(exp and exp >= t)
        keep = {"all": True, "active": active, "soon": bool(exp and t <= exp <= t + datetime.timedelta(days=7)),
                "expired": not active, "pt": "pt" in (m["package"] or "").lower(),
                "pending": (m["pending"] or 0) > 0,
                "expired_on_machine": (not active) and pin in names and pin not in blocked,
                "active_missing": active and pin not in names}.get(f, True)
        if term and term not in ("%s %s %s %s" % (pin, member_id(pin), m["name"], m["phone"])).lower():
            keep = False
        if keep:
            out.append(m)
    return out


def members_list(conn, sn, q):
    t = M.today()
    f = q.get("f", "all")
    term = (q.get("q") or "").strip().lower()
    page = int(q.get("p", "1")) if q.get("p", "1").isdigit() else 1
    allm = conn.execute("SELECT * FROM members").fetchall()
    n_active = sum(1 for m in allm if (M.parse_date(m["expiry"]) or datetime.date.min) >= t)
    n_soon = sum(1 for m in allm if t <= (M.parse_date(m["expiry"]) or datetime.date.min) <= t + datetime.timedelta(days=7))
    n_pt = sum(1 for m in allm if "pt" in (m["package"] or "").lower())
    n_pend = sum(1 for m in allm if (m["pending"] or 0) > 0)
    tab_n = {"all": len(allm), "active": n_active, "soon": n_soon, "expired": len(allm) - n_active, "pt": n_pt,
             "pending": n_pend}
    rows = member_rows(conn, sn, f, term)
    per = 50
    pages = max(1, (len(rows) + per - 1) // per)
    page = min(page, pages)
    shown = rows[(page - 1) * per: page * per]
    trs = "".join(
        '<tr><td><a class="mem" href="/m?id=%d"><span class="av">%s</span>%s</a></td><td class="dim">%s</td><td>%s</td>'
        '<td>%s</td><td>%s</td><td>%s</td><td style="text-align:right;display:flex;gap:6px;justify-content:flex-end">%s'
        '%s<a class="ibtn" href="/member?id=%d" aria-label="Edit">%s</a></td></tr>' % (
            m["client_id"], initials(m["name"]), e(nice(m["name"])), member_id(m["client_id"]), e(m["package"] or ""),
            short_date(m["expiry"]), status_pill(m["expiry"]),
            '<span class="pill p-warn">%s</span>' % money(m["pending"]) if (m["pending"] or 0) > 0 else "₹0",
            wa_btn(m, renew_msg(m)), call_btn(m), m["client_id"], icon("edit", 16))
        for m in shown) or '<tr><td colspan="7" class="dim">No members match.</td></tr>'
    tabs = "".join('<a href="/members?%s"%s>%s %d</a>' % (urlencode({"f": k, "q": term}), ' class="on"' if k == f else "",
                                                          lbl, tab_n[k]) for k, lbl in TABS)
    qs = lambda p: urlencode({"f": f, "q": term, "p": p})
    pager = '<div style="display:flex;justify-content:space-between;align-items:center;margin-top:14px"><span class="dim">Showing %d–%d of %d</span><span style="display:flex;gap:8px">%s%s</span></div>' % (
        (page - 1) * per + 1 if rows else 0, (page - 1) * per + len(shown), len(rows),
        '<a class="btn sm" href="/members?%s">Previous</a>' % qs(page - 1) if page > 1 else "",
        '<a class="btn sm red" href="/members?%s">Next</a>' % qs(page + 1) if page < pages else "")
    door_issues = ""
    if f in ("expired_on_machine", "active_missing"):
        door_issues = '<div class="warn">Showing: %s</div>' % ("Expired but door still opens" if f == "expired_on_machine"
                                                               else "Active but not enrolled on the gate machine")
    body = """<div class="kpis">
<a class="kpi" href="/members"><div class="l">All members</div><div class="v">%d</div><div class="s">since Nov 2025</div></a>
<a class="kpi" href="/members?f=active"><div class="l">Active</div><div class="v">%d</div><div class="s">%d%%</div></a>
<a class="kpi" href="/members?f=soon"><div class="l">Expiring in 7 days</div><div class="v">%d</div><div class="s">send reminder</div></a>
<a class="kpi" href="/members?f=expired"><div class="l">Expired</div><div class="v">%d</div><div class="s">win-back list</div></a></div>
%s<div class="panel"><div class="ph"><div class="tabs">%s</div><div class="acts">
<a class="btn sm" href="/members?f=expired_on_machine">Door: expired inside</a><a class="btn sm" href="/members?f=active_missing">Door: not enrolled</a>
%s</div></div>
<div class="tw"><table><tr><th>Member</th><th>ID</th><th>Package</th><th>Expiry</th><th>Status</th><th>Due</th><th></th></tr>%s</table></div>%s</div>
%s<details class="panel"><summary style="cursor:pointer;font-weight:600">Import from old software</summary>
<p class="dim">CSV files made from the old software. Re-importing updates, it never duplicates.</p>
<p>Members: <input type="file" id="csv" accept=".csv,text/csv"> <button type="button" onclick="up('csv','/members/import','st')">Import members</button> <span id="st"></span></p>
<p>Old bills: <input type="file" id="bills" accept=".csv,text/csv"> <button type="button" onclick="up('bills','/payments/import','st2')">Import bills</button> <span id="st2"></span></p>
<p>Old attendance: <input type="file" id="att" accept=".csv,text/csv"> <button type="button" onclick="up('att','/attendance/import','st3')">Import attendance</button> <span id="st3"></span></p>
<script>function up(id,url,sid){var f=document.getElementById(id).files[0];if(!f){return}
var s=document.getElementById(sid);s.textContent='Uploading…';f.text().then(function(t){
return fetch(url,{method:'POST',headers:{'Content-Type':'text/csv'},body:t})}).then(function(r){return r.text()})
.then(function(t){s.textContent=t;setTimeout(function(){location.href='/members'},2500)})}</script></details>%s""" % (
        len(allm), n_active, round(100 * n_active / max(1, len(allm))), n_soon, len(allm) - n_active,
        door_issues, tabs, admin_only('<a class="btn sm" href="/members.csv?%s">%sExport Excel</a>' % (urlencode({"f": f, "q": term}), icon("down", 16))), trs, pager,
        "" if A.is_admin() else "<div hidden>", "" if A.is_admin() else "</div>")
    actions = '<a class="btn red" href="/member">%sAdd member</a>' % icon("plus")
    return shell("Members", "/members" if f != "pending" else "/members?f=pending", body,
                 sub="Every member, their package and status", actions=actions, msg=q.get("m", ""), cnt=counts(conn, sn))


def members_csv(conn, sn, q):
    rows = member_rows(conn, sn, q.get("f", "all"), (q.get("q") or "").strip().lower())
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Member ID", "Biometric ID", "Name", "Phone", "Package", "Expiry", "Status", "Pending"])
    for m in rows:
        d = M.parse_date(m["expiry"])
        w.writerow([member_id(m["client_id"]), m["client_id"], nice(m["name"]), m["phone"], m["package"],
                    d.strftime("%d-%m-%Y") if d else "", "Active" if d and d >= M.today() else "Expired",
                    "%g" % (m["pending"] or 0)])
    return "﻿" + buf.getvalue()


# ---------------- member profile ----------------

def profile(conn, sn, q):
    cid = q.get("id", "")
    m = conn.execute("SELECT * FROM members WHERE client_id=?", (cid,)).fetchone() if cid.isdigit() else None
    if not m:
        return shell("Member", "/members", '<div class="panel">Member not found. <a href="/members">Back to members</a></div>',
                     cnt=counts(conn, sn))
    t = M.today()
    exp = M.parse_date(m["expiry"])
    pays = conn.execute("SELECT * FROM payments WHERE client_id=? ORDER BY paid_on DESC, id DESC", (m["client_id"],)).fetchall()
    first = pays[-1] if pays else None
    start = M.parse_date(pays[0]["start"]) if pays else None
    left = (exp - t).days if exp else 0
    span = (exp - start).days if exp and start and exp > start else 0
    pct = max(0, min(100, int(100 * (span - left) / span))) if span else 0
    punches = conn.execute("SELECT DISTINCT substr(ts,1,10) d, MAX(ts) FROM punches WHERE sn=? AND pin=? AND ts >= ? GROUP BY d",
                           (sn, str(m["client_id"]), M.iso(t - datetime.timedelta(days=29)))).fetchall()
    days_in = {r[0] for r in punches}
    last = conn.execute("SELECT MAX(ts) FROM punches WHERE pin=?", (str(m["client_id"]),)).fetchone()[0]
    lastd = M.parse_date(last[:10]) if last else None
    last_txt = ("Today" if lastd == t else "Yesterday" if lastd == t - datetime.timedelta(days=1)
                else lastd.strftime("%d %b") if lastd else "—")
    heat = "".join('<i class="%s" title="%s"></i>' % ("on" if M.iso(t - datetime.timedelta(days=29 - i)) in days_in else "",
                                                      (t - datetime.timedelta(days=29 - i)).strftime("%d %b"))
                   for i in range(30))
    names = M.machine_names(conn, sn)
    blocked = str(m["client_id"]) in M.blocked_pins(conn, sn)
    door = "Blocked" if blocked else ("On gate machine" if str(m["client_id"]) in names else "Not enrolled on machine")
    status = status_pill(m["expiry"])
    bill_rows = "".join(
        '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
            e(p["invoice"] or "—"), short_date(p["paid_on"]), e(p["package"] or ""),
            money(p["payable"] if p["payable"] is not None else (p["list_price"] or p["amount"])), money(p["amount"]),
            '<span class="pill p-warn">Due %s</span>' % money(p["balance"]) if (p["balance"] or 0) > 0 else '<span class="pill p-ok">Paid</span>')
        for p in pays) or '<tr><td colspan="6" class="dim">No bills yet</td></tr>'
    lastinv = next((p["invoice"] for p in pays if p["invoice"]), "")
    body = """<div class="panel"><div class="hero"><div class="big">%s</div><div style="flex:1;min-width:240px">
<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap"><h2>%s</h2>%s%s</div>
<div class="dim" style="margin-top:6px">%s · ends %s · %s</div><div class="prog"><i style="width:%d%%"></i></div></div>
<div class="acts"><a class="btn red" href="/bill?id=%d">%sRenew</a>%s<a class="btn" href="/member?id=%d">%sEdit</a></div></div></div>
<div class="two"><div class="panel"><div class="ph"><h2>Details</h2></div><div class="kv">
<div><span>Member ID</span><b>%s</b></div><div><span>Mobile</span><b>%s</b></div>
<div><span>Gender</span><b>%s</b></div><div><span>Joined</span><b>%s</b></div>
<div><span>Biometric ID</span><b>%d</b></div><div><span>Gate door</span><b>%s</b></div>
<div><span>Pending</span><b>%s</b></div><div><span>Package</span><b>%s</b></div></div></div>
<div class="panel"><div class="ph"><h2>Attendance · last 30 days</h2></div>
<div class="kpis" style="grid-template-columns:repeat(2,minmax(0,1fr))"><div class="kpi"><div class="l">Visits</div><div class="v">%d</div><div class="s">of 30 days</div></div>
<div class="kpi"><div class="l">Last visit</div><div class="v">%s</div><div class="s">%s</div></div></div>
<div class="heat" style="margin-top:16px">%s</div><p class="dim" style="margin:10px 0 0;font-size:12px">Gate data on the new system since %s.</p></div></div>
<div class="panel"><div class="ph"><h2>Bills &amp; payments</h2><a href="/bill?id=%d">New bill</a></div>
<div class="tw"><table><tr><th>Invoice</th><th>Date</th><th>Package</th><th>Amount</th><th>Paid</th><th>Status</th></tr>%s</table></div>
%s</div>""" % (
        initials(m["name"]), e(nice(m["name"])), status,
        ' <span class="pill p-warn">Due %s</span>' % money(m["pending"]) if (m["pending"] or 0) > 0 else "",
        e(m["package"] or "—"), short_date(m["expiry"]),
        ("%d days left" % left) if left >= 0 else ("expired %d days ago" % -left), pct,
        m["client_id"], icon("renew"), wa_btn_big(m), m["client_id"], icon("edit"),
        member_id(m["client_id"]), e(show_phone(m) or "—"), e(m["gender"] or "—"),
        short_date(m["registration"] or (first["paid_on"] if first else "")), m["client_id"], door,
        money(m["pending"]), e(m["package"] or "—"),
        len(days_in), last_txt, last[11:16] if last else "", heat, tracking_start(conn).strftime("%d %b %Y"),
        m["client_id"], bill_rows,
        ('<p style="display:flex;gap:10px;flex-wrap:wrap;margin:16px 0 0"><a class="btn sm" href="/receipt?inv=%s">%sPrint last receipt</a></p>'
         % (quote(lastinv), icon("print", 16))) if lastinv else "")
    jr = conn.execute("SELECT id, data FROM joinings WHERE client_id=? ORDER BY id DESC LIMIT 1", (m["client_id"],)).fetchone()
    jform = ""
    if jr and A.role() in ("admin", "reception"):
        import joining as J
        try:
            flags = J.health_flags(__import__("json").loads(jr["data"] or "{}"))
        except ValueError:
            flags = []
        jform = '<a class="btn" href="/joinings/view?id=%d">%sJoining form%s</a>' % (
            jr["id"], icon("edit", 16), (' <span class="pill p-bad">%s</span>' % e(flags[0][:30])) if flags else "")
    return shell("Member profile", "/members", body, sub='<a href="/members">Members</a> › %s' % e(nice(m["name"])),
                 actions=jform + '<a class="btn red" href="/bill?id=%d">%sNew bill</a>' % (m["client_id"], icon("plus")),
                 msg=q.get("m", ""), cnt=counts(conn, sn))


def wa_btn_big(m):
    if not phone_ok(m):
        return ""
    link = wa(m["phone"], "Hi %s, House of Strength se." % nice(m["name"]))
    return '<a class="btn" href="%s" target="_blank" rel="noopener">%sWhatsApp</a>' % (e(link), icon("chat")) if link else ""


# ---------------- new bill ----------------

def bill_page(conn, sn, q):
    cid = q.get("id", "")
    m = conn.execute("SELECT * FROM members WHERE client_id=?", (cid,)).fetchone() if cid.isdigit() else None
    pk = conn.execute("SELECT * FROM packages WHERE active=1 ORDER BY kind, sort").fetchall()
    sold = {}
    for name, n in conn.execute("SELECT lower(package), COUNT(*) FROM payments GROUP BY lower(package)"):
        sold[name] = n
    cards = "".join(
        '<label><input type="radio" name="package_id" value="%d" data-days="%d" data-price="%g" data-name="%s" data-kind="%s" %s required>'
        '<b>%s</b><span class="dim">%d days%s</span><span class="pr">%s</span></label>' % (
            p["id"], p["days"], p["price"], e(p["name"]), p["kind"], "", e(p["name"]), p["days"],
            " · PT" if p["kind"] == "pt" else "", money(p["price"]))
        for p in pk)
    options = "".join('<option value="%d">%s · %s</option>' % (r[0], e(nice(r[1])), member_id(r[0]))
                      for r in conn.execute("SELECT client_id, name FROM members ORDER BY client_id DESC"))
    tr = "".join('<option>%s</option>' % e(x) for x in trainers(conn))
    inv = "%s%05d" % (M.setting(conn, "invoice_prefix", "HOS-"), int(M.setting(conn, "next_invoice", "1242")))
    start = M.today()
    if m:
        old = M.parse_date(m["expiry"])
        if old and old >= start:
            start = old + datetime.timedelta(days=1)
    ai_box = """<div class="panel" style="display:flex;flex-direction:column;gap:10px"><div class="ph" style="margin:0"><h2>AI-fill</h2>
<span class="dim" style="font-size:12px">%s</span></div><div style="display:flex;flex-wrap:wrap;gap:10px">
<input id="aitext" placeholder="e.g. Rohit 3 month, 1500 discount, 5000 UPI se diya" style="flex:1 1 360px"%s>
<button type="button" class="btn red" id="aibtn" onclick="aiFill()"%s>Fill with AI</button></div>
<div id="aimsg" class="dim" style="font-size:13px"></div></div>""" % (
        "Type one line, check the form, then Save. Nothing is saved without you." if AI.available() else "AI is not set up on the server yet.",
        "" if AI.available() else " disabled", "" if AI.available() else " disabled")
    body = ai_box + """<form method="post" action="/bill/save" class="two" style="grid-template-columns:minmax(0,2fr) minmax(280px,1fr);align-items:start" id="bf">
<div class="panel" style="display:flex;flex-direction:column;gap:22px">
<div><h2 style="margin-bottom:12px">1 · Member</h2><div class="grid">
<label>Member (type name or ID)<input name="member" list="mlist" value="%s" required placeholder="Search member" autocomplete="off"></label>
<datalist id="mlist">%s</datalist>
<label>Bill type<select name="kind" id="kind"><option value="gym">Gym membership</option><option value="pt">Personal training</option></select></label></div>
<p class="dim" style="margin:8px 0 0;font-size:12px">New person? <a href="/member">Add member first</a> (enroll the finger on the gate with the same ID).</p></div>
<div><h2 style="margin-bottom:12px">2 · Package</h2><div class="pk">%s</div></div>
<div><h2 style="margin-bottom:12px">3 · Dates &amp; trainer</h2><div class="grid">
<label>Start date<input type="date" name="start" id="start" value="%s" required></label>
<label>End date<input type="date" name="end" id="end" required></label>
<label>Trainer (optional)<select name="trainer"><option value="">No trainer</option>%s</select></label></div></div>
<div><h2 style="margin-bottom:12px">4 · Payment</h2><div class="grid">
<label>Discount (₹)<input name="discount" id="disc" inputmode="decimal" value="0"></label>
<label>Admission fee (₹)<input name="admission" id="adm" inputmode="decimal" value="%s"></label>
<label>GST<select name="gst" id="gst"><option value="0">No GST</option><option value="18">18%% GST</option></select></label>
<label>Amount paid now (₹)<input name="paid" id="paid" inputmode="decimal" required></label>
<label>Payment mode<select name="mode"><option>UPI</option><option>Cash</option><option>Card</option><option>Online</option></select></label>
<label>Next due date (if balance)<input type="date" name="next_due"></label></div></div></div>
<div class="panel" style="position:sticky;top:16px"><h2 style="margin-bottom:16px">Bill summary</h2><div class="sum">
<div><span id="s_pk">Package</span><span id="s_price">₹0</span></div><div><span>Discount</span><span id="s_disc">– ₹0</span></div>
<div><span>Admission</span><span id="s_adm">₹0</span></div><div><span>GST</span><span id="s_gst">₹0</span></div>
<div class="t"><span>Total payable</span><span id="s_tot">₹0</span></div><div><span>Paid now</span><span id="s_paid">₹0</span></div>
<div class="t"><span>Balance</span><span id="s_bal">₹0</span></div>
<label class="chk"><input type="checkbox" name="send_wa" value="1" checked>Send receipt on WhatsApp</label>
<label class="chk"><input type="checkbox" name="print" value="1">Print receipt (A4)</label>
<button class="btn red" style="font-family:Oswald,sans-serif;font-size:18px;letter-spacing:.04em;min-height:52px" id="savebtn">SAVE BILL</button>
<span class="dim" style="font-size:12px">Invoice %s · prepared by %s</span></div></div></form>
<script>
(function(){var f=document.getElementById('bf');function n(v){v=parseFloat((v||'').toString().replace(/,/g,''));return isNaN(v)?0:v}
function r(v){return '₹'+Math.round(v).toLocaleString('en-IN')}
function sel(){return f.querySelector('input[name=package_id]:checked')}
function kindFilter(){var k=document.getElementById('kind').value;f.querySelectorAll('.pk label').forEach(function(l){var i=l.querySelector('input');l.style.display=(i.dataset.kind==k||(k=='gym'&&i.dataset.kind=='gym'))?'':'none'})}
function upd(){var p=sel(),price=p?n(p.dataset.price):0,d=n(f.disc.value),a=n(f.adm.value),g=n(f.gst.value);
var base=Math.max(0,price-d+a),gst=base*g/100,tot=base+gst,paid=f.paid.value===''?tot:n(f.paid.value);
document.getElementById('s_pk').textContent=p?('Package · '+p.dataset.name):'Package';document.getElementById('s_price').textContent=r(price);
document.getElementById('s_disc').textContent='– '+r(d);document.getElementById('s_adm').textContent=r(a);document.getElementById('s_gst').textContent=r(gst);
document.getElementById('s_tot').textContent=r(tot);document.getElementById('s_paid').textContent=r(paid);document.getElementById('s_bal').textContent=r(Math.max(0,tot-paid));
document.getElementById('savebtn').textContent='SAVE BILL · '+r(paid);if(p&&f.start.value){var s=new Date(f.start.value);s.setDate(s.getDate()+n(p.dataset.days)-1);
if(!f.end.dataset.touched){f.end.value=s.toISOString().slice(0,10)}}}
f.disc=document.getElementById('disc');f.adm=document.getElementById('adm');f.gst=document.getElementById('gst');f.paid=document.getElementById('paid');
f.start=document.getElementById('start');f.end=document.getElementById('end');
f.addEventListener('input',upd);f.addEventListener('change',upd);f.end.addEventListener('input',function(){f.end.dataset.touched=1});
f.start.addEventListener('input',function(){delete f.end.dataset.touched});f.querySelectorAll('input[name=package_id]').forEach(function(i){i.addEventListener('change',function(){delete f.end.dataset.touched;upd()})});
document.getElementById('kind').addEventListener('change',function(){kindFilter();upd()});kindFilter();upd();
window.aiFill=function(){var t=document.getElementById('aitext').value.trim(),m=document.getElementById('aimsg'),b=document.getElementById('aibtn');if(!t){return}
b.disabled=true;b.textContent='Reading…';m.textContent='';fetch('/bill/ai',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'text='+encodeURIComponent(t)})
.then(function(r){return r.json()}).then(function(d){b.disabled=false;b.textContent='Fill with AI';if(d.error){m.textContent=d.error;return}
var set=function(name,v){var el=f.querySelector('[name='+name+']');if(el&&v!==undefined&&v!==null&&v!==''){el.value=v}};
if(d.member){f.querySelector('[name=member]').value=d.member}
document.getElementById('kind').value=d.bill_type||'gym';kindFilter();
if(d.package){f.querySelectorAll('input[name=package_id]').forEach(function(i){if(i.dataset.name===d.package){i.checked=true}})}
if(d.start_date){f.start.value=d.start_date}delete f.end.dataset.touched;set('trainer',d.trainer);
f.disc.value=d.discount||0;f.adm.value=d.admission||0;f.paid.value=(d.paid===null||d.paid<0)?'':d.paid;set('mode',d.mode);upd();
m.innerHTML=d.note||'Form filled. Check every field, then Save.'}).catch(function(){b.disabled=false;b.textContent='Fill with AI';m.textContent='Could not reach the server.'})};
document.getElementById('aitext').addEventListener('keydown',function(ev){if(ev.key==='Enter'){ev.preventDefault();aiFill()}})})();
</script>""" % (
        e("%s · %s" % (nice(m["name"]), member_id(m["client_id"]))) if m else "", options, cards,
        M.iso(start), tr, e(M.setting(conn, "default_admission", "0")), inv, e(staff_name()))
    return shell("New bill", "/bill", body, sub="Membership or PT bill in under a minute", msg=q.get("m", ""),
                 cnt=counts(conn, sn))


def ai_fill(conn, f):
    """JSON for the bill page. The typed line goes to Claude; member lookup stays on this server."""
    text = (f.get("text") or "").strip()
    if not text:
        return {"error": "Type a line first."}
    pk = [(r["name"], r["days"], r["price"], r["kind"]) for r in conn.execute("SELECT * FROM packages WHERE active=1 ORDER BY kind, sort")]
    data, err = AI.bill_fill(text, pk, trainers(conn), M.iso(M.today()))
    if err:
        return {"error": err}
    out = {k: data.get(k) for k in ("bill_type", "package", "start_date", "trainer", "discount", "admission", "paid", "mode")}
    notes = []
    q = (data.get("member") or "").strip()
    found = []
    if q:
        found = [r for r in [resolve_member(conn, q)] if r]
        if not found:
            words = [w for w in re.split(r"\s+", q.lower()) if len(w) > 1]
            rows = conn.execute("SELECT * FROM members ORDER BY expiry DESC").fetchall()
            found = [r for r in rows if words and all(w in (r["name"] or "").lower() for w in words)][:6]
    if len(found) == 1:
        out["member"] = "%s · %s" % (nice(found[0]["name"]), member_id(found[0]["client_id"]))
    elif found:
        notes.append("More than one member matches <b>%s</b>: %s. Pick the right one in the Member box." % (
            e(q), ", ".join("%s (%s)" % (e(nice(r["name"])), member_id(r["client_id"])) for r in found)))
    elif q:
        notes.append("No member found for <b>%s</b>. Pick from the list, or add them as a new member first." % e(q))
    if data.get("unclear"):
        notes.append("AI note: %s" % e(data["unclear"]))
    out["note"] = " ".join(notes + ["Check every field, then Save."])
    return out


def resolve_member(conn, text):
    text = (text or "").strip()
    m = re.search(r"HOS-0*(\d+)", text, re.I) or re.fullmatch(r"\s*(\d+)\s*", text)
    if m:
        return conn.execute("SELECT * FROM members WHERE client_id=?", (int(m.group(1)),)).fetchone()
    rows = conn.execute("SELECT * FROM members WHERE lower(name)=lower(?)", (text,)).fetchall()
    return rows[0] if len(rows) == 1 else None


def num(v):
    try:
        return float(str(v or "0").replace(",", "").strip() or 0)
    except ValueError:
        return 0.0


def save_bill(conn, sn, f):
    m = resolve_member(conn, f.get("member"))
    if not m:
        return None, "Member not found. Pick from the list (name · HOS-ID)."
    p = conn.execute("SELECT * FROM packages WHERE id=?", (f.get("package_id", "0"),)).fetchone()
    if not p:
        return None, "Choose a package."
    start = M.parse_date(f.get("start")) or M.today()
    end = M.parse_date(f.get("end")) or (start + datetime.timedelta(days=p["days"] - 1))
    if end < start:
        return None, "End date is before start date."
    disc, adm, rate = num(f.get("discount")), num(f.get("admission")), num(f.get("gst"))
    cap = num(M.setting(conn, "max_discount_reception", str(A.RECEPTION_MAX_DISCOUNT)))
    if not A.is_admin() and disc > p["price"] * cap / 100:
        request_approval(conn, "discount", m["client_id"], dict(f, package_name=p["name"]),
                         "Discount %s on %s (limit %g%%)" % (money(disc), p["name"], cap))
        return None, ("Discount above %g%% (%s) needs the owner. The bill has been sent to the owner for approval; "
                      "it is made as soon as they approve." % (cap, money(p["price"] * cap / 100)))
    base = max(0.0, p["price"] - disc + adm)
    gst = round(base * rate / 100, 2)
    total = base + gst
    paid = num(f.get("paid")) if (f.get("paid") or "").strip() else total
    balance = max(0.0, round(total - paid, 2))
    n = int(M.setting(conn, "next_invoice", "1242"))
    inv = "%s%05d" % (M.setting(conn, "invoice_prefix", "HOS-"), n)
    M.set_setting(conn, "next_invoice", n + 1)
    conn.execute(
        "INSERT INTO payments (client_id, paid_on, amount, mode, package, start, expiry, note, created_at, invoice, "
        "list_price, discount, admission, gst, payable, balance, trainer, kind, created_by, next_due) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (m["client_id"], M.iso(M.today()), paid, f.get("mode", ""), p["name"], M.iso(start), M.iso(end), "",
         M.stamp(), inv, p["price"], disc, adm, gst, total, balance, f.get("trainer", ""), p["kind"], staff_name(),
         M.iso(M.parse_date(f.get("next_due")))))
    old_exp = M.parse_date(m["expiry"])
    new_exp = max(end, old_exp) if old_exp else end
    conn.execute("UPDATE members SET package=?, expiry=?, pending=COALESCE(pending,0)+?, updated_at=? WHERE client_id=?",
                 (p["name"], M.iso(new_exp), balance, M.stamp(), m["client_id"]))
    note = ""
    if sn and new_exp >= M.today() and str(m["client_id"]) in M.blocked_pins(conn, sn):
        ok, note = M.unblock(conn, sn, m["client_id"])
    return inv, "Bill %s saved. %s" % (inv, note)


# ---------------- receipt ----------------

def receipt_text(conn, inv):
    """(WhatsApp text, member row) for a bill, or ("", None)."""
    p = conn.execute("SELECT * FROM payments WHERE invoice=?", (inv,)).fetchone()
    if not p:
        return "", None
    m = conn.execute("SELECT * FROM members WHERE client_id=?", (p["client_id"],)).fetchone()
    name = nice(m["name"]) if m else ""
    return ("House of Strength - Receipt %s\nMember: %s (%s)\nPackage: %s\nPeriod: %s to %s\nTotal: %s\nPaid: %s (%s)\n%s"
            "Thank you! Get better, together.") % (
        inv, name, member_id(p["client_id"]), p["package"], short_date(p["start"]), short_date(p["expiry"]),
        money(p["payable"]), money(p["amount"]), p["mode"] or "",
        ("Balance: %s\n" % money(p["balance"])) if (p["balance"] or 0) > 0 else ""), m


def receipt(conn, sn, q):
    inv = q.get("inv", "")
    p = conn.execute("SELECT * FROM payments WHERE invoice=?", (inv,)).fetchone()
    if not p:
        return shell("Receipt", "/bill", '<div class="panel">Receipt not found.</div>', cnt=counts(conn, sn))
    m = conn.execute("SELECT * FROM members WHERE client_id=?", (p["client_id"],)).fetchone()
    S = lambda k: M.setting(conn, k, "")
    name = nice(m["name"]) if m else ""
    text = ("House of Strength - Receipt %s\nMember: %s (%s)\nPackage: %s\nPeriod: %s to %s\nTotal: %s\nPaid: %s (%s)\n%s"
            "Thank you! Get better, together.") % (
        inv, name, member_id(p["client_id"]), p["package"], short_date(p["start"]), short_date(p["expiry"]),
        money(p["payable"]), money(p["amount"]), p["mode"] or "",
        ("Balance: %s\n" % money(p["balance"])) if (p["balance"] or 0) > 0 else "")
    link = wa(m["phone"], text) if m and phone_ok(m) else ""
    auto = ""
    if q.get("wa") == "1" and link:
        auto = "<script>window.open(%r,'_blank')</script>" % link
    if q.get("print") == "1":
        auto += "<script>setTimeout(function(){window.print()},700)</script>"
    thermal = q.get("size") == "80"
    rows = [("Package", e(p["package"] or "")), ("Period", "%s → %s" % (short_date(p["start"]), short_date(p["expiry"]))),
            ("Trainer", e(p["trainer"] or "—")), ("Package price", money(p["list_price"])),
            ("Discount", "– " + money(p["discount"])), ("Admission", money(p["admission"])), ("GST", money(p["gst"])),
            ("<b>Total payable</b>", "<b>%s</b>" % money(p["payable"])), ("Paid (%s)" % e(p["mode"] or ""), money(p["amount"])),
            ("<b>Balance</b>", "<b>%s</b>" % money(p["balance"]))]
    upi = S("upi_id").strip()
    pay_amt = (p["balance"] or 0) if (p["balance"] or 0) > 0 else 0
    upi_link = ""
    if upi:
        upi_link = "upi://pay?" + urlencode({"pa": upi, "pn": S("upi_name") or "House of Strength", "cu": "INR",
                                             "tn": "%s %s" % (inv, member_id(p["client_id"]))})
        if pay_amt:
            upi_link += "&am=%.2f" % pay_amt
    bank = [(l, S(k)) for l, k in (("Account name", "bank_name"), ("Account no.", "bank_account"), ("IFSC", "bank_ifsc"),
                                   ("Bank / branch", "bank_branch")) if S(k)]
    pay_block = ""
    if upi or bank:
        pay_block = """<div style="display:flex;flex-wrap:wrap;gap:18px;align-items:center;margin-top:18px;padding-top:14px;border-top:1px dashed #ccc">
%s<div style="font-size:12px;color:#333;line-height:1.7">%s%s</div></div>""" % (
            ('<div><div id="qr" style="width:%dpx;height:%dpx"></div><div style="font-size:11px;color:#555;text-align:center;margin-top:4px">%s</div></div>'
             % ((110, 110, "Scan to pay %s" % money(pay_amt)) if not thermal else (120, 120, "Scan to pay"))
             if upi else "") if True else "",
            ("<b>UPI:</b> %s<br>" % e(upi)) if upi else "",
            "".join("<b>%s:</b> %s<br>" % (e(l), e(v)) for l, v in bank))
        if pay_amt == 0 and upi:
            pay_block = pay_block.replace("Scan to pay ₹0", "Scan to pay")
    width = "300px" if thermal else "720px"
    head_extra = " · ".join(x for x in (e(S("gym_phone")), ("GSTIN " + e(S("gst_no"))) if S("gst_no") else "") if x)
    body = """<style>@media print{@page{%s}}</style><div class="panel" style="max-width:%s;background:#fff;color:#111;%s">
<div style="display:flex;%sjustify-content:space-between;align-items:center;gap:16px;border-bottom:2px solid #e10600;padding-bottom:14px">
<div style="display:flex;align-items:center;gap:12px"><img src="/logo.jpg" alt="" style="width:%dpx;height:%dpx;border-radius:10px">
<div><div style="font:700 %dpx Oswald,sans-serif">HOUSE OF STRENGTH</div><div style="color:#555;font-size:12px">%s</div>
<div style="color:#555;font-size:12px">%s</div></div></div>
<div style="text-align:right"><div style="font:600 20px Oswald,sans-serif">RECEIPT</div><div>%s</div><div style="color:#555">%s</div></div></div>
<p style="margin:16px 0"><b>%s</b> · %s · %s</p><p style="margin:-8px 0 12px;color:#555;font-size:12px">Prepared by %s</p>
<table style="color:#111">%s</table>%s
<div style="display:flex;justify-content:space-between;align-items:flex-end;gap:12px;margin-top:22px">
<p style="color:#555;font-size:12px;margin:0;max-width:420px">%s</p><div style="text-align:center;font-size:12px;color:#555"><div style="width:150px;border-top:1px solid #999;margin-bottom:4px"></div>Signature</div></div>
<p style="color:#888;font-size:11px">Powered by TFS · The First Solutions</p></div>
<div class="acts noprint"><button class="btn" onclick="window.print()">%sPrint</button><a class="btn" href="/receipt?%s">%s</a>%s
<a class="btn" href="/m?id=%d">Open member</a><a class="btn red" href="/bill">New bill</a></div>%s%s""" % (
        "size:80mm auto;margin:3mm" if thermal else "size:A4;margin:12mm", width, "font-size:12px;padding:12px" if thermal else "",
        "flex-direction:column;align-items:flex-start;" if thermal else "", 40 if thermal else 64, 40 if thermal else 64,
        18 if thermal else 24, e(S("gym_address")), head_extra, e(inv), short_date(p["paid_on"]), e(name),
        member_id(p["client_id"]), e(show_phone(m) if m else ""), e(p["created_by"] or "—"),
        "".join('<tr><td style="color:#444;border-color:#eee;padding:6px 8px">%s</td><td style="text-align:right;border-color:#eee;padding:6px 8px">%s</td></tr>' % r for r in rows),
        pay_block, e(S("receipt_terms") or "Fees are non-refundable and non-transferable. Thank you for training with us. Get better, together."),
        icon("print", 16), urlencode({"inv": inv, "size": "a4" if thermal else "80"}), "A4 size" if thermal else "Thermal 80 mm",
        ('<a class="btn" href="%s" target="_blank" rel="noopener">%sSend on WhatsApp</a>' % (e(link), icon("chat", 16))) if link else "",
        p["client_id"],
        ('<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>'
         '<script>try{new QRCode(document.getElementById("qr"),{text:%r,width:%d,height:%d,correctLevel:QRCode.CorrectLevel.M})}catch(x){}</script>'
         % (upi_link, 120 if thermal else 110, 120 if thermal else 110)) if upi else "", auto)
    return shell("Receipt", "/bill", body, sub=e(inv), msg=q.get("m", ""), cnt=counts(conn, sn))


# ---------------- settings ----------------

SETTING_FIELDS = [
    ("Gym profile", [("gym_name", "Gym name", "House of Strength"), ("gym_phone", "Phone", ""), ("gym_email", "Email", ""),
                     ("gym_instagram", "Instagram", ""), ("gym_address", "Address", ""), ("gst_no", "GST number (optional)", ""),
                     ("open_time", "Opens", "07:00"), ("close_time", "Closes", "23:00")]),
    ("Payment details on receipts", [("upi_id", "UPI ID (for the scan-to-pay QR)", ""), ("upi_name", "UPI payee name", ""),
                                     ("bank_name", "Bank account name", ""), ("bank_account", "Account number", ""),
                                     ("bank_ifsc", "IFSC", ""), ("bank_branch", "Bank & branch", "")]),
    ("Billing rules", [("max_discount_reception", "Max discount · reception (%)", "20"), ("invoice_prefix", "Invoice prefix", "HOS-"),
                       ("next_invoice", "Next invoice number", "1242"), ("default_admission", "Default admission fee (₹)", "0"),
                       ("receipt_terms", "Receipt terms", "Fees are non-refundable and non-transferable.")]),
]


def settings_page(conn, sn, q):
    blocks = []
    for title, fields in SETTING_FIELDS:
        inputs = "".join('<label>%s<input name="%s" value="%s"></label>' % (e(lbl), k, e(M.setting(conn, k, d))) for k, lbl, d in fields)
        blocks.append('<div class="panel"><h2 style="margin-bottom:14px">%s</h2><div class="grid">%s</div></div>' % (e(title), inputs))
    body = ('<form method="post" action="/settings/save" style="display:flex;flex-direction:column;gap:20px">%s'
            '<button class="btn red" style="align-self:flex-start">Save changes</button></form>' % "".join(blocks)) + GS.settings_block(conn)
    return shell("Settings", "/settings", body, sub="Gym profile, receipt payment details, billing rules",
                 msg=q.get("m", ""), cnt=counts(conn, sn))


def save_settings(conn, f):
    for _, fields in SETTING_FIELDS:
        for k, _, _ in fields:
            if k in f:
                v = f[k].strip()
                if k in ("max_discount_reception", "next_invoice", "default_admission") and not re.fullmatch(r"\d+(\.\d+)?", v or "x"):
                    continue
                M.set_setting(conn, k, v)
    return "Settings saved."


def max_discount():
    return A.RECEPTION_MAX_DISCOUNT


# ---------------- packages ----------------

def packages_page(conn, sn, q):
    sold = {r[0]: r[1] for r in conn.execute("SELECT lower(trim(package)), COUNT(*) FROM payments GROUP BY 1")}
    edit_id = q.get("edit", "")
    out = []
    for kind, title in (("gym", "Gym membership"), ("pt", "Personal training")):
        cards = []
        for p in conn.execute("SELECT * FROM packages WHERE kind=? ORDER BY active DESC, sort, id", (kind,)):
            n = sold.get(p["name"].lower(), 0)
            if A.is_admin() and str(p["id"]) == edit_id:
                cards.append("""<form class="panel" method="post" action="/packages/save" style="display:flex;flex-direction:column;gap:10px">
<input type="hidden" name="id" value="%d"><label>Name<input name="name" value="%s" required></label>
<div class="grid"><label>Days<input name="days" value="%d" required></label><label>Price (₹)<input name="price" value="%g" required></label></div>
<label>Type<select name="kind"><option value="gym"%s>Gym membership</option><option value="pt"%s>Personal training</option></select></label>
<div style="display:flex;gap:8px"><button class="btn red sm">Save</button><a class="btn sm" href="/packages">Cancel</a></div></form>""" % (
                    p["id"], e(p["name"]), p["days"], p["price"], " selected" if kind == "gym" else "", " selected" if kind == "pt" else ""))
                continue
            tools = ""
            if A.is_admin():
                tools = ('<div style="display:flex;gap:8px;margin-top:14px"><a class="btn sm" href="/packages?edit=%d">Edit</a>'
                         '<form method="post" action="/packages/save"><input type="hidden" name="id" value="%d"><input type="hidden" name="toggle" value="1">'
                         '<button class="btn sm">%s</button></form></div>' % (p["id"], p["id"], "Hide" if p["active"] else "Show"))
            cards.append('<div class="panel" style="%s"><div class="ph" style="margin:0"><h2>%s</h2>%s</div><div class="dim">%d days</div>'
                         '<div style="font:600 34px Oswald,sans-serif;margin:8px 0">%s</div><div class="dim">%d sold%s</div>%s</div>' % (
                             "" if p["active"] else "opacity:.5", e(p["name"]),
                             '<span class="pill p-bad">Best seller</span>' if n and n == max(sold.values() or [0]) else "",
                             p["days"], money(p["price"]), n, "" if p["active"] else " · hidden", tools))
        out.append('<h2 class="dim" style="font-family:Oswald,sans-serif;margin:6px 0 0">%s</h2><div class="kpis">%s</div>' % (title, "".join(cards)))
    add = ""
    if A.is_admin():
        add = """<form class="panel" method="post" action="/packages/save" style="display:flex;flex-direction:column;gap:12px">
<h2>Add package</h2><div class="grid"><label>Name<input name="name" required></label><label>Days<input name="days" required></label>
<label>Price (₹)<input name="price" required></label><label>Type<select name="kind"><option value="gym">Gym membership</option><option value="pt">Personal training</option></select></label></div>
<button class="btn red" style="align-self:flex-start">Add package</button></form>"""
    return shell("Packages", "/packages", "".join(out) + add, sub="Prices, and what actually sells", msg=q.get("m", ""),
                 cnt=counts(conn, sn))


def save_package(conn, f):
    pid = f.get("id", "")
    if f.get("toggle") and pid.isdigit():
        conn.execute("UPDATE packages SET active = 1 - active WHERE id=?", (int(pid),))
        return "Package updated."
    name = (f.get("name") or "").strip()
    days, price = f.get("days", ""), f.get("price", "").replace(",", "")
    if not name or not days.isdigit() or not re.fullmatch(r"\d+(\.\d+)?", price):
        return "Name, days and price are needed."
    kind = "pt" if f.get("kind") == "pt" else "gym"
    if pid.isdigit():
        conn.execute("UPDATE packages SET name=?, days=?, price=?, kind=? WHERE id=?", (name, int(days), float(price), kind, int(pid)))
        return "Saved %s." % name
    if conn.execute("SELECT 1 FROM packages WHERE lower(name)=lower(?)", (name,)).fetchone():
        return "A package with this name already exists."
    conn.execute("INSERT INTO packages (name, days, price, kind, sessions, sort) VALUES (?,?,?,?,0,99)",
                 (name, int(days), float(price), kind))
    return "Added %s." % name


def soon(conn, sn, q):
    name = q.get("p", "This page")
    links = {"Attendance": "/gate", "Absent": "/", "Inquiries": "/", "Packages": "/bill", "Staff": "/", "Reports": "/today"}
    body = ('<div class="panel"><h2>%s</h2><p class="dim">This screen is being built next, exactly as in the approved design. '
            'Until then use <a href="%s">this page</a>.</p></div>' % (e(name), links.get(name, "/")))
    nav = {"Attendance": "/soon?p=Attendance", "Absent": "/soon?p=Absent", "Inquiries": "/soon?p=Inquiries",
           "Packages": "/soon?p=Packages", "Staff": "/soon?p=Staff", "Reports": "/soon?p=Reports"}.get(name, "")
    return shell(name, nav, body, sub="Coming next", cnt=counts(conn, sn))


# ---------------- attendance import ----------------

def parse_time(t):
    t = (t or "").strip()
    for fmt in ("%I:%M:%S %p", "%I:%M %p", "%H:%M:%S", "%H:%M"):
        try:
            return datetime.datetime.strptime(t, fmt).strftime("%H:%M:%S")
        except ValueError:
            pass
    return None


def import_attendance(conn, sn, text):
    """Old software's attendance (CSV: date, in time, out time, biometric id). Safe to re-run."""
    if not sn:
        return 0, 0, "No gate machine connected yet."
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    added = skipped = 0
    for r in reader:
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        pin = r.get("biometric / client id") or r.get("biometric id") or r.get("pin") or r.get("member id") or ""
        d = M.parse_date(r.get("date"))
        if not pin.isdigit() or not d:
            skipped += 1
            continue
        for col, status in (("in time", "0"), ("out time", "1")):
            tm = parse_time(r.get(col))
            if tm:
                cur = conn.execute("INSERT OR IGNORE INTO punches (sn, pin, ts, status, verify, raw, received_at) "
                                   "VALUES (?,?,?,?,?,?,?)", (sn, pin, "%s %s" % (M.iso(d), tm), status, "old",
                                                               "old software", M.stamp()))
                added += cur.rowcount
    return added, skipped, ""


# ---------------- part B: attendance, renewals, pending, absent ----------------

def staff_names(conn, sn):
    return {p: n for p, n in M.machine_names(conn, sn).items() if p.isdigit() and int(p) >= STAFF_FROM}


def member_names(conn):
    return {str(r[0]): r[1] for r in conn.execute("SELECT client_id, name FROM members")}


def log_reminder(conn, cid, kind):
    conn.execute("CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY, client_id INTEGER, kind TEXT, at TEXT)")
    conn.execute("INSERT INTO reminders (client_id, kind, at) VALUES (?,?,?)", (cid, kind, M.stamp()))


def last_reminders(conn, kind):
    conn.execute("CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY, client_id INTEGER, kind TEXT, at TEXT)")
    return {r[0]: r[1] for r in conn.execute("SELECT client_id, MAX(at) FROM reminders WHERE kind=? GROUP BY client_id", (kind,))}


def remind_link(cid, kind):
    """Through our server so the reminder is logged, then on to WhatsApp."""
    return "/r?" + urlencode({"id": cid, "k": kind})


def remind_redirect(conn, q):
    cid = q.get("id", "")
    m = conn.execute("SELECT * FROM members WHERE client_id=?", (cid,)).fetchone() if cid.isdigit() else None
    if not m:
        return "/members"
    kind = q.get("k", "renew")
    text = {"renew": renew_msg, "absent": absent_msg, "due": due_msg}.get(kind, renew_msg)(m)
    link = wa(m["phone"], text)
    if not link:
        return "/m?" + urlencode({"id": cid, "m": "No valid phone number for this member."})
    log_reminder(conn, m["client_id"], kind)
    return link


def due_msg(m):
    return ("Hi %s, House of Strength me aapka %s baaki hai. Agli visit pe reception pe clear kar dijiye. "
            "Thank you!") % (nice(m["name"]), money(m["pending"]))


def remind_btn(m, kind):
    if not phone_ok(m):
        return ""
    return ('<a class="ibtn wa" href="%s" target="_blank" rel="noopener" aria-label="WhatsApp %s">%s</a>'
            % (remind_link(m["client_id"], kind), e(m["name"] or ""), icon("chat", 16))) if m["phone"] else ""


def sel_box(cid):
    return '<input type="checkbox" name="id" value="%d" aria-label="Select" style="width:18px;height:18px;min-height:0;accent-color:#e10600">' % cid


# ---------- attendance ----------

def attendance(conn, sn, q):
    t = M.today()
    ti = M.iso(t)
    tab = q.get("t", "members")
    mn = member_names(conn)
    sn_names = staff_names(conn, sn)
    today_rows = conn.execute("SELECT pin, ts, status FROM punches WHERE sn=? AND substr(ts,1,10)=? ORDER BY ts DESC",
                              (sn, ti)).fetchall()
    mem_today = {r[0] for r in today_rows if is_member(r[0])}
    staff_today = {r[0] for r in today_rows if not is_member(r[0])}
    now = datetime.datetime.now()
    recent = {r[0] for r in today_rows if is_member(r[0]) and r[2] != "1" and
              (now - datetime.datetime.strptime(r[1], "%Y-%m-%d %H:%M:%S")).total_seconds() <= 5400}
    staff_30 = {r[0] for r in conn.execute("SELECT DISTINCT pin FROM punches WHERE CAST(pin AS INT) >= ? AND ts >= ?",
                                           (STAFF_FROM, M.iso(t - datetime.timedelta(days=30))))}
    month_n = conn.execute("SELECT COUNT(DISTINCT pin || substr(ts,1,10)) FROM punches WHERE substr(ts,1,7)=? AND CAST(pin AS INT) < ?",
                           (ti[:7], STAFF_FROM)).fetchone()[0]
    live = "".join(
        '<tr><td style="white-space:normal;padding-left:0"><a class="mem" href="%s"><span class="av">%s</span>%s</a></td><td class="dim" style="padding:11px 6px">%s</td>'
        '<td style="text-align:right;padding-right:0"><b>%s</b></td></tr>' % (
            "/m?id=%s" % r[0] if is_member(r[0]) else "#", initials(mn.get(r[0]) or sn_names.get(r[0], r[0])),
            e(nice(mn.get(r[0]) or sn_names.get(r[0]) or "ID %s" % r[0])),
            "Out" if r[2] == "1" else ("In" if is_member(r[0]) else "Staff"),
            datetime.datetime.strptime(r[1], "%Y-%m-%d %H:%M:%S").strftime("%I:%M %p").lstrip("0"))
        for r in today_rows[:14]) or '<tr><td class="dim">No check-ins yet today.</td></tr>'
    # busy hours: last 28 days, weekday x hour, distinct member visits
    heat = {}
    for wd, h, n in conn.execute(
            "SELECT CAST(strftime('%w', substr(ts,1,10)) AS INT), CAST(substr(ts,12,2) AS INT), COUNT(DISTINCT pin || substr(ts,1,10)) "
            "FROM punches WHERE ts >= ? AND CAST(pin AS INT) < ? AND status != '1' GROUP BY 1, 2",
            (M.iso(t - datetime.timedelta(days=28)), STAFF_FROM)):
        heat[(wd, h)] = n
    top = max(heat.values() or [1])
    hours = list(range(6, 23))
    days = [(1, "Mon"), (2, "Tue"), (3, "Wed"), (4, "Thu"), (5, "Fri"), (6, "Sat"), (0, "Sun")]
    grid = '<div style="display:grid;grid-template-columns:40px repeat(%d,minmax(0,1fr));gap:4px;font-size:11px;color:var(--muted)"><span></span>%s%s</div>' % (
        len(hours), "".join('<span style="text-align:center">%d%s</span>' % ((h - 1) % 12 + 1, "a" if h < 12 else "p") for h in hours),
        "".join('<span>%s</span>%s' % (dn, "".join(
            '<i title="%s %d:00 · %d" style="height:26px;border-radius:5px;background:rgba(225,6,0,%.2f)"></i>' % (
                dn, h, heat.get((wd, h), 0), 0.08 + 0.92 * heat.get((wd, h), 0) / top) for h in hours)) for wd, dn in days))
    # per month
    if tab == "members":
        rows = conn.execute("SELECT substr(ts,1,7) m, COUNT(DISTINCT pin || substr(ts,1,10)) FROM punches "
                            "WHERE CAST(pin AS INT) < ? AND status != '1' GROUP BY m ORDER BY m", (STAFF_FROM,)).fetchall()[-12:]
        lower = '<div class="panel"><div class="ph"><h2>Member check-ins per month</h2></div>%s</div>' % bars(
            [(datetime.datetime.strptime(m + "-01", "%Y-%m-%d").strftime("%b"), n) for m, n in rows], lambda l, v: True)
    else:
        staff_rows = []
        for pin, name in sorted(sn_names.items(), key=lambda x: x[1].lower()):
            n30 = conn.execute("SELECT COUNT(DISTINCT substr(ts,1,10)) FROM punches WHERE pin=? AND ts >= ?",
                               (pin, M.iso(t - datetime.timedelta(days=30)))).fetchone()[0]
            if n30 == 0 and tab != "all":
                continue
            first = conn.execute("SELECT MIN(ts), MAX(ts) FROM punches WHERE pin=? AND substr(ts,1,10)=?", (pin, ti)).fetchone()
            staff_rows.append('<tr><td><span class="mem"><span class="av">%s</span>%s</span></td><td class="dim">ID %s</td>'
                              '<td>%d / 30</td><td>%s</td></tr>' % (
                                  initials(name), e(nice(name)), pin, n30,
                                  ('<span class="pill p-ok">In %s</span>' % first[0][11:16]) if first[0] else '<span class="pill p-dim">Not in</span>'))
        lower = ('<div class="panel"><div class="ph"><h2>Staff &amp; trainers · last 30 days</h2><a href="/attendance?t=all">Show all</a></div>'
                 '<div class="tw"><table><tr><th>Name</th><th>ID</th><th>Present</th><th>Today</th></tr>%s</table></div></div>'
                 % ("".join(staff_rows) or '<tr><td class="dim">No staff check-ins in the last 30 days.</td></tr>'))
    tabs = "".join('<a href="/attendance?t=%s"%s>%s</a>' % (k, ' class="on"' if tab == k or (k == "staff" and tab == "all") else "", l)
                   for k, l in (("members", "Members"), ("staff", "Staff & trainers")))
    body = """<div class="kpis">
<div class="kpi hot"><div class="l">Inside now</div><div class="v">%d</div><div class="s">checked in during the last 90 min</div></div>
<div class="kpi"><div class="l">Today</div><div class="v">%d</div><div class="s">member check-ins</div></div>
<div class="kpi"><div class="l">Staff present</div><div class="v">%d / %d</div><div class="s">came in the last 30 days</div></div>
<div class="kpi"><div class="l">This month</div><div class="v">%s</div><div class="s">member visits since 1 %s</div></div></div>
<div class="two" style="grid-template-columns:repeat(auto-fit,minmax(360px,1fr))"><div class="panel" style="min-width:0"><div class="ph"><h2>Live check-ins</h2><span class="pill p-ok">%s</span></div>
<div class="tw"><table>%s</table></div></div><div class="panel"><div class="ph"><h2>Busy hours · last 4 weeks</h2></div>%s
<p class="dim" style="margin:12px 0 0;font-size:12px">Darker = more members.</p></div></div>
<div class="tabs">%s</div>%s
<details class="panel"><summary style="cursor:pointer;font-weight:600">Manual check-in</summary>
<form method="post" action="/attendance/manual" class="row" style="margin-top:12px"><input name="member" list="mlist2" placeholder="Member name or ID" required style="min-width:280px">
<datalist id="mlist2">%s</datalist><button>Check in now</button></form>
<p class="dim" style="font-size:12px">Use when the finger does not read. It is saved as a manual entry.</p></details>""" % (
        len(recent), len(mem_today), len(staff_today), len(staff_30) or len(sn_names), inr(month_n), t.strftime("%b"),
        "Biometric connected" if gate_online(conn) else "Gate offline", live, grid, tabs, lower,
        "".join('<option value="%s · %s">' % (e(nice(n)), member_id(c)) for c, n in conn.execute(
            "SELECT client_id, name FROM members WHERE expiry >= ? ORDER BY name", (ti,))))
    actions = admin_only('<a class="btn red" href="/attendance.csv">%sExport</a>' % icon("down"))
    return shell("Attendance", "/attendance", body, sub="Live from the biometric device", actions=actions,
                 msg=q.get("m", ""), cnt=counts(conn, sn))


def gate_online(conn):
    row = conn.execute("SELECT MAX(last_seen) FROM devices").fetchone()
    if not row or not row[0]:
        return False
    return (datetime.datetime.now() - datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")).total_seconds() < 300


def attendance_csv(conn, sn, q):
    mn = member_names(conn)
    sname = staff_names(conn, sn)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Date", "Time", "ID", "Name", "Type", "In/Out", "Source"])
    for pin, ts, st, ver in conn.execute("SELECT pin, ts, status, verify FROM punches ORDER BY ts DESC"):
        w.writerow([ts[:10], ts[11:19], pin, nice(mn.get(pin) or sname.get(pin, "")),
                    "Member" if is_member(pin) else "Staff", "Out" if st == "1" else "In",
                    {"old": "Old software", "manual": "Manual"}.get(ver, "Gate")])
    return "﻿" + buf.getvalue()


def manual_checkin(conn, sn, f):
    m = resolve_member(conn, f.get("member"))
    if not m:
        return "Member not found."
    conn.execute("INSERT OR IGNORE INTO punches (sn, pin, ts, status, verify, raw, received_at) VALUES (?,?,?,?,?,?,?)",
                 (sn or "manual", str(m["client_id"]), M.stamp(), "0", "manual", "manual check-in", M.stamp()))
    return "Checked in %s." % nice(m["name"])


# ---------- renewals ----------

def pkg_price(conn):
    return {r[0].lower(): r[1] for r in conn.execute("SELECT name, price FROM packages")}


def renewals(conn, sn, q):
    t = M.today()
    ti = M.iso(t)
    tab = q.get("t", "week")
    prices = pkg_price(conn)
    sent = last_reminders(conn, "renew")
    rng = {"today": (t, t), "week": (t, t + datetime.timedelta(days=7)), "month": (t, t + datetime.timedelta(days=30)),
           "expired": (t - datetime.timedelta(days=30), t - datetime.timedelta(days=1))}

    def members_in(a, b):
        return conn.execute("SELECT * FROM members WHERE expiry BETWEEN ? AND ? ORDER BY expiry", (M.iso(a), M.iso(b))).fetchall()

    def value(ms):
        return sum(prices.get((m["package"] or "").lower(), 0) for m in ms)

    sets = {k: members_in(*v) for k, v in rng.items()}
    cut = M.iso(t - datetime.timedelta(days=30))
    total = conn.execute("SELECT COUNT(*) FROM members WHERE registration != '' AND registration <= ?", (cut,)).fetchone()[0]
    renewed = conn.execute("SELECT COUNT(*) FROM members WHERE registration != '' AND registration <= ? AND expiry >= ?",
                           (cut, ti)).fetchone()[0]
    rows = sets.get(tab, sets["week"])
    trs = "".join(
        '<tr><td>%s</td><td><a class="mem" href="/m?id=%d"><span class="av">%s</span>%s</a></td><td>%s</td><td>%s</td><td>%s</td>'
        '<td>%s</td><td class="dim">%s</td><td style="display:flex;gap:6px;justify-content:flex-end">%s<a class="btn red sm" href="/bill?id=%d">Renew</a></td></tr>' % (
            sel_box(m["client_id"]), m["client_id"], initials(m["name"]), e(nice(m["name"])), e(m["package"] or ""),
            short_date(m["expiry"])[:6], due_pill(m["expiry"]),
            money(prices.get((m["package"] or "").lower(), 0)) if prices.get((m["package"] or "").lower()) else "—",
            ("Sent %s" % M.parse_date(sent[m["client_id"]][:10]).strftime("%d %b")) if m["client_id"] in sent else "Not sent",
            remind_btn(m, "renew"), m["client_id"]) for m in rows) or '<tr><td colspan="8" class="dim">Nobody in this list.</td></tr>'
    tabs = "".join('<a href="/renewals?t=%s"%s>%s %d</a>' % (k, ' class="on"' if k == tab else "", l, len(sets[k]))
                   for k, l in (("today", "Today"), ("week", "This week"), ("month", "This month"), ("expired", "Expired")))
    body = """<div class="kpis">
<a class="kpi hot" href="/renewals?t=today"><div class="l">Due today</div><div class="v">%d</div><div class="s">%s</div></a>
<a class="kpi" href="/renewals?t=week"><div class="l">Next 7 days</div><div class="v">%d</div><div class="s">%s value</div></a>
<a class="kpi" href="/renewals?t=expired"><div class="l">Expired last 30 days</div><div class="v">%d</div><div class="s">not renewed yet</div></a>
<div class="kpi"><div class="l">Retention</div><div class="v">%d%%</div><div class="s">%d of %d who joined 30+ days ago are active</div></div></div>
<form class="panel" method="get" action="/remind"><input type="hidden" name="k" value="renew"><div class="ph"><div class="tabs">%s</div>
<div class="acts"><button class="btn red sm">Remind selected on WhatsApp</button>%s</div></div>
<div class="tw"><table><tr><th></th><th>Member</th><th>Package</th><th>Expiry</th><th>Due in</th><th>Renewal value</th><th>Reminder</th><th></th></tr>%s</table></div></form>""" % (
        len(sets["today"]), money(value(sets["today"])), len(sets["week"]), money(value(sets["week"])), len(sets["expired"]),
        round(100 * renewed / max(1, total)), renewed, total, tabs,
        admin_only('<a class="btn sm" href="/renewals.csv?t=%s">%sExport Excel</a>' % (tab, icon("down", 16))), trs)
    return shell("Renewals", "/renewals", body, sub="Who needs to renew, and one-tap reminders", msg=q.get("m", ""),
                 cnt=counts(conn, sn))


def remind_queue(conn, sn, q, ids):
    """Selected members, one WhatsApp button each (WhatsApp opens one chat at a time)."""
    kind = q.get("k", "renew")
    ms = [conn.execute("SELECT * FROM members WHERE client_id=?", (i,)).fetchone() for i in ids if str(i).isdigit()]
    ms = [m for m in ms if m]
    rows = "".join(
        '<tr><td>%d</td><td><span class="mem"><span class="av">%s</span>%s</span></td><td class="dim">%s</td>'
        '<td style="text-align:right"><a class="btn sm red" href="%s" target="_blank" rel="noopener" onclick="this.textContent=\'Opened\';this.classList.remove(\'red\')">%sSend</a></td></tr>' % (
            i + 1, initials(m["name"]), e(nice(m["name"])), e(m["phone"] or "no phone"), remind_link(m["client_id"], kind),
            icon("chat", 16)) for i, m in enumerate(ms) if m["phone"]) or '<tr><td class="dim">Nobody selected.</td></tr>'
    body = ('<div class="panel"><p class="dim">Tap Send on each row: WhatsApp opens with the message ready, press send there, '
            'come back and tap the next one.</p><table>%s</table></div>' % rows)
    back = {"renew": "/renewals", "absent": "/absent", "due": "/pending"}.get(kind, "/")
    return shell("Send reminders", back, body, sub="%d members" % len(ms), cnt=counts(conn, sn))


def renewals_csv(conn, sn, q):
    t = M.today()
    tab = q.get("t", "week")
    a, b = {"today": (t, t), "week": (t, t + datetime.timedelta(days=7)), "month": (t, t + datetime.timedelta(days=30)),
            "expired": (t - datetime.timedelta(days=30), t - datetime.timedelta(days=1))}.get(tab, (t, t + datetime.timedelta(days=7)))
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Member ID", "Name", "Phone", "Package", "Expiry"])
    for m in conn.execute("SELECT * FROM members WHERE expiry BETWEEN ? AND ? ORDER BY expiry", (M.iso(a), M.iso(b))):
        w.writerow([member_id(m["client_id"]), nice(m["name"]), m["phone"], m["package"], short_date(m["expiry"])])
    return "﻿" + buf.getvalue()


# ---------- pending ----------

def pending_since(conn):
    out = {}
    for cid, d in conn.execute("SELECT client_id, MIN(paid_on) FROM payments WHERE balance > 0 GROUP BY client_id"):
        out[cid] = M.parse_date(d)
    return out


def pending(conn, sn, q):
    t = M.today()
    since = pending_since(conn)
    ms = conn.execute("SELECT * FROM members WHERE pending > 0").fetchall()
    ms = sorted(ms, key=lambda m: since.get(m["client_id"]) or t)
    total = sum(m["pending"] for m in ms)
    old = [m for m in ms if since.get(m["client_id"]) and (t - since[m["client_id"]]).days > 90]
    col = conn.execute("SELECT COALESCE(SUM(amount),0), COUNT(*) FROM payments WHERE substr(paid_on,1,7)=?", (M.iso(t)[:7],)).fetchone()
    trs = ""
    for m in ms:
        s = since.get(m["client_id"])
        od = (t - s).days if s else None
        cls = "p-bad" if od and od > 90 else ("p-warn" if od and od > 30 else "p-dim")
        trs += ('<tr><td>%s</td><td><a class="mem" href="/m?id=%d"><span class="av">%s</span>%s</a></td><td>%s</td><td>%s</td>'
                '<td><b>%s</b></td><td><span class="pill %s">%s</span></td><td style="display:flex;gap:6px;justify-content:flex-end">%s'
                '<a class="btn red sm" href="/collect?id=%d">Collect</a></td></tr>') % (
            sel_box(m["client_id"]), m["client_id"], initials(m["name"]), e(nice(m["name"])), short_date(M.iso(s)) if s else "—",
            e(m["package"] or ""), money(m["pending"]), cls, ("%d days" % od) if od is not None else "—",
            remind_btn(m, "due"), m["client_id"])
    body = """<div class="kpis"><div class="kpi hot"><div class="l">Total pending</div><div class="v">%s</div><div class="s">%d members</div></div>
<div class="kpi"><div class="l">Older than 90 days</div><div class="v">%s</div><div class="s">%d members</div></div>
<div class="kpi"><div class="l">Collected this month</div><div class="v">%s</div><div class="s">%d bills</div></div></div>
<form class="panel" method="get" action="/remind"><input type="hidden" name="k" value="due"><div class="ph"><h2>Pending dues</h2>
<div class="acts"><button class="btn red sm">Remind selected</button>%s</div></div>
<div class="tw"><table><tr><th></th><th>Member</th><th>Since</th><th>Package</th><th>Amount due</th><th>Overdue</th><th></th></tr>%s</table></div></form>""" % (
        money(total), len(ms), money(sum(m["pending"] for m in old)), len(old), money(col[0]), col[1],
        admin_only('<a class="btn sm" href="/pending.csv">%sExport Excel</a>' % icon("down", 16)),
        trs or '<tr><td colspan="7" class="dim">No pending dues.</td></tr>')
    return shell("Pending payments", "/pending", body, sub="Balance left on bills, oldest first", msg=q.get("m", ""),
                 cnt=counts(conn, sn))


def pending_csv(conn, sn, q):
    since = pending_since(conn)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Member ID", "Name", "Phone", "Package", "Pending", "Since"])
    for m in conn.execute("SELECT * FROM members WHERE pending > 0 ORDER BY pending DESC"):
        s = since.get(m["client_id"])
        w.writerow([member_id(m["client_id"]), nice(m["name"]), m["phone"], m["package"], "%g" % m["pending"],
                    s.strftime("%d-%m-%Y") if s else ""])
    return "﻿" + buf.getvalue()


def collect_page(conn, sn, q):
    cid = q.get("id", "")
    m = conn.execute("SELECT * FROM members WHERE client_id=?", (cid,)).fetchone() if cid.isdigit() else None
    if not m:
        return shell("Collect", "/pending", '<div class="panel">Member not found.</div>', cnt=counts(conn, sn))
    body = """<form class="panel" method="post" action="/collect" style="max-width:560px;display:flex;flex-direction:column;gap:16px">
<input type="hidden" name="id" value="%d"><div class="mem" style="font-size:16px"><span class="av">%s</span>%s · %s</div>
<p style="margin:0">Pending: <b>%s</b></p><div class="grid">
<label>Amount received (₹)<input name="amount" inputmode="decimal" value="%g" required></label>
<label>Payment mode<select name="mode"><option>UPI</option><option>Cash</option><option>Card</option><option>Online</option></select></label></div>
<button class="btn red">Save payment</button></form>""" % (m["client_id"], initials(m["name"]), e(nice(m["name"])),
                                                           member_id(m["client_id"]), money(m["pending"]), m["pending"] or 0)
    return shell("Collect payment", "/pending", body, sub="Clear a pending balance", cnt=counts(conn, sn))


def save_collect(conn, f):
    cid = f.get("id", "")
    m = conn.execute("SELECT * FROM members WHERE client_id=?", (cid,)).fetchone() if cid.isdigit() else None
    amt = num(f.get("amount"))
    if not m or amt <= 0:
        return None, "Enter an amount."
    n = int(M.setting(conn, "next_invoice", "1242"))
    inv = "%s%05d" % (M.setting(conn, "invoice_prefix", "HOS-"), n)
    M.set_setting(conn, "next_invoice", n + 1)
    left = max(0.0, (m["pending"] or 0) - amt)
    conn.execute(
        "INSERT INTO payments (client_id, paid_on, amount, mode, package, start, expiry, note, created_at, invoice, "
        "list_price, discount, admission, gst, payable, balance, trainer, kind, created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (m["client_id"], M.iso(M.today()), amt, f.get("mode", ""), "Due payment", "", "", "pending cleared", M.stamp(), inv,
         m["pending"] or 0, 0, 0, 0, m["pending"] or 0, left, "", "due", staff_name()))
    conn.execute("UPDATE payments SET balance=0 WHERE client_id=? AND balance > 0 AND invoice IS NOT ?", (m["client_id"], inv))
    conn.execute("UPDATE members SET pending=?, updated_at=? WHERE client_id=?", (left, M.stamp(), m["client_id"]))
    return inv, "Received %s from %s. Left: %s." % (money(amt), nice(m["name"]), money(left))


# ---------- absent ----------

def absent(conn, sn, q):
    d = q.get("d", "7")
    d = int(d) if d.isdigit() else 7
    lists = {n: absent_list(conn, sn, n) for n in (3, 7, 14, 30)}
    rows = lists.get(d) or absent_list(conn, sn, d)
    trs = "".join(
        '<tr><td>%s</td><td><a class="mem" href="/m?id=%d"><span class="av">%s</span>%s</a></td><td>%s</td><td>%s</td><td>%s</td>'
        '<td>%s</td><td style="display:flex;gap:6px;justify-content:flex-end">%s%s</td></tr>' % (
            sel_box(m["client_id"]), m["client_id"], initials(m["name"]), e(nice(m["name"])), e(m["package"] or ""),
            ("%d days ago" % days) if last else "No visit since %s" % tracking_start(conn).strftime("%d %b"),
            status_pill(m["expiry"]), '<span class="pill %s">%s</span>' % (("p-bad", "At risk") if days >= 14 else ("p-warn", "Check in")),
            remind_btn(m, "absent"), call_btn(m)) for days, last, m in rows
    ) or '<tr><td colspan="7" class="dim">Nobody.</td></tr>'
    tabs = "".join('<a href="/absent?d=%d"%s>%d+ days</a>' % (n, ' class="on"' if n == d else "", n) for n in (3, 7, 14, 30))
    body = """<div class="kpis"><a class="kpi hot" href="/absent?d=3"><div class="l">Absent 3+ days</div><div class="v">%d</div><div class="s">active members</div></a>
<a class="kpi" href="/absent?d=7"><div class="l">Absent 7+ days</div><div class="v">%d</div><div class="s">message them</div></a>
<a class="kpi" href="/absent?d=14"><div class="l">Absent 14+ days</div><div class="v">%d</div><div class="s">likely to quit</div></a></div>
<form class="panel" method="get" action="/remind"><input type="hidden" name="k" value="absent"><div class="ph"><div class="tabs">%s</div>
<button class="btn red sm">Message selected on WhatsApp</button></div>
<div class="tw"><table><tr><th></th><th>Member</th><th>Package</th><th>Last visit</th><th>Plan</th><th>Risk</th><th></th></tr>%s</table></div></form>""" % (
        len(lists[3]), len(lists[7]), len(lists[14]), tabs, trs)
    return shell("Absent members", "/absent", body, sub="Active members who stopped coming, from biometric data",
                 msg=q.get("m", ""), cnt=counts(conn, sn))


# ---------------- trainer ----------------

def trainer_page(conn, sn, q):
    me_ = A.me()
    tname = (me_.get("trainer") or me_.get("name") or "").strip().lower()
    t = M.today()
    rows = conn.execute(
        "SELECT p.client_id, MAX(p.expiry) pt_end, m.* FROM payments p JOIN members m ON m.client_id = p.client_id "
        "WHERE lower(trim(p.trainer)) = ? AND p.trainer != '' GROUP BY p.client_id ORDER BY pt_end DESC", (tname,)).fetchall()
    trs = ""
    for r in rows:
        end = M.parse_date(r["pt_end"])
        visits = conn.execute("SELECT COUNT(DISTINCT substr(ts,1,10)) FROM punches WHERE pin=? AND ts >= ?",
                              (str(r["client_id"]), M.iso(t - datetime.timedelta(days=30)))).fetchone()[0]
        active = end and end >= t
        trs += ('<tr><td><span class="mem"><span class="av">%s</span>%s</span></td><td>%s</td><td>%s</td><td>%s</td><td>%d / 30</td>'
                '<td>%s</td></tr>') % (initials(r["name"]), e(nice(r["name"])), e(r["package"] or ""), short_date(r["pt_end"]),
                                       '<span class="pill p-ok">Active</span>' if active else '<span class="pill p-dim">Ended</span>',
                                       visits, ('<a class="ibtn" href="tel:%s" aria-label="Call">%s</a>' % (e(r["phone"] or ""), icon("phone", 16)))
                                       if active and r["phone"] else "")
    body = ('<div class="panel"><div class="ph"><h2>My PT clients</h2><span class="dim">%d</span></div><div class="tw"><table>'
            '<tr><th>Client</th><th>Package</th><th>PT ends</th><th>Status</th><th>Visits (30 d)</th><th></th></tr>%s</table></div></div>'
            % (len(rows), trs or '<tr><td colspan="6" class="dim">No PT clients linked to your name yet.</td></tr>'))
    init_staff(conn)
    st = conn.execute("SELECT s.*, sh.name sname, sh.start, sh.end, sh.days FROM staff s LEFT JOIN shifts sh ON sh.id = s.shift_id "
                      "WHERE lower(trim(s.name)) = ?", (tname,)).fetchone()
    if st and st["sname"]:
        body = ('<div class="kpis"><div class="kpi hot"><div class="l">My shift</div><div class="v" style="font-size:28px">%s</div>'
                '<div class="s">%s – %s · %s</div></div></div>' % (e(st["sname"]), fmt_t(st["start"]), fmt_t(st["end"]),
                                                               " ".join(WEEKDAYS[int(c)] for c in (st["days"] or ""))) + body)
    return shell("My PT clients", "/trainer", body, sub="Trainer: %s" % e(me_.get("trainer") or me_.get("name") or ""))


# ---------------- reports ----------------

EXPENSE_CATS = ["Rent", "Electricity", "Salaries", "Equipment", "Repairs", "Marketing", "Cleaning", "Other"]


def init_expenses(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY, spent_on TEXT, category TEXT, amount REAL,
        paid_to TEXT, mode TEXT, note TEXT, created_by TEXT, created_at TEXT)""")


def period(q):
    t = M.today()
    p = q.get("p", "month")
    if p == "last":
        end = t.replace(day=1) - datetime.timedelta(days=1)
        return p, end.replace(day=1), end, end.strftime("%B %Y")
    if p == "year":
        return p, t.replace(month=1, day=1), t, "This year"
    if p == "all":
        return p, datetime.date(2015, 1, 1), t, "All time"
    if p == "custom":
        a, b = M.parse_date(q.get("from")), M.parse_date(q.get("to"))
        if a and b and a <= b:
            return p, a, b, "%s – %s" % (a.strftime("%d %b %Y"), b.strftime("%d %b %Y"))
    return "month", t.replace(day=1), t, t.strftime("%B %Y")


def reports(conn, sn, q):
    init_expenses(conn)
    p, a, b, label = period(q)
    A_, B_ = M.iso(a), M.iso(b)
    col = conn.execute("SELECT COALESCE(SUM(amount),0), COUNT(*) FROM payments WHERE paid_on BETWEEN ? AND ?", (A_, B_)).fetchone()
    bills = conn.execute("SELECT COUNT(*) FROM payments WHERE paid_on BETWEEN ? AND ? AND kind != 'due'", (A_, B_)).fetchone()[0]
    newm = conn.execute("SELECT COUNT(*) FROM members WHERE registration BETWEEN ? AND ?", (A_, B_)).fetchone()[0]
    visits = conn.execute("SELECT COUNT(DISTINCT pin || substr(ts,1,10)) FROM punches WHERE substr(ts,1,10) BETWEEN ? AND ? "
                          "AND CAST(pin AS INT) < ? AND status != '1'", (A_, B_, STAFF_FROM)).fetchone()[0]
    exp = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE spent_on BETWEEN ? AND ?", (A_, B_)).fetchone()[0]
    sal = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE spent_on BETWEEN ? AND ? AND category='Salaries'",
                       (A_, B_)).fetchone()[0]
    pk = conn.execute("SELECT lower(trim(package)) p, COUNT(*) n FROM payments WHERE paid_on BETWEEN ? AND ? AND kind != 'due' "
                      "GROUP BY p ORDER BY n DESC", (A_, B_)).fetchall()
    top = pk[:5]
    others = sum(r[1] for r in pk[5:])
    most = max([r[1] for r in pk] + [1])
    buy = "".join('<div style="display:flex;align-items:center;gap:12px;margin:8px 0"><span style="width:130px">%s</span>'
                  '<span style="flex:1;height:10px;background:var(--card2);border-radius:5px;overflow:hidden"><i style="display:block;height:100%%;width:%d%%;background:var(--red)"></i></span>'
                  '<b style="width:40px;text-align:right">%d</b></div>' % (e(nice(n)), int(100 * c / most), c)
                  for n, c in top + ([("Others", others)] if others else [])) or '<p class="dim">No bills in this period.</p>'
    disc = conn.execute("SELECT COALESCE(SUM(list_price),0), COALESCE(SUM(payable),0), SUM(discount > 0), COUNT(*) FROM payments "
                        "WHERE paid_on BETWEEN ? AND ? AND kind != 'due'", (A_, B_)).fetchone()
    modes = conn.execute("SELECT COALESCE(NULLIF(mode,''),'Not recorded'), COALESCE(SUM(amount),0), COUNT(*) FROM payments "
                         "WHERE paid_on BETWEEN ? AND ? GROUP BY 1 ORDER BY 2 DESC", (A_, B_)).fetchall()
    days = conn.execute("SELECT paid_on, COALESCE(SUM(amount),0), COUNT(*) FROM payments WHERE paid_on BETWEEN ? AND ? "
                        "GROUP BY paid_on ORDER BY paid_on DESC LIMIT 62", (A_, B_)).fetchall()
    tabs = "".join('<a href="/reports?p=%s"%s>%s</a>' % (k, ' class="on"' if k == p else "", l)
                   for k, l in (("month", "This month"), ("last", "Last month"), ("year", "This year"), ("all", "All time")))
    custom = ('<form method="get" action="/reports" class="row" style="margin:0"><input type="hidden" name="p" value="custom">'
              '<input type="date" name="from" value="%s" aria-label="From"><input type="date" name="to" value="%s" aria-label="To">'
              '<button class="btn sm">Custom</button></form>' % (A_ if p == "custom" else "", B_ if p == "custom" else ""))
    rng = urlencode({"from": A_, "to": B_})
    dl = [("Collection", "Day-wise money in", "/reports/collection.csv?" + rng), ("Bills", "Every bill with discount & balance", "/reports/bills.csv?" + rng),
          ("Members", "Full member list", "/members.csv"), ("Attendance", "Members, staff, trainers", "/attendance.csv"),
          ("Renewals", "Due this month", "/renewals.csv?t=month"), ("Pending dues", "Who owes what", "/pending.csv"),
          ("Expenses", "Every expense", "/reports/expenses.csv?" + rng)]
    downloads = "".join('<a class="kpi" href="%s" style="display:flex;justify-content:space-between;align-items:center;gap:10px">'
                        '<span><b>%s</b><br><span class="dim" style="font-size:12px">%s</span></span>%s</a>' % (h, t_, s_, icon("down"))
                        for t_, s_, h in dl)
    profit = col[0] - exp
    body = """<div class="ph" style="flex-wrap:wrap"><div class="tabs">%s</div>%s</div>
<div class="kpis"><div class="kpi hot"><div class="l">Collection</div><div class="v">%s</div><div class="s">%s</div></div>
<div class="kpi"><div class="l">Bills</div><div class="v">%s</div><div class="s">avg %s</div></div>
<div class="kpi"><div class="l">New members</div><div class="v">%s</div><div class="s">joined in this period</div></div>
<div class="kpi"><div class="l">Check-ins</div><div class="v">%s</div><div class="s">member visits</div></div></div>
<div class="kpis"><div class="kpi"><div class="l">Expenses</div><div class="v">%s</div><div class="s">of which salaries %s</div></div>
<div class="kpi" style="%s"><div class="l">Profit</div><div class="v">%s</div><div class="s">collection − expenses (incl. salaries)</div></div>
<a class="kpi" href="/expenses"><div class="l">Add expenses</div><div class="v" style="font-size:22px;margin-top:14px">Open expenses →</div><div class="s">rent, bijli, salary…</div></a></div>
<div class="two"><div class="panel"><div class="ph"><h2>What members buy · %d bills</h2></div>%s</div>
<div class="panel"><div class="ph"><h2>Discount check</h2></div><div class="kpis" style="grid-template-columns:repeat(2,minmax(0,1fr))">
<div class="kpi"><div class="l">List price</div><div class="v">%s</div><div class="s">%d bills</div></div>
<div class="kpi"><div class="l">Actually billed</div><div class="v">%s</div><div class="s">after discount</div></div></div>
<p class="dim" style="margin:12px 0 0">%d of %d bills had a discount%s. Reception's limit is set in Settings.</p></div></div>
<div class="two"><div class="panel"><div class="ph"><h2>By payment mode</h2></div><table><tr><th>Mode</th><th>Bills</th><th style="text-align:right">Amount</th></tr>%s</table></div>
<div class="panel"><div class="ph"><h2>Day by day</h2></div><div class="tw" style="max-height:360px;overflow-y:auto"><table><tr><th>Date</th><th>Bills</th><th style="text-align:right">Amount</th></tr>%s</table></div></div></div>
<div class="panel"><div class="ph"><h2>Download reports (Excel)</h2></div><div class="kpis">%s</div></div>""" % (
        tabs, custom, money(col[0]), e(label), inr(bills), money(col[0] / bills) if bills else "₹0", inr(newm), inr(visits),
        money(exp), money(sal), "border-color:#14532d" if profit >= 0 else "border-color:#7f1d1d", money(profit),
        bills, buy, money(disc[0]), disc[3] or 0, money(disc[1]), disc[2] or 0, disc[3] or 0,
        (" (avg %d%% off list)" % round(100 * (1 - disc[1] / disc[0]))) if disc[0] else "",
        "".join("<tr><td>%s</td><td>%d</td><td style=\"text-align:right\">%s</td></tr>" % (e(m_), n, money(v)) for m_, v, n in modes)
        or '<tr><td class="dim" colspan="3">—</td></tr>',
        "".join("<tr><td>%s</td><td>%d</td><td style=\"text-align:right\">%s</td></tr>" % (short_date(d), n, money(v)) for d, v, n in days)
        or '<tr><td class="dim" colspan="3">—</td></tr>', downloads)
    return shell("Reports", "/reports", body, sub="Numbers for any period, ready to export", msg=q.get("m", ""), cnt=counts(conn, sn))


def _range(q):
    t = M.today()
    return M.iso(M.parse_date(q.get("from")) or t.replace(day=1)), M.iso(M.parse_date(q.get("to")) or t)


def collection_csv(conn, sn, q):
    a, b = _range(q)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Date", "Bills", "Cash", "UPI", "Card", "Online", "Other", "Total"])
    for d, in conn.execute("SELECT DISTINCT paid_on FROM payments WHERE paid_on BETWEEN ? AND ? ORDER BY paid_on", (a, b)).fetchall():
        rows = conn.execute("SELECT lower(mode), SUM(amount), COUNT(*) FROM payments WHERE paid_on=? GROUP BY 1", (d,)).fetchall()
        by = {r[0] or "": r[1] for r in rows}
        known = sum(by.get(k, 0) for k in ("cash", "upi", "card", "online"))
        total = sum(r[1] for r in rows)
        w.writerow([short_date(d), sum(r[2] for r in rows)] + ["%g" % by.get(k, 0) for k in ("cash", "upi", "card", "online")]
                   + ["%g" % (total - known), "%g" % total])
    return "﻿" + buf.getvalue()


def bills_csv(conn, sn, q):
    a, b = _range(q)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Invoice", "Date", "Member ID", "Name", "Package", "Start", "End", "Trainer", "List price", "Discount",
                "Admission", "GST", "Payable", "Paid", "Balance", "Mode", "Prepared by"])
    for p in conn.execute("SELECT p.*, m.name FROM payments p LEFT JOIN members m ON m.client_id = p.client_id "
                          "WHERE paid_on BETWEEN ? AND ? ORDER BY paid_on, p.id", (a, b)):
        w.writerow([p["invoice"] or "", short_date(p["paid_on"]), member_id(p["client_id"]), nice(p["name"] or ""), p["package"],
                    short_date(p["start"]), short_date(p["expiry"]), p["trainer"] or "", "%g" % (p["list_price"] or 0),
                    "%g" % (p["discount"] or 0), "%g" % (p["admission"] or 0), "%g" % (p["gst"] or 0), "%g" % (p["payable"] or 0),
                    "%g" % (p["amount"] or 0), "%g" % (p["balance"] or 0), p["mode"] or "", p["created_by"] or ""])
    return "﻿" + buf.getvalue()


def expenses_csv(conn, sn, q):
    init_expenses(conn)
    a, b = _range(q)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Date", "Category", "Amount", "Paid to", "Mode", "Note", "Added by"])
    for x in conn.execute("SELECT * FROM expenses WHERE spent_on BETWEEN ? AND ? ORDER BY spent_on", (a, b)):
        w.writerow([short_date(x["spent_on"]), x["category"], "%g" % x["amount"], x["paid_to"], x["mode"], x["note"], x["created_by"]])
    return "﻿" + buf.getvalue()


# ---------------- expenses ----------------

def expenses_page(conn, sn, q):
    init_expenses(conn)
    p, a, b, label = period(q)
    A_, B_ = M.iso(a), M.iso(b)
    rows = conn.execute("SELECT * FROM expenses WHERE spent_on BETWEEN ? AND ? ORDER BY spent_on DESC, id DESC", (A_, B_)).fetchall()
    total = sum(r["amount"] for r in rows)
    bycat = {}
    for r in rows:
        bycat[r["category"]] = bycat.get(r["category"], 0) + r["amount"]
    col = conn.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE paid_on BETWEEN ? AND ?", (A_, B_)).fetchone()[0]
    tabs = "".join('<a href="/expenses?p=%s"%s>%s</a>' % (k, ' class="on"' if k == p else "", l)
                   for k, l in (("month", "This month"), ("last", "Last month"), ("year", "This year"), ("all", "All time")))
    trs = "".join('<tr><td>%s</td><td>%s</td><td>%s</td><td class="dim">%s</td><td class="dim">%s</td><td style="text-align:right"><b>%s</b></td>'
                  '<td><form method="post" action="/expenses/save" onsubmit="return confirm(\'Delete this expense?\')">'
                  '<input type="hidden" name="delete" value="%d"><button class="btn sm" aria-label="Delete">✕</button></form></td></tr>' % (
                      short_date(r["spent_on"]), e(r["category"]), e(r["paid_to"] or ""), e(r["mode"] or ""), e(r["note"] or ""),
                      money(r["amount"]), r["id"]) for r in rows) or '<tr><td colspan="7" class="dim">No expenses in this period.</td></tr>'
    cats = "".join('<div class="kpi"><div class="l">%s</div><div class="v" style="font-size:26px">%s</div></div>' % (e(c), money(v))
                   for c, v in sorted(bycat.items(), key=lambda x: -x[1]))
    body = """<div class="ph" style="flex-wrap:wrap"><div class="tabs">%s</div><span class="dim">%s</span></div>
<div class="kpis"><div class="kpi"><div class="l">Collection</div><div class="v">%s</div></div>
<div class="kpi hot"><div class="l">Expenses</div><div class="v">%s</div><div class="s">%d entries</div></div>
<div class="kpi"><div class="l">Profit</div><div class="v">%s</div><div class="s">collection − expenses</div></div></div>
%s<form class="panel" method="post" action="/expenses/save" style="display:flex;flex-direction:column;gap:14px" id="expf"><h2>Add expense</h2><div class="grid">
<label>Date<input type="date" name="spent_on" value="%s" required></label>
<label>Category<select name="category">%s</select></label>
<label>Amount (₹)<input name="amount" inputmode="decimal" required></label>
<label>Paid to<input name="paid_to" placeholder="e.g. MPEB, landlord, trainer name"></label>
<label>Mode<select name="mode"><option>UPI</option><option>Cash</option><option>Bank</option><option>Card</option></select></label>
<label>Note<input name="note"></label></div><button class="btn red" style="align-self:flex-start">Save expense</button>
<p class="dim" style="margin:0;font-size:12px">Salaries paid go in category "Salaries" so profit is right.</p></form>
%s<div class="panel"><div class="ph"><h2>Expenses · %s</h2>%s</div><div class="tw"><table>
<tr><th>Date</th><th>Category</th><th>Paid to</th><th>Mode</th><th>Note</th><th style="text-align:right">Amount</th><th></th></tr>%s</table></div></div>""" % (
        tabs, e(label), money(col), money(total), len(rows), money(col - total), expense_ai_box(), M.iso(M.today()),
        "".join("<option>%s</option>" % c for c in EXPENSE_CATS),
        ('<div class="kpis">%s</div>' % cats) if cats else "", e(label),
        '<a class="btn sm" href="/reports/expenses.csv?%s">%sExport</a>' % (urlencode({"from": A_, "to": B_}), icon("down", 16)), trs)
    return shell("Expenses", "/expenses", body, sub="Kharcha, and what is left as profit", msg=q.get("m", ""), cnt=counts(conn, sn))


def expense_ai_box():
    ok = AI.available()
    return """<div class="panel" style="display:flex;flex-direction:column;gap:10px"><div class="ph" style="margin:0"><h2>AI-fill expense</h2>
<span class="dim" style="font-size:12px">%s</span></div><div style="display:flex;flex-wrap:wrap;gap:10px;align-items:center">
<input id="etext" placeholder="e.g. bijli bill 8400 aaj UPI se diya" style="flex:1 1 320px"%s>
<label class="btn" style="flex-direction:row;cursor:pointer">Bill photo<input type="file" id="eimg" accept="image/*" capture="environment" hidden%s></label>
<button type="button" class="btn red" id="ebtn"%s>Fill with AI</button></div><div id="emsg" class="dim" style="font-size:13px"></div></div>
<script>(function(){var img=null;var m=document.getElementById('emsg');
document.getElementById('eimg').addEventListener('change',function(ev){var file=ev.target.files[0];if(!file){return}var r=new FileReader();
r.onload=function(){var im=new Image();im.onload=function(){var k=Math.min(1,1600/Math.max(im.width,im.height));var c=document.createElement('canvas');
c.width=Math.round(im.width*k);c.height=Math.round(im.height*k);c.getContext('2d').drawImage(im,0,0,c.width,c.height);
img=c.toDataURL('image/jpeg',0.8).split(',')[1];m.textContent='Photo ready: '+file.name};im.src=r.result};r.readAsDataURL(file)});
document.getElementById('ebtn').addEventListener('click',function(){var t=document.getElementById('etext').value.trim();if(!t&&!img){m.textContent='Type a line or add a bill photo.';return}
var b=this;b.disabled=true;b.textContent='Reading…';var body='text='+encodeURIComponent(t)+(img?'&img='+encodeURIComponent(img):'');
fetch('/expenses/ai',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:body}).then(function(r){return r.json()})
.then(function(d){b.disabled=false;b.textContent='Fill with AI';if(d.error){m.textContent=d.error;return}var f=document.getElementById('expf');
['spent_on','category','amount','paid_to','mode','note'].forEach(function(k){var el=f.querySelector('[name='+k+']');if(el&&d[k]!==undefined&&d[k]!==''&&d[k]!==null){el.value=d[k]}});
m.textContent=(d.unclear?('AI note: '+d.unclear+' '):'')+'Check the form below, then Save expense.';f.scrollIntoView({behavior:'smooth'})})
.catch(function(){b.disabled=false;b.textContent='Fill with AI';m.textContent='Could not reach the server.'})})})();</script>""" % (
        "Type it, or snap the bill. You check, then save." if ok else "AI is not set up on the server yet.",
        "" if ok else " disabled", "" if ok else " disabled", "" if ok else " disabled")


def expense_ai(conn, f):
    img = re.sub(r"[^A-Za-z0-9+/=]", "", f.get("img") or "")
    if len(img) > 8000000:
        return {"error": "Photo is too large. Try a smaller photo."}
    data, err = AI.expense_fill(f.get("text", ""), img, "image/jpeg", EXPENSE_CATS, M.iso(M.today()))
    if err:
        return {"error": err}
    if data.get("amount") == 0:
        data["amount"] = ""
    return data


def save_expense(conn, f):
    init_expenses(conn)
    if f.get("delete", "").isdigit():
        r = conn.execute("SELECT * FROM expenses WHERE id=?", (int(f["delete"]),)).fetchone()
        conn.execute("DELETE FROM expenses WHERE id=?", (int(f["delete"]),))
        return "Deleted %s %s." % (r["category"], money(r["amount"])) if r else "Deleted."
    amt = num(f.get("amount"))
    d = M.parse_date(f.get("spent_on")) or M.today()
    cat = f.get("category") if f.get("category") in EXPENSE_CATS else "Other"
    if amt <= 0:
        return "Enter an amount."
    conn.execute("INSERT INTO expenses (spent_on, category, amount, paid_to, mode, note, created_by, created_at) VALUES (?,?,?,?,?,?,?,?)",
                 (M.iso(d), cat, amt, (f.get("paid_to") or "").strip(), f.get("mode", ""), (f.get("note") or "").strip(),
                  staff_name(), M.stamp()))
    return "Saved %s %s." % (cat, money(amt))


# ---------------- staff, shifts, salaries ----------------

STAFF_ROLES = ["Trainer", "Front desk", "Manager", "Housekeeping", "Other"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def init_staff(conn):
    conn.executescript("""
CREATE TABLE IF NOT EXISTS staff (pin TEXT PRIMARY KEY, name TEXT, role TEXT, phone TEXT, salary REAL DEFAULT 0,
    shift_id INTEGER, active INTEGER DEFAULT 1, joined TEXT);
CREATE TABLE IF NOT EXISTS shifts (id INTEGER PRIMARY KEY, name TEXT, start TEXT, end TEXT, days TEXT DEFAULT '0123456',
    grace INTEGER DEFAULT 10);
CREATE TABLE IF NOT EXISTS shift_log (id INTEGER PRIMARY KEY, pin TEXT, shift_id INTEGER, from_date TEXT, changed_by TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS salary_pay (id INTEGER PRIMARY KEY, pin TEXT, month TEXT, present INTEGER, working INTEGER,
    base REAL, incentive REAL, advance REAL, deduction REAL, payable REAL, paid_on TEXT, mode TEXT, expense_id INTEGER,
    created_by TEXT, UNIQUE (pin, month));
""")
    SH.init(conn)


def sync_staff_from_machine(conn, sn):
    """Every machine user with an ID 10000+ is staff; add the ones we have not seen yet."""
    tr = {t.lower() for t in trainers(conn)}
    for pin, name in staff_names(conn, sn).items():
        if not conn.execute("SELECT 1 FROM staff WHERE pin=?", (pin,)).fetchone():
            role = "Trainer" if (name or "").strip().lower() in tr else ("Manager" if (name or "").lower() == "admin" else "Other")
            conn.execute("INSERT INTO staff (pin, name, role, active, joined) VALUES (?,?,?,1,?)", (pin, nice(name), role, M.iso(M.today())))


def hm(t):
    try:
        h, m = (t or "").split(":")[:2]
        return int(h) * 60 + int(m)
    except ValueError:
        return None


def fmt_t(t):
    v = hm(t)
    if v is None:
        return "—"
    return datetime.time(v // 60 % 24, v % 60).strftime("%I:%M %p").lstrip("0")


def day_status(conn, pin, shift, d):
    """('On time'|'Late 12m'|'Not in'|'Off day', first_in, last_out, early_leave). Late uses the gym's late rule."""
    info = SH.day_info(conn, pin, shift, d)
    to_s = lambda m: None if m is None else "%02d:%02d" % (m // 60, m % 60)
    pr = SH.parts(shift)
    early = bool(info["last"] is not None and pr and info["last"] < pr[-1][1] - SH.grace(conn))
    return info["status"], to_s(info["first"]), to_s(info["last"]), early


def working_days(shift, a, b):
    days = (shift["days"] if shift else "0123456") or "0123456"
    n, d = 0, a
    while d <= b:
        n += str(d.weekday()) in days
        d += datetime.timedelta(days=1)
    return n


def pt_load(conn):
    out = {}
    t = M.iso(M.today())
    for tname, n in conn.execute("SELECT lower(trim(trainer)), COUNT(DISTINCT client_id) FROM payments "
                                 "WHERE trainer != '' AND expiry >= ? GROUP BY 1", (t,)):
        out[tname] = n
    return out


def staff_page(conn, sn, q):
    init_staff(conn)
    sync_staff_from_machine(conn, sn)
    t = M.today()
    shifts = {r["id"]: r for r in conn.execute("SELECT * FROM shifts ORDER BY start")}
    staff = conn.execute("SELECT * FROM staff ORDER BY active DESC, role, name").fetchall()
    loads = pt_load(conn)
    edit = q.get("edit", "")
    rows, present, trainers_n, others = "", 0, 0, 0
    for s_ in staff:
        if not s_["active"] and q.get("all") != "1":
            continue
        sh = shifts.get(s_["shift_id"])
        st, first, last, early = day_status(conn, s_["pin"], sh, t)
        present += first is not None
        trainers_n += s_["role"] == "Trainer" and s_["active"]
        others += s_["role"] != "Trainer" and s_["active"]
        n30 = conn.execute("SELECT COUNT(DISTINCT substr(ts,1,10)) FROM punches WHERE pin=? AND ts >= ?",
                           (s_["pin"], M.iso(t - datetime.timedelta(days=30)))).fetchone()[0]
        pill = {"On time": "p-ok", "Present": "p-ok", "Not in": "p-dim", "Off day": "p-dim"}.get(st, "p-warn")
        rows += ('<tr%s><td><a class="mem" href="/staff/report?pin=%s"><span class="av">%s</span>%s</a></td><td>%s</td><td>%s</td><td>%d / 30</td><td>%s</td>'
                 '<td><span class="pill %s">%s</span>%s</td><td class="dim">%s</td><td>%s</td><td style="display:flex;gap:6px;justify-content:flex-end">%s'
                 '<a class="ibtn" href="/staff?edit=%s" aria-label="Edit">%s</a></td></tr>') % (
            ' style="opacity:.5"' if not s_["active"] else "", e(s_["pin"]), initials(s_["name"]), e(s_["name"] or "ID " + s_["pin"]),
            e(s_["role"] or ""), e(sh["name"]) if sh else '<span class="dim">No shift</span>', n30,
            ("%d clients" % loads.get((s_["name"] or "").lower(), 0)) if s_["role"] == "Trainer" else "—",
            pill, e(st), (' <span class="pill p-warn">Left early</span>' if early else ""),
            ("%s%s" % (fmt_t(first), (" → " + fmt_t(last)) if last else "")) if first else "", money(s_["salary"]) if s_["salary"] else "—",
            ('<a class="ibtn" href="tel:%s" aria-label="Call">%s</a>' % (e(s_["phone"]), icon("phone", 16))) if s_["phone"] else "",
            e(s_["pin"]), icon("edit", 16))
    # shift cards
    sh_cards = ""
    for sh in shifts.values():
        members_ = [s_["name"] for s_ in staff if s_["shift_id"] == sh["id"] and s_["active"]]
        sh_cards += ('<div class="kpi"><div class="ph" style="margin:0"><b style="font:600 18px Oswald,sans-serif;text-transform:uppercase">%s</b>'
                     '<a class="btn sm" href="/staff?shift=%d">Edit</a></div><div class="v" style="font-size:24px">%s – %s%s</div>'
                     '<div class="s">%s · %s a day</div><div class="s" style="margin-top:8px">%s</div></div>') % (
            e(sh["name"]), sh["id"], fmt_t(sh["start"]), fmt_t(sh["end"]),
            ('<div style="font-size:18px">+ %s – %s</div>' % (fmt_t(sh["start2"]), fmt_t(sh["end2"]))) if sh["start2"] else "",
            " ".join(WEEKDAYS[int(c)] for c in (sh["days"] or "")) or "No days", SH.dur(SH.shift_minutes(sh)),
            e(", ".join(members_)) if members_ else "Nobody assigned")
    es = conn.execute("SELECT * FROM shifts WHERE id=?", (q.get("shift"),)).fetchone() if q.get("shift", "").isdigit() else None
    day_boxes = "".join('<label class="chk" style="flex-direction:row"><input type="checkbox" name="d%d" value="1"%s>%s</label>' % (
        i, " checked" if (str(i) in (es["days"] if es else "012345")) else "", d) for i, d in enumerate(WEEKDAYS))
    shift_form = """<form class="panel" method="post" action="/staff/shift" style="display:flex;flex-direction:column;gap:14px">
<h2>%s</h2><input type="hidden" name="id" value="%s"><div class="grid">
<label>Shift name<input name="name" value="%s" placeholder="e.g. Morning" required></label>
<label>Starts<input type="time" name="start" value="%s" required></label><label>Ends<input type="time" name="end" value="%s" required></label>
<label>Second part starts (split shift, optional)<input type="time" name="start2" value="%s"></label>
<label>Second part ends<input type="time" name="end2" value="%s"></label></div>
<p class="dim" style="margin:0;font-size:12px">Split shift: e.g. 6:00–10:00 AM and 5:00–9:00 PM. Leave the second part empty for one continuous shift.
Late is checked at the start of each part (rule below).</p>
<div style="display:flex;flex-wrap:wrap;gap:14px">%s</div>
<div style="display:flex;gap:8px"><button class="btn red">Save shift</button>%s</div></form>""" % (
        "Edit shift" if es else "Create a shift", es["id"] if es else "", e(es["name"]) if es else "", es["start"] if es else "06:00",
        es["end"] if es else "14:00", (es["start2"] or "") if es else "", (es["end2"] or "") if es else "", day_boxes,
        ('<button class="btn" name="delete" value="1" onclick="return confirm(\'Delete this shift? Staff on it become unassigned.\')">Delete</button>'
         '<a class="btn" href="/staff">Cancel</a>') if es else "")
    edit_form = ""
    em = conn.execute("SELECT * FROM staff WHERE pin=?", (edit,)).fetchone() if edit else None
    if em:
        edit_form = """<form class="panel" method="post" action="/staff/save" style="display:flex;flex-direction:column;gap:14px" id="edit">
<h2>Edit %s (gate ID %s)</h2><input type="hidden" name="pin" value="%s"><div class="grid">
<label>Name<input name="name" value="%s" required></label><label>Role<select name="role">%s</select></label>
<label>Phone<input name="phone" value="%s"></label><label>Monthly salary (₹)<input name="salary" value="%g" inputmode="decimal"></label>
<label>Shift<select name="shift_id"><option value="">No shift</option>%s</select></label>
<label>Status<select name="active"><option value="1"%s>Working</option><option value="0"%s>Left / inactive</option></select></label></div>
<div style="display:flex;gap:8px"><button class="btn red">Save</button><a class="btn" href="/staff">Cancel</a></div>
<p class="dim" style="margin:0;font-size:12px">Changing the shift keeps a history. Trainer names must match the trainer chosen on bills to count PT clients.</p></form>""" % (
            e(em["name"] or ""), e(em["pin"]), e(em["pin"]), e(em["name"] or ""),
            "".join('<option%s>%s</option>' % (" selected" if r == em["role"] else "", r) for r in STAFF_ROLES), e(em["phone"] or ""),
            em["salary"] or 0, "".join('<option value="%d"%s>%s (%s–%s)</option>' % (
                i, " selected" if i == em["shift_id"] else "", e(s["name"]), fmt_t(s["start"]), fmt_t(s["end"])) for i, s in shifts.items()),
            " selected" if em["active"] else "", "" if em["active"] else " selected")
    body = """%s<div class="kpis"><div class="kpi hot"><div class="l">Trainers</div><div class="v">%d</div><div class="s">working</div></div>
<div class="kpi"><div class="l">Other staff</div><div class="v">%d</div><div class="s">front desk, manager, housekeeping</div></div>
<div class="kpi"><div class="l">Present today</div><div class="v">%d</div><div class="s">via biometric</div></div>
<a class="kpi" href="/salary"><div class="l">Salaries</div><div class="v" style="font-size:22px;margin-top:14px">Salary sheet →</div><div class="s">days from biometric</div></a></div>
<div class="panel"><div class="ph"><h2>Shifts</h2></div><div class="kpis">%s</div></div><div class="two">%s%s</div>
<div class="panel"><div class="ph"><h2>Team</h2><a href="/staff?all=1">Show people who left</a></div><div class="tw"><table>
<tr><th>Name</th><th>Role</th><th>Shift</th><th>Present (30 d)</th><th>PT load</th><th>Today</th><th>In / out</th><th>Salary</th><th></th></tr>%s</table></div>
<p class="dim" style="font-size:12px;margin:12px 0 0">Staff come from the gate machine (IDs 10000+). Enroll a new staff finger on the machine with the next 100xx ID and they appear here.</p></div>""" % (
        edit_form, trainers_n, others, present, sh_cards or '<p class="dim">No shifts yet. Create one below.</p>', shift_form,
        admin_only(SH.rule_panel(conn)),
        rows or '<tr><td colspan="9" class="dim">No staff found on the gate machine yet.</td></tr>')
    return shell("Staff & trainers", "/staff", body, sub="Team, shifts, attendance and salary", msg=q.get("m", ""), cnt=counts(conn, sn))


def save_shift(conn, f):
    init_staff(conn)
    sid = f.get("id", "")
    if f.get("delete") and sid.isdigit():
        conn.execute("UPDATE staff SET shift_id=NULL WHERE shift_id=?", (int(sid),))
        conn.execute("DELETE FROM shifts WHERE id=?", (int(sid),))
        return "Shift deleted."
    name, start, end = (f.get("name") or "").strip(), f.get("start", ""), f.get("end", "")
    if not name or hm(start) is None or hm(end) is None:
        return "Shift name, start and end time are needed."
    days = "".join(str(i) for i in range(7) if f.get("d%d" % i))
    grace = int(M.setting(conn, "late_grace", "14") or 14)
    s2, e2 = f.get("start2", ""), f.get("end2", "")
    if hm(s2) is None or hm(e2) is None:
        s2 = e2 = ""
    elif hm(s2) <= hm(end) or hm(e2) <= hm(s2):
        return "The second part must start after the first part ends, and end after it starts."
    if hm(end) <= hm(start):
        return "The shift must end after it starts."
    if sid.isdigit():
        conn.execute("UPDATE shifts SET name=?, start=?, end=?, days=?, grace=?, start2=?, end2=? WHERE id=?",
                     (name, start, end, days, grace, s2, e2, int(sid)))
    else:
        conn.execute("INSERT INTO shifts (name, start, end, days, grace, start2, end2) VALUES (?,?,?,?,?,?,?)",
                     (name, start, end, days, grace, s2, e2))
    return "Shift %s saved (%s – %s%s)." % (name, fmt_t(start), fmt_t(end), (", %s – %s" % (fmt_t(s2), fmt_t(e2))) if s2 else "")


def save_staff(conn, f):
    init_staff(conn)
    pin = f.get("pin", "")
    old = conn.execute("SELECT * FROM staff WHERE pin=?", (pin,)).fetchone()
    if not old:
        return "Staff not found."
    shift_id = int(f["shift_id"]) if (f.get("shift_id") or "").isdigit() else None
    conn.execute("UPDATE staff SET name=?, role=?, phone=?, salary=?, shift_id=?, active=? WHERE pin=?",
                 ((f.get("name") or old["name"]).strip(), f.get("role") if f.get("role") in STAFF_ROLES else old["role"],
                  (f.get("phone") or "").strip(), num(f.get("salary")), shift_id, 1 if f.get("active", "1") == "1" else 0, pin))
    if shift_id != old["shift_id"]:
        conn.execute("INSERT INTO shift_log (pin, shift_id, from_date, changed_by, at) VALUES (?,?,?,?,?)",
                     (pin, shift_id, M.iso(M.today()), staff_name(), M.stamp()))
    return "Saved %s." % (f.get("name") or old["name"])


def salary_page(conn, sn, q):
    init_staff(conn)
    sync_staff_from_machine(conn, sn)
    t = M.today()
    month = q.get("month") or t.strftime("%Y-%m")
    try:
        first = datetime.datetime.strptime(month + "-01", "%Y-%m-%d").date()
    except ValueError:
        first = t.replace(day=1)
        month = first.strftime("%Y-%m")
    nxt = (first + datetime.timedelta(days=32)).replace(day=1)
    last = min(nxt - datetime.timedelta(days=1), t)
    shifts = {r["id"]: r for r in conn.execute("SELECT * FROM shifts")}
    paid = {r["pin"]: r for r in conn.execute("SELECT * FROM salary_pay WHERE month=?", (month,))}
    rows, total = "", 0
    for s_ in conn.execute("SELECT * FROM staff WHERE active=1 ORDER BY role, name"):
        sh = shifts.get(s_["shift_id"])
        sm = SH.month_summary(conn, s_["pin"], sh, s_["salary"], first, last)
        pres = sm["present"]
        work = working_days(sh, first, last) if last >= first else 0
        base = s_["salary"] or 0
        suggested = round(base * min(pres, work) / work) if work else 0
        p = paid.get(s_["pin"])
        if p:
            total += p["payable"]
            act = '<span class="pill p-ok">Paid %s · %s</span>' % (money(p["payable"]), short_date(p["paid_on"])[:6])
            cells = "<td>%s</td><td>%s</td><td>%s</td>" % (money(p["incentive"]), money(p["advance"]), money(p["deduction"]))
        else:
            total += suggested - sm["cut"]
            fid = "f%s" % s_["pin"]
            cells = ('<td><input form="%s" name="incentive" value="0" style="width:72px" inputmode="decimal"></td>'
                     '<td><input form="%s" name="advance" value="0" style="width:72px" inputmode="decimal"></td>'
                     '<td><input form="%s" name="deduction" value="%d" style="width:72px" inputmode="decimal"></td>') % (fid, fid, fid, sm["cut"])
            act = ('<form id="%s" method="post" action="/salary/pay" style="display:flex;gap:6px;align-items:center">'
                   '<input type="hidden" name="pin" value="%s"><input type="hidden" name="month" value="%s">'
                   '<input type="hidden" name="present" value="%d"><input type="hidden" name="working" value="%d"><input type="hidden" name="base" value="%g">'
                   '<input name="payable" value="%d" style="width:100px" inputmode="decimal" aria-label="Payable">'
                   '<select name="mode" aria-label="Mode"><option>Bank</option><option>UPI</option><option>Cash</option></select>'
                   '<button class="btn red sm" onclick="return confirm(\'Mark salary paid? It is added to expenses.\')">Mark paid</button></form>') % (
                fid, e(s_["pin"]), month, pres, work, base, suggested)
        late_txt = ('<a href="/staff/report?pin=%s&month=%s">%d late</a>%s' % (
            e(s_["pin"]), month, sm["late"], ('<div class="dim" style="font-size:12px">cut %gh = %s</div>' % (sm["hours_cut"], money(sm["cut"])))
            if sm["hours_cut"] else "")) if sm["late"] else '<span class="dim">0</span>'
        rows += ('<tr><td><a href="/staff/report?pin=%s&month=%s"><b>%s</b></a><div class="dim" style="font-size:12px">%s</div></td><td>%s</td>'
                 '<td>%d / %d</td><td>%d</td><td>%s</td><td>%s</td>%s<td>%s</td></tr>') % (
            e(s_["pin"]), month, e(s_["name"]), e(s_["role"]), money(base) if base else '<a href="/staff?edit=%s">Set salary</a>' % e(s_["pin"]),
            pres, work, max(0, work - pres), SH.dur(sm["worked"]) if sm["worked"] else "—", late_txt, cells, act)
    prev = (first - datetime.timedelta(days=1)).strftime("%Y-%m")
    body = """<div class="ph"><div class="tabs"><a href="/salary?month=%s">← %s</a><a class="on" href="/salary?month=%s">%s</a>%s</div>
<span class="dim">Total %s</span></div><div class="panel"><div class="tw"><table>
<tr><th>Staff</th><th>Monthly salary</th><th>Present / working days</th><th>Absent</th><th>Hours</th><th>Late</th><th>Incentive</th><th>Advance</th><th>Deduction</th><th>Payable</th></tr>%s</table></div>
<p class="dim" style="font-size:12px;margin:12px 0 0">Present days and hours come from the gate machine (hours need an out punch). Working days follow each person's shift days up to today.
Payable box = salary × present ÷ working days; on Mark paid, incentive is added and advance and deduction are taken off. Deduction starts with the late-rule pay cut
(salary ÷ (working days × shift hours) per hour); excuse a late day on the person's page. Paid salaries go into Expenses → Salaries.</p></div>""" % (
        prev, datetime.datetime.strptime(prev + "-01", "%Y-%m-%d").strftime("%b"), month, first.strftime("%B %Y"),
        ('<a href="/salary?month=%s">%s →</a>' % (nxt.strftime("%Y-%m"), nxt.strftime("%b"))) if nxt <= t else "",
        money(total), rows or '<tr><td colspan="10" class="dim">No staff yet.</td></tr>')
    return shell("Salary sheet", "/staff", body, sub="Monthly salaries from biometric attendance", msg=q.get("m", ""), cnt=counts(conn, sn))


def pay_salary(conn, f):
    init_staff(conn)
    init_expenses(conn)
    s_ = conn.execute("SELECT * FROM staff WHERE pin=?", (f.get("pin", ""),)).fetchone()
    month = f.get("month", "")
    if not s_ or not re.fullmatch(r"\d{4}-\d{2}", month):
        return month, "Staff not found."
    if conn.execute("SELECT 1 FROM salary_pay WHERE pin=? AND month=?", (s_["pin"], month)).fetchone():
        return month, "Already marked paid."
    inc, adv, ded = num(f.get("incentive")), num(f.get("advance")), num(f.get("deduction"))
    payable = num(f.get("payable")) + inc - adv - ded
    cur = conn.execute("INSERT INTO expenses (spent_on, category, amount, paid_to, mode, note, created_by, created_at) VALUES (?,?,?,?,?,?,?,?)",
                       (M.iso(M.today()), "Salaries", payable, s_["name"], f.get("mode", ""), "Salary %s" % month, staff_name(), M.stamp()))
    conn.execute("INSERT INTO salary_pay (pin, month, present, working, base, incentive, advance, deduction, payable, paid_on, mode, "
                 "expense_id, created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                 (s_["pin"], month, int(num(f.get("present"))), int(num(f.get("working"))), num(f.get("base")), inc, adv, ded,
                  payable, M.iso(M.today()), f.get("mode", ""), cur.lastrowid, staff_name()))
    return month, "Salary %s for %s marked paid: %s." % (month, s_["name"], money(payable))


# ---------------- inquiries ----------------

LEAD_SOURCES = ["Walk-in", "Instagram", "Flyer", "Hoarding", "Friend / referral", "Google", "Other"]
LEAD_STAGES = [("new", "New"), ("follow", "Follow-up due"), ("trial", "Trial booked"), ("joined", "Joined"), ("lost", "Not interested")]


def init_leads(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS inquiries (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, interest TEXT, source TEXT,
        stage TEXT DEFAULT 'new', next_date TEXT, trial_at TEXT, note TEXT, client_id INTEGER, created_by TEXT, created_at TEXT,
        updated_at TEXT)""")


def lead_chip(r):
    t = M.today()
    if r["stage"] == "joined":
        return '<span class="pill p-ok">Converted</span>'
    if r["stage"] == "trial" and r["trial_at"]:
        d = M.parse_date(r["trial_at"][:10])
        if d:
            n = (d - t).days
            return '<span class="pill %s">%s</span>' % ("p-ok" if n >= 0 else "p-bad",
                                                         "Today" if n == 0 else "Tomorrow" if n == 1 else ("%d days" % n if n > 0 else "Trial missed"))
    d = M.parse_date(r["next_date"]) if r["next_date"] else None
    if d:
        n = (d - t).days
        if n < 0:
            return '<span class="pill p-bad">Overdue %dd</span>' % -n
        if n == 0:
            return '<span class="pill p-warn">Call today</span>'
        return '<span class="pill p-dim">%s</span>' % d.strftime("%d %b")
    c = M.parse_date((r["created_at"] or "")[:10])
    return '<span class="pill p-ok">%s</span>' % ("Today" if c == t else "Yesterday" if c == t - datetime.timedelta(days=1)
                                                  else c.strftime("%d %b") if c else "New")


def lead_wa(r):
    link = wa(r["phone"], "Hi %s, House of Strength se baat kar rahe hain. Aapne gym ke baare me poocha tha. Kab visit kar sakte hain? "
                          "Free trial bhi le sakte hain." % nice(r["name"]))
    return ('<a class="ibtn wa" href="%s" target="_blank" rel="noopener" aria-label="WhatsApp">%s</a>' % (e(link), icon("chat", 16))) if link else ""


def inquiries(conn, sn, q):
    init_leads(conn)
    rows = conn.execute("SELECT * FROM inquiries WHERE stage != 'lost' ORDER BY COALESCE(next_date, created_at)").fetchall()
    cols = ""
    for key, title in LEAD_STAGES[:4]:
        items = [r for r in rows if r["stage"] == key]
        if key == "joined":
            items = sorted(items, key=lambda r: r["updated_at"] or "", reverse=True)[:12]
        cards = "".join('<div class="kpi" style="padding:14px"><a href="/inquiries?id=%d" style="color:inherit"><b>%s</b></a>'
                        '<div class="dim" style="font-size:12px;margin:4px 0 10px">%s · %s</div>'
                        '<div style="display:flex;justify-content:space-between;align-items:center">%s%s</div></div>' % (
                            r["id"], e(nice(r["name"])), e(r["interest"] or "—"), e(r["source"] or "—"), lead_chip(r), lead_wa(r))
                        for r in items) or '<p class="dim" style="font-size:13px">Empty</p>'
        cols += ('<div class="panel" style="padding:14px;display:flex;flex-direction:column;gap:10px"><div class="ph" style="margin:0">'
                 '<h2 style="font-size:16px">%s</h2><span class="pill p-dim">%d</span></div>%s</div>' % (
                     e(title), len([r for r in rows if r["stage"] == key]), cards))
    src = conn.execute("SELECT COALESCE(NULLIF(source,''),'Other'), COUNT(*) FROM inquiries GROUP BY 1 ORDER BY 2 DESC").fetchall()
    total = conn.execute("SELECT COUNT(*) FROM inquiries").fetchone()[0]
    joined = conn.execute("SELECT COUNT(*) FROM inquiries WHERE stage='joined'").fetchone()[0]
    sel = conn.execute("SELECT * FROM inquiries WHERE id=?", (q.get("id"),)).fetchone() if (q.get("id") or "").isdigit() else None
    v = lambda k: e(str((sel[k] if sel else "") or ""))
    pk = "".join('<option%s>%s</option>' % (" selected" if sel and sel["interest"] == p_[0] else "", e(p_[0]))
                 for p_ in conn.execute("SELECT name FROM packages WHERE active=1 ORDER BY kind, sort"))
    form = """<form class="panel" method="post" action="/inquiries/save" style="display:flex;flex-direction:column;gap:14px" id="lead">
<h2>%s</h2><input type="hidden" name="id" value="%s"><div class="grid">
<label>Name<input name="name" value="%s" required></label><label>Phone<input name="phone" value="%s" inputmode="tel"></label>
<label>Interested in<select name="interest"><option value="">—</option>%s</select></label>
<label>Came from<select name="source">%s</select></label>
<label>Stage<select name="stage">%s</select></label>
<label>Next follow-up<input type="date" name="next_date" value="%s"></label>
<label>Trial date &amp; time<input type="datetime-local" name="trial_at" value="%s"></label>
<label>Note<input name="note" value="%s"></label></div>
<div style="display:flex;flex-wrap:wrap;gap:8px"><button class="btn red">Save</button>%s</div></form>""" % (
        "Edit inquiry" if sel else "Add inquiry", v("id"), v("name"), v("phone"), pk,
        "".join('<option%s>%s</option>' % (" selected" if sel and sel["source"] == s_ else "", s_) for s_ in LEAD_SOURCES),
        "".join('<option value="%s"%s>%s</option>' % (k, " selected" if (sel["stage"] if sel else "new") == k else "", l) for k, l in LEAD_STAGES),
        v("next_date") or M.iso(M.today() + datetime.timedelta(days=1)), v("trial_at"), v("note"),
        ('<a class="btn" href="/member?%s">Joined → add as member</a><a class="btn" href="/inquiries">Cancel</a>' % urlencode(
            {"name": sel["name"] or "", "phone": sel["phone"] or ""})) if sel else "")
    chart = bars([(s_, n) for s_, n in src], lambda l, v_: True) if src else '<p class="dim">No inquiries yet.</p>'
    body = """<div class="kpis" style="grid-template-columns:repeat(auto-fit,minmax(240px,1fr));align-items:start">%s</div>%s
<div class="panel"><div class="ph"><h2>Where leads come from · all time</h2></div>%s
<p class="dim" style="margin:10px 0 0">%d inquiries · %d joined (%s). Logging every walk-in and call lifts this.</p></div>""" % (
        cols, form, chart, total, joined, ("%.1f%%" % (100.0 * joined / total)) if total else "0%")
    return shell("Inquiries", "/inquiries", body, sub="Simple lead board: new → follow-up → trial → joined",
                 actions='<a class="btn red" href="/inquiries#lead">%sAdd inquiry</a>' % icon("plus"), msg=q.get("m", ""), cnt=counts(conn, sn))


def save_inquiry(conn, f):
    init_leads(conn)
    name = (f.get("name") or "").strip()
    if not name:
        return "Name is needed."
    stage = f.get("stage") if f.get("stage") in dict(LEAD_STAGES) else "new"
    vals = (name, re.sub(r"[^\d+]", "", f.get("phone") or ""), f.get("interest", ""), f.get("source", ""), stage,
            M.iso(M.parse_date(f.get("next_date"))), (f.get("trial_at") or "").replace("T", " "), (f.get("note") or "").strip(), M.stamp())
    if (f.get("id") or "").isdigit():
        conn.execute("UPDATE inquiries SET name=?, phone=?, interest=?, source=?, stage=?, next_date=?, trial_at=?, note=?, updated_at=? "
                     "WHERE id=?", vals + (int(f["id"]),))
    else:
        conn.execute("INSERT INTO inquiries (name, phone, interest, source, stage, next_date, trial_at, note, updated_at, created_by, "
                     "created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)", vals + (staff_name(), M.stamp()))
    return "Saved %s (%s)." % (nice(name), dict(LEAD_STAGES)[stage])


# ---------------- approvals ----------------

def init_approvals(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS approvals (id INTEGER PRIMARY KEY, kind TEXT, client_id INTEGER, payload TEXT,
        note TEXT, status TEXT DEFAULT 'pending', requested_by TEXT, requested_role TEXT, decided_by TEXT, decided_at TEXT,
        result TEXT, created_at TEXT)""")


APPROVAL_KINDS = {"discount": "Discount above limit", "cancel_bill": "Cancel a bill", "extend": "Extend / freeze membership",
                  "phone": "Phone number access", "leave": "Leave / shift swap", "other": "Other"}


def request_approval(conn, kind, client_id, payload, note):
    import json
    init_approvals(conn)
    conn.execute("INSERT INTO approvals (kind, client_id, payload, note, requested_by, requested_role, created_at) VALUES (?,?,?,?,?,?,?)",
                 (kind, client_id, json.dumps(payload), note, staff_name(), A.role(), M.stamp()))


def approvals(conn, sn, q):
    import json
    init_approvals(conn)
    admin = A.is_admin()
    where = "" if admin else " WHERE requested_by = %s" % "?"
    args = () if admin else (staff_name(),)
    rows = conn.execute("SELECT * FROM approvals%s ORDER BY status='pending' DESC, id DESC LIMIT 200" % where, args).fetchall()
    names = member_names(conn)
    trs = ""
    for r in rows:
        try:
            pl = json.loads(r["payload"] or "{}")
        except ValueError:
            pl = {}
        what = {"discount": lambda: "%s · discount %s" % (pl.get("package_name", ""), money(num(pl.get("discount")))),
                "cancel_bill": lambda: "Bill %s" % pl.get("invoice", ""),
                "extend": lambda: "+%s days" % pl.get("days", "")}.get(r["kind"], lambda: "")()
        st = {"pending": "p-warn", "approved": "p-ok", "rejected": "p-bad"}[r["status"]]
        act = ""
        if admin and r["status"] == "pending":
            act = ('<form method="post" action="/approvals/decide" style="display:flex;gap:6px"><input type="hidden" name="id" value="%d">'
                   '<button class="btn red sm" name="do" value="approve">Approve</button><button class="btn sm" name="do" value="reject">Reject</button></form>' % r["id"])
        trs += '<tr><td class="dim">%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class="dim">%s</td><td><span class="pill %s">%s</span>%s</td><td>%s</td></tr>' % (
            e((r["created_at"] or "")[:16]), e(r["requested_by"] or ""), e(APPROVAL_KINDS.get(r["kind"], r["kind"])),
            ('<a href="/m?id=%d">%s</a>' % (r["client_id"], e(nice(names.get(str(r["client_id"]), ""))))) if r["client_id"] else "—",
            e(what), e(r["note"] or ""), st, r["status"].title(), ('<div class="dim" style="font-size:12px">%s</div>' % e(r["result"])) if r["result"] else "", act)
    form = ""
    if not admin:
        kinds = ("extend", "cancel_bill", "phone", "other") if A.role() == "reception" else ("leave", "other")
        form = """<form class="panel" method="post" action="/approvals/request" style="display:flex;flex-direction:column;gap:14px">
<h2>Ask the owner</h2><div class="grid"><label>Request<select name="kind">%s</select></label>
<label>Member (if any)<input name="member" list="mlist3" placeholder="Name or HOS-ID"></label><datalist id="mlist3">%s</datalist>
<label>Bill invoice (for cancel)<input name="invoice" placeholder="HOS-01250"></label><label>Days (for extend)<input name="days" inputmode="numeric"></label>
<label>Reason<input name="note" required></label></div><button class="btn red" style="align-self:flex-start">Send request</button></form>""" % (
            "".join('<option value="%s">%s</option>' % (k, APPROVAL_KINDS[k]) for k in kinds),
            "".join('<option value="%s · %s">' % (e(nice(n)), member_id(c)) for c, n in conn.execute(
                "SELECT client_id, name FROM members ORDER BY client_id DESC LIMIT 800")) if A.role() == "reception" else "")
    pending = sum(1 for r in rows if r["status"] == "pending")
    body = """%s<div class="panel"><div class="ph"><h2>%s</h2><span class="pill p-warn">%d pending</span></div><div class="tw"><table>
<tr><th>When</th><th>From</th><th>Request</th><th>Member</th><th>Detail</th><th>Reason</th><th>Status</th><th></th></tr>%s</table></div></div>""" % (
        form, "Requests" if admin else "My requests", pending, trs or '<tr><td colspan="8" class="dim">No requests.</td></tr>')
    return shell("Approvals", "/approvals", body, sub="Requests from reception and trainers wait for the owner's yes or no",
                 msg=q.get("m", ""), cnt=counts(conn, sn))


def make_request(conn, f):
    kind = f.get("kind") if f.get("kind") in APPROVAL_KINDS else "other"
    if A.role() == "trainer" and kind not in ("leave", "other"):
        kind = "other"
    m = resolve_member(conn, f.get("member")) if f.get("member") else None
    payload = {}
    if kind == "cancel_bill":
        inv = (f.get("invoice") or "").strip().upper()
        p = conn.execute("SELECT * FROM payments WHERE invoice=?", (inv,)).fetchone()
        if not p:
            return "Bill %s not found." % inv
        payload = {"invoice": inv}
        m = m or conn.execute("SELECT * FROM members WHERE client_id=?", (p["client_id"],)).fetchone()
    if kind == "extend":
        if not m or not (f.get("days") or "").isdigit():
            return "Pick the member and number of days."
        payload = {"days": int(f["days"])}
    request_approval(conn, kind, m["client_id"] if m else None, payload, (f.get("note") or "").strip())
    return "Request sent to the owner."


def decide(conn, sn, f):
    import json
    init_approvals(conn)
    r = conn.execute("SELECT * FROM approvals WHERE id=? AND status='pending'", (f.get("id", ""),)).fetchone()
    if not r:
        return "Already decided."
    pl = json.loads(r["payload"] or "{}")
    if f.get("do") != "approve":
        conn.execute("UPDATE approvals SET status='rejected', decided_by=?, decided_at=? WHERE id=?", (staff_name(), M.stamp(), r["id"]))
        return "Rejected."
    result = "Approved."
    if r["kind"] == "discount":
        inv, msg = save_bill(conn, sn, dict(pl, approved_by=staff_name(), on_behalf=r["requested_by"]))
        result = msg if inv else "Could not make the bill: " + msg
    elif r["kind"] == "extend" and r["client_id"]:
        m = conn.execute("SELECT * FROM members WHERE client_id=?", (r["client_id"],)).fetchone()
        old = M.parse_date(m["expiry"]) or M.today()
        new = old + datetime.timedelta(days=int(pl.get("days", 0)))
        conn.execute("UPDATE members SET expiry=?, updated_at=? WHERE client_id=?", (M.iso(new), M.stamp(), r["client_id"]))
        if sn and new >= M.today() and str(r["client_id"]) in M.blocked_pins(conn, sn):
            M.unblock(conn, sn, r["client_id"])
        result = "Expiry moved to %s." % new.strftime("%d %b %Y")
    elif r["kind"] == "cancel_bill":
        p = conn.execute("SELECT * FROM payments WHERE invoice=?", (pl.get("invoice"),)).fetchone()
        if p:
            conn.execute("UPDATE members SET pending=MAX(0, COALESCE(pending,0)-?) WHERE client_id=?", (p["balance"] or 0, p["client_id"]))
            conn.execute("UPDATE payments SET amount=0, balance=0, payable=0, note='CANCELLED ' || COALESCE(note,'') WHERE id=?", (p["id"],))
            result = "Bill %s cancelled. Fix the member's expiry from Edit if needed." % pl.get("invoice")
    conn.execute("UPDATE approvals SET status='approved', decided_by=?, decided_at=?, result=? WHERE id=?",
                 (staff_name(), M.stamp(), result, r["id"]))
    return result


# ---------------- routing ----------------

GET_PAGES = {"/": dashboard, "/members": members_list, "/m": profile, "/bill": bill_page, "/receipt": receipt,
             "/soon": soon, "/attendance": attendance, "/renewals": renewals, "/pending": pending, "/absent": absent,
             "/collect": collect_page, "/trainer": trainer_page, "/settings": settings_page, "/packages": packages_page,
             "/reports": reports, "/expenses": expenses_page, "/staff": staff_page, "/salary": salary_page,
             "/inquiries": inquiries, "/approvals": approvals}
CSV_PAGES = {"/members.csv": members_csv, "/attendance.csv": attendance_csv, "/renewals.csv": renewals_csv,
             "/pending.csv": pending_csv, "/reports/collection.csv": collection_csv, "/reports/bills.csv": bills_csv,
             "/reports/expenses.csv": expenses_csv}


def handle_get(path, q, conn, sn):
    """Return (content_type, body) or None when the path is not ours."""
    if path in GET_PAGES:
        return "text/html", GET_PAGES[path](conn, sn, q)
    if path in CSV_PAGES:
        return "text/csv", CSV_PAGES[path](conn, sn, q)
    return None
