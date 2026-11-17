"""Login (email one-time code), roles, sessions and the activity log.

Roles (from the approved Features & Access plan):
  admin      everything
  reception  desk work: members, bills, payments, block/unblock, lists. No exports,
             backups, imports, settings, reports. Phone numbers only for members
             with a due. Discount up to RECEPTION_MAX_DISCOUNT percent.
  trainer    own PT clients only, never money.

Email is sent through Gmail SMTP with an App Password:
  SMTP_USER=gym@gmail.com  SMTP_PASS=<16-letter app password>
Until that is set, the owner can sign in with ADMIN_PASS ("Owner password").
"""
import datetime
import hashlib
import hmac
import html
import os
import re
import secrets
import smtplib
import ssl
import threading
from email.message import EmailMessage

e = html.escape
CURRENT = threading.local()  # .user for the request being handled

SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()
CODE_MINUTES = 10
SESSION_DAYS = 30
RECEPTION_MAX_DISCOUNT = 20  # percent of package price
COOKIE = "hos_s"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    email TEXT PRIMARY KEY, name TEXT, role TEXT, trainer TEXT, active INTEGER DEFAULT 1, created_at TEXT
);
CREATE TABLE IF NOT EXISTS otps (
    email TEXT, code_hash TEXT, expires TEXT, tries INTEGER DEFAULT 0, created_at TEXT
);
CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, email TEXT, expires TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS activity (id INTEGER PRIMARY KEY, at TEXT, email TEXT, name TEXT, role TEXT,
    action TEXT, detail TEXT);
"""

OWNER = {"email": "owner", "name": "Owner", "role": "admin", "trainer": ""}


def now():
    return datetime.datetime.now()


def stamp(dt=None):
    return (dt or now()).strftime("%Y-%m-%d %H:%M:%S")


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


def valid_email(s):
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", s or "", re.I))


def init(conn):
    conn.executescript(SCHEMA)
    if ADMIN_EMAIL and valid_email(ADMIN_EMAIL):
        conn.execute("INSERT OR IGNORE INTO users (email, name, role, trainer, active, created_at) VALUES (?,?,?,?,1,?)",
                     (ADMIN_EMAIL, "Owner", "admin", "", stamp()))


def user_row(conn, email):
    r = conn.execute("SELECT * FROM users WHERE email=? AND active=1", ((email or "").lower(),)).fetchone()
    return dict(r) if r else None


# ---------------- codes ----------------

def send_code(conn, email):
    """Always answers the same way, so nobody can probe which emails exist."""
    email = (email or "").strip().lower()
    generic = "If this email is registered, a 6-digit code has been sent. It works for %d minutes." % CODE_MINUTES
    if not valid_email(email):
        return False, "Enter a valid email."
    u = user_row(conn, email)
    if not u:
        return True, generic
    recent = conn.execute("SELECT COUNT(*) FROM otps WHERE email=? AND created_at >= ?",
                          (email, stamp(now() - datetime.timedelta(hours=1)))).fetchone()[0]
    if recent >= 5:
        return False, "Too many codes asked for this email. Try again in an hour."
    if not (SMTP_USER and SMTP_PASS):
        return False, "Email sending is not set up yet. The owner can sign in with the owner password."
    code = "%06d" % secrets.randbelow(1000000)
    conn.execute("DELETE FROM otps WHERE email=?", (email,))
    conn.execute("INSERT INTO otps (email, code_hash, expires, tries, created_at) VALUES (?,?,?,0,?)",
                 (email, sha(email + code), stamp(now() + datetime.timedelta(minutes=CODE_MINUTES)), stamp()))
    msg = EmailMessage()
    msg["Subject"] = "House of Strength login code: %s" % code
    msg["From"] = "House of Strength <%s>" % SMTP_USER
    msg["To"] = email
    msg.set_content("Hi %s,\n\nYour House of Strength app login code is %s\nIt works for %d minutes.\n\n"
                    "If you did not ask for it, ignore this email.\n" % (u["name"] or "", code, CODE_MINUTES))
    if not smtp_send(msg):
        return False, "Could not send the email right now. Try again in a minute."
    return True, generic


def smtp_send(msg):
    """Gmail on 587 (STARTTLS) first, then 465 (SSL). Errors go to the server log only."""
    ctx = ssl.create_default_context()
    for port in (587, 465):
        try:
            if port == 587:
                with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as s:
                    s.ehlo()
                    s.starttls(context=ctx)
                    s.ehlo()
                    s.login(SMTP_USER, SMTP_PASS)
                    s.send_message(msg)
            else:
                with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=20) as s:
                    s.login(SMTP_USER, SMTP_PASS)
                    s.send_message(msg)
            return True
        except smtplib.SMTPAuthenticationError as exc:
            print("%s smtp error port %d: login refused (check SMTP_USER / app password): %s"
                  % (stamp(), port, exc.smtp_code), flush=True)
            return False
        except Exception as exc:
            print("%s smtp error port %d: %s: %s" % (stamp(), port, type(exc).__name__, exc), flush=True)
    return False


def verify_code(conn, email, code):
    email = (email or "").strip().lower()
    code = re.sub(r"\D", "", code or "")
    row = conn.execute("SELECT * FROM otps WHERE email=?", (email,)).fetchone()
    if not row or row["expires"] < stamp():
        return None, "Code expired. Ask for a new one."
    if row["tries"] >= 5:
        return None, "Too many wrong tries. Ask for a new code."
    if not hmac.compare_digest(row["code_hash"], sha(email + code)):
        conn.execute("UPDATE otps SET tries=tries+1 WHERE email=?", (email,))
        return None, "Wrong code."
    conn.execute("DELETE FROM otps WHERE email=?", (email,))
    u = user_row(conn, email)
    if not u:
        return None, "This account is switched off."
    return new_session(conn, email), ""


def new_session(conn, email):
    token = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO sessions (token_hash, email, expires, created_at) VALUES (?,?,?,?)",
                 (sha(token), email, stamp(now() + datetime.timedelta(days=SESSION_DAYS)), stamp()))
    conn.execute("DELETE FROM sessions WHERE expires < ?", (stamp(),))
    return token


def session_user(conn, token):
    if not token:
        return None
    r = conn.execute("SELECT * FROM sessions WHERE token_hash=? AND expires >= ?", (sha(token), stamp())).fetchone()
    if not r:
        return None
    if r["email"] == "owner":
        return dict(OWNER)
    return user_row(conn, r["email"])


def end_session(conn, token):
    if token:
        conn.execute("DELETE FROM sessions WHERE token_hash=?", (sha(token),))


def cookie_token(header):
    for part in (header or "").split(";"):
        k, _, v = part.strip().partition("=")
        if k == COOKIE:
            return v
    return ""


# ---------------- permissions ----------------

RECEPTION_PATHS = {
    "/", "/members", "/m", "/member", "/member/save", "/member/door", "/bill", "/bill/save", "/receipt",
    "/attendance", "/attendance/manual", "/renewals", "/pending", "/collect", "/absent", "/r", "/remind", "/soon",
    "/logout", "/me", "/packages", "/inquiries", "/inquiries/save", "/approvals", "/approvals/request", "/bill/ai",
    "/joinings", "/joinings/view", "/joinings/upload", "/joinings/send", "/joinings/mark",
}
TRAINER_PATHS = {"/", "/trainer", "/logout", "/me", "/approvals", "/approvals/request"}


def allowed(user, path):
    if not user:
        return False
    role = user.get("role")
    if role == "admin":
        return True
    if role == "reception":
        return path in RECEPTION_PATHS
    if role == "trainer":
        return path in TRAINER_PATHS
    return False


def role():
    u = getattr(CURRENT, "user", None)
    return u.get("role") if u else ""


def is_admin():
    return role() == "admin"


def me():
    return getattr(CURRENT, "user", None) or {}


# ---------------- activity ----------------

def log(conn, action, detail=""):
    u = me()
    conn.execute("INSERT INTO activity (at, email, name, role, action, detail) VALUES (?,?,?,?,?,?)",
                 (stamp(), u.get("email", ""), u.get("name", ""), u.get("role", ""), action, (detail or "")[:500]))


# ---------------- pages ----------------

LOGIN_CSS = """*{box-sizing:border-box}body{margin:0;background:#0a0a0a;color:#f4f4f5;font:14px Inter,system-ui,sans-serif}
.wrap{display:flex;flex-wrap:wrap;min-height:100vh}.l{flex:1 1 380px;background:#000;display:flex;flex-direction:column;align-items:center;
justify-content:center;gap:22px;border-right:3px solid #e10600;padding:40px 16px}.l img{width:220px;max-width:70%}
.l h2{font:600 30px Oswald,sans-serif;margin:0;letter-spacing:.02em}.l h2 span{color:#ff4d4d}
.r{flex:1 1 380px;display:flex;align-items:center;justify-content:center;padding:40px 16px}.box{width:100%;max-width:400px;display:flex;flex-direction:column;gap:14px}
h1{font:600 38px Oswald,sans-serif;margin:0}.dim{color:#a1a1aa}label{display:flex;flex-direction:column;gap:6px;color:#c4c4cc}
input{min-height:48px;border-radius:10px;border:1px solid #26262a;background:#151517;color:#fff;padding:0 14px;font:15px Inter,sans-serif}
button{min-height:50px;border-radius:10px;border:0;background:#e10600;color:#fff;font:600 16px Oswald,sans-serif;letter-spacing:.05em;cursor:pointer}
a{color:#ff6b6b}.msg{background:#1f2a1a;padding:12px;border-radius:10px}.err{background:#2a0a0c;padding:12px;border-radius:10px;color:#ffd6d6}
.foot{color:#71717a;font-size:12px;margin-top:18px}details summary{cursor:pointer;color:#a1a1aa}"""


def login_page(step="email", email="", msg="", err=""):
    if step == "code":
        form = """<form method="post" action="/login/verify" class="box" style="gap:14px"><input type="hidden" name="email" value="%s">
<label>6-digit code sent to %s<input name="code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" required autofocus></label>
<button>LOG IN</button><a href="/login">Use another email</a></form>""" % (e(email), e(email))
    else:
        form = """<form method="post" action="/login/send" class="box" style="gap:14px">
<label>Email<input name="email" type="email" value="%s" placeholder="you@gmail.com" required autofocus></label>
<button>SEND LOGIN CODE</button></form>
<details><summary>Owner password</summary><form method="post" action="/login/owner" class="box" style="margin-top:12px">
<label>Owner password<input name="password" type="password" required></label><button>LOG IN AS OWNER</button></form></details>""" % e(email)
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Staff login · House of Strength</title><link href="https://fonts.googleapis.com/css2?family=Oswald:wght@600&family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>%s</style></head><body><div class="wrap"><div class="l"><img src="/logo.jpg" alt="House of Strength"><h2>GET BETTER, <span>TOGETHER.</span></h2></div>
<div class="r"><div class="box"><h1>STAFF LOGIN</h1><div class="dim">Owner, front desk and trainers sign in here.</div>%s%s%s
<div class="foot">Powered by TFS · The First Solutions</div></div></div></div></body></html>""" % (
        LOGIN_CSS, '<div class="msg">%s</div>' % e(msg) if msg else "", '<div class="err">%s</div>' % e(err) if err else "", form)


def users_page(conn, trainers):
    rows = "".join(
        '<tr><td><b>%s</b></td><td class="dim">%s</td><td>%s</td><td>%s</td><td>%s</td><td>'
        '<form method="post" action="/users/save" style="display:flex;gap:6px"><input type="hidden" name="email" value="%s">'
        '<input type="hidden" name="toggle" value="1"><button class="btn sm">%s</button></form></td></tr>' % (
            e(u["name"] or ""), e(u["email"]), e(u["role"].title()), e(u["trainer"] or "—"),
            '<span class="pill p-ok">Active</span>' if u["active"] else '<span class="pill p-dim">Off</span>',
            e(u["email"]), "Switch off" if u["active"] else "Switch on")
        for u in conn.execute("SELECT * FROM users ORDER BY role, name")) or '<tr><td colspan="6" class="dim">No staff yet.</td></tr>'
    topt = "".join('<option>%s</option>' % e(t) for t in trainers)
    return """<div class="panel"><div class="ph"><h2>Staff logins</h2></div><div class="tw"><table>
<tr><th>Name</th><th>Email</th><th>Role</th><th>Trainer name</th><th>Status</th><th></th></tr>%s</table></div></div>
<form class="panel" method="post" action="/users/save" style="display:flex;flex-direction:column;gap:14px"><h2>Add staff login</h2><div class="grid">
<label>Name<input name="name" required></label><label>Email<input name="email" type="email" required></label>
<label>Role<select name="role"><option value="reception">Reception</option><option value="trainer">Trainer</option><option value="admin">Admin</option></select></label>
<label>Trainer name (for trainers)<select name="trainer"><option value="">—</option>%s</select></label></div>
<button class="btn red" style="align-self:flex-start">Save</button>
<p class="dim" style="margin:0;font-size:12px">They sign in with this email: the app emails them a 6-digit code. Switching a login off stops it at once.</p></form>
<div class="panel"><h2>What each role can do</h2><div class="tw"><table><tr><th></th><th>Admin</th><th>Reception</th><th>Trainer</th></tr>
<tr><td>Members, bills, payments, renewals, dues</td><td>✓</td><td>✓</td><td>—</td></tr>
<tr><td>Block / unblock door</td><td>✓</td><td>✓ (logged)</td><td>—</td></tr>
<tr><td>Discount</td><td>Any</td><td>Up to %d%%</td><td>—</td></tr>
<tr><td>Phone numbers</td><td>All</td><td>Only members with a due</td><td>Own PT clients</td></tr>
<tr><td>Money totals, reports, exports, imports, backup, door sync, settings</td><td>✓</td><td>—</td><td>—</td></tr>
<tr><td>Own PT clients</td><td>✓</td><td>—</td><td>✓</td></tr></table></div></div>""" % (rows, topt, RECEPTION_MAX_DISCOUNT)


def save_user(conn, f):
    email = (f.get("email") or "").strip().lower()
    if f.get("toggle"):
        if email == ADMIN_EMAIL:
            return "The owner email set on the server cannot be switched off here."
        conn.execute("UPDATE users SET active = 1 - active WHERE email=?", (email,))
        conn.execute("DELETE FROM sessions WHERE email=?", (email,))
        log(conn, "staff login switched", email)
        return "Updated %s." % email
    if not valid_email(email):
        return "Enter a valid email."
    r = f.get("role") if f.get("role") in ("admin", "reception", "trainer") else "reception"
    conn.execute("INSERT INTO users (email, name, role, trainer, active, created_at) VALUES (?,?,?,?,1,?) "
                 "ON CONFLICT(email) DO UPDATE SET name=excluded.name, role=excluded.role, trainer=excluded.trainer, active=1",
                 (email, (f.get("name") or "").strip(), r, f.get("trainer", ""), stamp()))
    log(conn, "staff login saved", "%s as %s" % (email, r))
    return "Saved %s as %s." % (email, r.title())


def activity_page(conn, q):
    who = q.get("who", "")
    rows = conn.execute("SELECT * FROM activity WHERE (?='' OR email=?) ORDER BY id DESC LIMIT 300", (who, who)).fetchall()
    people = conn.execute("SELECT DISTINCT email, name FROM activity ORDER BY name").fetchall()
    opts = "".join('<option value="%s"%s>%s</option>' % (e(p[0]), " selected" if p[0] == who else "", e(p[1] or p[0])) for p in people)
    trs = "".join('<tr><td class="dim">%s</td><td>%s</td><td class="dim">%s</td><td>%s</td><td class="dim">%s</td></tr>' % (
        e(r["at"][:16]), e(r["name"] or r["email"]), e((r["role"] or "").title()), e(r["action"]), e(r["detail"] or ""))
        for r in rows) or '<tr><td colspan="5" class="dim">Nothing yet.</td></tr>'
    return """<form class="row" method="get" action="/activity"><select name="who"><option value="">Everyone</option>%s</select>
<button class="btn sm">Filter</button></form><div class="panel"><div class="tw"><table>
<tr><th>When</th><th>Who</th><th>Role</th><th>Action</th><th>Detail</th></tr>%s</table></div></div>""" % (opts, trs)
