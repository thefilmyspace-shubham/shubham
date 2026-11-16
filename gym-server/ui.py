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

import members as M

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
    return c


def wa(phone, text):
    return M.wa_link(phone, text)


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
    ("/soon?p=Attendance", "Attendance", "finger", None), ("/today", "Renewals", "renew", "renewals"),
    ("/members?f=pending", "Pending Payments", "rupee", "pending"), ("/soon?p=Absent", "Absent Members", "alert", "absent"),
    ("/soon?p=Inquiries", "Inquiries", "chat", None), ("/soon?p=Packages", "Packages", "box", None),
    ("/soon?p=Staff", "Staff & Trainers", "staff", None), ("/soon?p=Reports", "Reports", "chart", None),
]
SYSTEM = [("/sync", "Door sync", "door"), ("/gate", "Gate machine", "server"), ("/backup", "Backup", "down")]


def shell(title, active, body, sub="", actions="", msg="", cnt=None, warn=""):
    cnt = cnt or {}
    links = []
    for href, label, ic, key in NAV:
        badge = '<span class="badge">%d</span>' % cnt[key] if key and cnt.get(key) else ""
        links.append('<a href="%s"%s>%s<span>%s</span>%s</a>' % (href, ' class="on"' if href == active else "",
                                                                  icon(ic), label, badge))
    sys_links = "".join('<a href="%s"%s>%s<span>%s</span></a>' % (h, ' class="on"' if h == active else "", icon(i), l)
                        for h, l, i in SYSTEM)
    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>%s · House of Strength</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>%s</style></head><body><div class="app">
<aside class="side"><div class="brand"><img src="/logo.jpg" alt=""><b>HOUSE OF<br><span>STRENGTH</span></b></div>
<nav class="nav">%s<div class="navsec">System</div>%s</nav>
<div class="who"><div class="av">AD</div><div><b>Admin</b><div class="dim" style="font-size:12px">Owner</div></div></div></aside>
<div class="main"><div class="top"><div><h1>%s</h1><div class="sub">%s</div></div>
<div class="acts"><form action="/members" method="get" class="search">%s<input name="q" placeholder="Search name, phone or member ID" aria-label="Search members"></form>%s</div></div>
<div class="content">%s%s%s</div>
<div class="foot"><span>House of Strength · Ratlam</span><span>Powered by <b>TFS · The First Solutions</b></span></div>
</div></div></body></html>""" % (
        e(title), CSS, "".join(links), sys_links, e(title), sub, icon("search"), actions,
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
<div class="kpi"><div class="l">Collection this month</div><div class="v">%s</div><div class="s">%d bills since 1 %s</div></div>
<a class="kpi" href="/members?f=pending"><div class="l">Pending dues</div><div class="v">%s</div><div class="s">%d members</div></a></div>
<div class="two"><div class="panel"><div class="ph"><h2>Check-ins by hour · today</h2><a href="/gate">Open gate</a></div>%s</div>
<div class="panel"><div class="ph"><h2>Collection · last 6 months</h2><span class="dim">₹ thousand</span></div>%s</div></div>
<div class="two"><div class="panel"><div class="ph"><h2>Renewals due this week</h2><a href="/today">View all %d</a></div>
<div class="tw"><table><tr><th>Member</th><th>Package</th><th>Expiry</th><th>Due</th><th></th></tr>%s</table></div></div>
<div style="display:flex;flex-direction:column;gap:20px"><div class="panel"><div class="ph"><h2>Quick actions</h2></div><div class="qa">
<a href="/bill">%sNew membership bill</a><a href="/member">%sAdd member</a><a href="/soon?p=Inquiries">%sAdd inquiry</a><a href="/today">%sSend reminders</a></div></div>
<div class="panel"><div class="ph"><h2>Not seen for 7+ days</h2><span class="dim">%d</span></div><table>%s</table></div></div></div>""" % (
        active, total - active, total, today_in,
        "Peak %s" % ("%d %s" % ((peak - 1) % 12 + 1, "AM" if peak < 12 else "PM")) if peak is not None else "From the gate",
        money(col_m[0]), col_m[1], t.strftime("%b"), money(pend[0]), pend[1] or 0,
        bars(hour_items, lambda l, v: v and v >= max(hmap.values() or [1]) * 0.6),
        bars(col6, lambda l, v: True), cnt["renewals"], ren_rows,
        icon("bill", 22), icon("users", 22), icon("chat", 22), icon("chat", 22), cnt["absent"], abs_rows)
    actions = ('<a class="btn" href="/gate">%sGate</a><a class="btn red" href="/bill">%sNew bill</a>'
               % (icon("finger"), icon("plus")))
    return shell("Dashboard", "/", body, sub=t.strftime("%A, %d %B %Y"), actions=actions, msg=q.get("m", ""), cnt=cnt)


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
        '<a class="ibtn" href="tel:%s" aria-label="Call">%s</a><a class="ibtn" href="/member?id=%d" aria-label="Edit">%s</a></td></tr>' % (
            m["client_id"], initials(m["name"]), e(nice(m["name"])), member_id(m["client_id"]), e(m["package"] or ""),
            short_date(m["expiry"]), status_pill(m["expiry"]),
            '<span class="pill p-warn">%s</span>' % money(m["pending"]) if (m["pending"] or 0) > 0 else "₹0",
            wa_btn(m, renew_msg(m)), e(m["phone"] or ""), icon("phone", 16), m["client_id"], icon("edit", 16))
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
<a class="btn sm" href="/members.csv?%s">%sExport Excel</a></div></div>
<div class="tw"><table><tr><th>Member</th><th>ID</th><th>Package</th><th>Expiry</th><th>Status</th><th>Due</th><th></th></tr>%s</table></div>%s</div>
<details class="panel"><summary style="cursor:pointer;font-weight:600">Import from old software</summary>
<p class="dim">CSV files made from the old software. Re-importing updates, it never duplicates.</p>
<p>Members: <input type="file" id="csv" accept=".csv,text/csv"> <button type="button" onclick="up('csv','/members/import','st')">Import members</button> <span id="st"></span></p>
<p>Old bills: <input type="file" id="bills" accept=".csv,text/csv"> <button type="button" onclick="up('bills','/payments/import','st2')">Import bills</button> <span id="st2"></span></p>
<script>function up(id,url,sid){var f=document.getElementById(id).files[0];if(!f){return}
var s=document.getElementById(sid);s.textContent='Uploading…';f.text().then(function(t){
return fetch(url,{method:'POST',headers:{'Content-Type':'text/csv'},body:t})}).then(function(r){return r.text()})
.then(function(t){s.textContent=t;setTimeout(function(){location.href='/members'},2500)})}</script></details>""" % (
        len(allm), n_active, round(100 * n_active / max(1, len(allm))), n_soon, len(allm) - n_active,
        door_issues, tabs, urlencode({"f": f, "q": term}), icon("down", 16), trs, pager)
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
        member_id(m["client_id"]), e(m["phone"] or "—"), e(m["gender"] or "—"),
        short_date(m["registration"] or (first["paid_on"] if first else "")), m["client_id"], door,
        money(m["pending"]), e(m["package"] or "—"),
        len(days_in), last_txt, last[11:16] if last else "", heat, tracking_start(conn).strftime("%d %b %Y"),
        m["client_id"], bill_rows,
        ('<p style="display:flex;gap:10px;flex-wrap:wrap;margin:16px 0 0"><a class="btn sm" href="/receipt?inv=%s">%sPrint last receipt</a></p>'
         % (quote(lastinv), icon("print", 16))) if lastinv else "")
    return shell("Member profile", "/members", body, sub='<a href="/members">Members</a> › %s' % e(nice(m["name"])),
                 actions='<a class="btn red" href="/bill?id=%d">%sNew bill</a>' % (m["client_id"], icon("plus")),
                 msg=q.get("m", ""), cnt=counts(conn, sn))


def wa_btn_big(m):
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
    body = """<form method="post" action="/bill/save" class="two" style="grid-template-columns:minmax(0,2fr) minmax(280px,1fr);align-items:start" id="bf">
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
<label>Admission fee (₹)<input name="admission" id="adm" inputmode="decimal" value="0"></label>
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
<span class="dim" style="font-size:12px">Invoice %s · prepared by Admin</span></div></div></form>
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
document.getElementById('kind').addEventListener('change',function(){kindFilter();upd()});kindFilter();upd()})();
</script>""" % (
        e("%s · %s" % (nice(m["name"]), member_id(m["client_id"]))) if m else "", options, cards,
        M.iso(start), tr, inv)
    return shell("New bill", "/bill", body, sub="Membership or PT bill in under a minute", msg=q.get("m", ""),
                 cnt=counts(conn, sn))


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
         M.stamp(), inv, p["price"], disc, adm, gst, total, balance, f.get("trainer", ""), p["kind"], "Admin",
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

def receipt(conn, sn, q):
    inv = q.get("inv", "")
    p = conn.execute("SELECT * FROM payments WHERE invoice=?", (inv,)).fetchone()
    if not p:
        return shell("Receipt", "/bill", '<div class="panel">Receipt not found.</div>', cnt=counts(conn, sn))
    m = conn.execute("SELECT * FROM members WHERE client_id=?", (p["client_id"],)).fetchone()
    name = nice(m["name"]) if m else ""
    text = ("House of Strength - Receipt %s\nMember: %s (%s)\nPackage: %s\nPeriod: %s to %s\nTotal: %s\nPaid: %s (%s)\n%s"
            "Thank you! Get better, together.") % (
        inv, name, member_id(p["client_id"]), p["package"], short_date(p["start"]), short_date(p["expiry"]),
        money(p["payable"]), money(p["amount"]), p["mode"] or "",
        ("Balance: %s\n" % money(p["balance"])) if (p["balance"] or 0) > 0 else "")
    link = wa(m["phone"], text) if m else ""
    auto = ""
    if q.get("wa") == "1" and link:
        auto = "<script>window.open(%r,'_blank')</script>" % link
    if q.get("print") == "1":
        auto += "<script>setTimeout(function(){window.print()},400)</script>"
    rows = [("Package", e(p["package"] or "")), ("Period", "%s → %s" % (short_date(p["start"]), short_date(p["expiry"]))),
            ("Trainer", e(p["trainer"] or "—")), ("Package price", money(p["list_price"])),
            ("Discount", "– " + money(p["discount"])), ("Admission", money(p["admission"])), ("GST", money(p["gst"])),
            ("<b>Total payable</b>", "<b>%s</b>" % money(p["payable"])), ("Paid (%s)" % e(p["mode"] or ""), money(p["amount"])),
            ("<b>Balance</b>", "<b>%s</b>" % money(p["balance"]))]
    body = """<div class="panel" style="max-width:720px;background:#fff;color:#111">
<div style="display:flex;justify-content:space-between;align-items:center;gap:16px;border-bottom:2px solid #e10600;padding-bottom:14px">
<div style="display:flex;align-items:center;gap:12px"><img src="/logo.jpg" alt="" style="width:64px;height:64px;border-radius:10px">
<div><div style="font:700 24px Oswald,sans-serif">HOUSE OF STRENGTH</div><div style="color:#555;font-size:12px">%s</div></div></div>
<div style="text-align:right"><div style="font:600 20px Oswald,sans-serif">RECEIPT</div><div>%s</div><div style="color:#555">%s</div></div></div>
<p style="margin:16px 0"><b>%s</b> · %s · %s</p>
<table style="color:#111">%s</table>
<p style="color:#555;font-size:12px;margin-top:20px">Payment non-refundable and non-transferable. Thank you for training with us. Get better, together.</p>
<p style="color:#888;font-size:11px">Powered by TFS · The First Solutions</p></div>
<div class="acts noprint"><button class="btn" onclick="window.print()">%sPrint (A4)</button>%s
<a class="btn" href="/m?id=%d">Open member</a><a class="btn red" href="/bill">New bill</a></div>%s""" % (
        e(M.setting(conn, "gym_address", "")), e(inv), short_date(p["paid_on"]), e(name), member_id(p["client_id"]),
        e(m["phone"] if m else ""),
        "".join('<tr><td style="color:#444;border-color:#eee">%s</td><td style="text-align:right;border-color:#eee">%s</td></tr>' % r for r in rows),
        icon("print", 16), ('<a class="btn" href="%s" target="_blank" rel="noopener">%sSend on WhatsApp</a>' % (e(link), icon("chat", 16))) if link else "",
        p["client_id"], auto)
    return shell("Receipt", "/bill", body, sub=e(inv), msg=q.get("m", ""), cnt=counts(conn, sn))


def soon(conn, sn, q):
    name = q.get("p", "This page")
    links = {"Attendance": "/gate", "Absent": "/", "Inquiries": "/", "Packages": "/bill", "Staff": "/", "Reports": "/today"}
    body = ('<div class="panel"><h2>%s</h2><p class="dim">This screen is being built next, exactly as in the approved design. '
            'Until then use <a href="%s">this page</a>.</p></div>' % (e(name), links.get(name, "/")))
    nav = {"Attendance": "/soon?p=Attendance", "Absent": "/soon?p=Absent", "Inquiries": "/soon?p=Inquiries",
           "Packages": "/soon?p=Packages", "Staff": "/soon?p=Staff", "Reports": "/soon?p=Reports"}.get(name, "")
    return shell(name, nav, body, sub="Coming next", cnt=counts(conn, sn))


# ---------------- routing ----------------

GET_PAGES = {"/": dashboard, "/members": members_list, "/m": profile, "/bill": bill_page, "/receipt": receipt,
             "/soon": soon}


def handle_get(path, q, conn, sn):
    """Return (content_type, body) or None when the path is not ours."""
    if path in GET_PAGES:
        return "text/html", GET_PAGES[path](conn, sn, q)
    if path == "/members.csv":
        return "text/csv", members_csv(conn, sn, q)
    return None
