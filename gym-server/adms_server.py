#!/usr/bin/env python3
"""House of Strength - eSSL / ZKTeco ADMS (push) test server.

Phase 1 goal: prove the gate machine (eSSL X2008, push firmware) can send
punches to our own server and take commands back from it.

Only the Python standard library is used, so it runs on a bare Ubuntu VM:

    ADMIN_PASS=choose-a-password python3 adms_server.py

Environment variables:
    PORT        port to listen on (default 8081, same as the machine's setting)
    DB_PATH     SQLite file (default hos.db next to this script)
    ADMIN_USER  admin page user name (default admin)
    ADMIN_PASS  admin page password (required)

Machine side (Menu > COMM > Cloud Server Setting):
    Server Mode ADMS, Enable Domain Name OFF,
    Server Address = this server's IP, Server Port = PORT.
"""
import base64
import datetime
import hmac
import json
import html
import os
import sqlite3
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import auth as A
import members as M
import ui as U
import assistant as AS
import gsheets as GS
import birthdays as BD
import door as D
import enroll as EN
import joining as J
import staffhours as SH
import whatsapp as W

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "8081"))
DB_PATH = os.environ.get("DB_PATH", os.path.join(HERE, "hos.db"))
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "")
# When set (e.g. https://34-63-254-31.sslip.io), people are sent to this HTTPS address; Caddy in front
# of the app holds the certificate. The gate machine keeps using plain http on PORT (/iclock/ only).
PUBLIC_URL = os.environ.get("HOS_PUBLIC_URL", "").rstrip("/")

DB_LOCK = threading.Lock()
PUBLIC = {"/login", "/login/send", "/login/verify", "/login/owner", "/logo.jpg", "/logout", "/join", "/join/submit", "/join.pdf"}
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), "backups")
KEEP_BACKUPS = 14

SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    sn TEXT PRIMARY KEY, ip TEXT, info TEXT, first_seen TEXT, last_seen TEXT
);
CREATE TABLE IF NOT EXISTS punches (
    id INTEGER PRIMARY KEY, sn TEXT, pin TEXT, ts TEXT, status TEXT,
    verify TEXT, raw TEXT, received_at TEXT, UNIQUE (sn, pin, ts)
);
-- Every USER / FP / BIODATA record the machine uploads, kept verbatim so a
-- removed member can be written back to the machine exactly as it was.
CREATE TABLE IF NOT EXISTS records (
    sn TEXT, kind TEXT, pin TEXT, idx TEXT, payload TEXT, updated_at TEXT,
    PRIMARY KEY (sn, kind, pin, idx)
);
CREATE TABLE IF NOT EXISTS commands (
    id INTEGER PRIMARY KEY, sn TEXT, cmd TEXT, created_at TEXT,
    sent_at TEXT, return_code TEXT, done_at TEXT
);
CREATE TABLE IF NOT EXISTS rawlog (
    id INTEGER PRIMARY KEY, at TEXT, method TEXT, path TEXT, body TEXT
);
"""


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with DB_LOCK, db() as conn:
        conn.executescript(SCHEMA)
        M.init(conn)
        U.init(conn)
        A.init(conn)
        GS.init(conn)
        J.init(conn)
        D.init(conn)
        W.init(conn)
        U.init_staff(conn)  # staff, shifts, late days
        BD.init(conn)
        EN.init(conn)


def kv_fields(text):
    """'PIN=1\tName=Ram\tPri=0' -> {'PIN': '1', 'Name': 'Ram', 'Pri': '0'}"""
    out = {}
    for part in text.split("\t"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v
    return out


def first(d, *keys):
    lower = {k.lower(): v for k, v in d.items()}
    for k in keys:
        if k.lower() in lower:
            return lower[k.lower()]
    return ""


class Handler(BaseHTTPRequestHandler):
    server_version = "HOS-ADMS/0.1"

    # ---------- helpers ----------
    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s - %s\n" % (now(), self.client_ip(), fmt % args))

    def send_text(self, text, code=200, ctype="text/plain"):
        data = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        return raw.decode("utf-8", errors="replace")

    def rawlog(self, method, body=""):
        with DB_LOCK, db() as conn:
            conn.execute(
                "INSERT INTO rawlog (at, method, path, body) VALUES (?,?,?,?)",
                (now(), method, self.path, body[:4000]),
            )
            # keep the debug log small
            conn.execute("DELETE FROM rawlog WHERE id <= (SELECT MAX(id) - 500 FROM rawlog)")

    def touch_device(self, sn, info=None):
        if not sn:
            return
        with DB_LOCK, db() as conn:
            conn.execute(
                "INSERT INTO devices (sn, ip, info, first_seen, last_seen) VALUES (?,?,?,?,?) "
                "ON CONFLICT(sn) DO UPDATE SET ip=excluded.ip, last_seen=excluded.last_seen, "
                "info=COALESCE(excluded.info, devices.info)",
                (sn, self.client_address[0], info, now(), now()),
            )

    def current_user(self):
        """Session cookie (email code or owner password), or the old Basic login as owner."""
        token = A.cookie_token(self.headers.get("Cookie", ""))
        if token:
            with DB_LOCK, db() as conn:
                u = A.session_user(conn, token)
            if u:
                return u
        header = self.headers.get("Authorization", "")
        if header.startswith("Basic "):
            try:
                user, _, pw = base64.b64decode(header[6:]).decode().partition(":")
            except Exception:
                return None
            if hmac.compare_digest(user, ADMIN_USER) and hmac.compare_digest(pw, ADMIN_PASS):
                return dict(A.OWNER)
        return None

    def authorized(self):
        return bool(getattr(A.CURRENT, "user", None))

    def ask_auth(self):
        return self.redirect("/login")

    def gate(self, path):
        """Login and role check for every page. Returns True when the request may go on."""
        A.CURRENT.user = None
        if path.startswith("/iclock/") or path in PUBLIC:
            return True
        u = self.current_user()
        if not u:
            self.redirect("/login")
            return False
        A.CURRENT.user = u
        if not A.allowed(u, path):
            self.send_text(U.shell("Not allowed", "", '<div class="panel">Your login cannot open this page. '
                                   'Ask the owner if you need it.</div>'), code=403, ctype="text/html")
            return False
        return True

    def client_ip(self):
        """The visitor's address; behind Caddy (a local connection) it is in X-Forwarded-For."""
        ip = self.client_address[0]
        if ip in ("127.0.0.1", "::1") and self.headers.get("X-Forwarded-For"):
            return self.headers["X-Forwarded-For"].split(",")[0].strip()
        return ip

    def is_https(self):
        return (self.headers.get("X-Forwarded-Proto") or "").lower() == "https"

    def base_url(self):
        """Address people should use for links we hand out (joining form, QR)."""
        if PUBLIC_URL:
            return PUBLIC_URL
        return ("https://" if self.is_https() else "http://") + (self.headers.get("Host") or "34.63.254.31:8081")

    def force_https(self, path):
        """People on the plain-http address go to the HTTPS one. True when the request was answered here."""
        if not PUBLIC_URL or path.startswith("/iclock/") or self.is_https():
            return False
        self.send_response(307 if self.command == "POST" else 301)  # 307 keeps a form post as a post
        self.send_header("Location", PUBLIC_URL + self.path)
        self.send_header("Content-Length", "0")
        self.end_headers()
        return True

    def set_session(self, token, location):
        self.send_response(303)
        self.send_header("Set-Cookie", "%s=%s; Path=/; HttpOnly; SameSite=Lax; Max-Age=%d%s" % (
            A.COOKIE, token, A.SESSION_DAYS * 86400, "; Secure" if self.is_https() else ""))
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    # ---------- routing ----------
    def route(self):
        """Parse the request; some firmware (eSSL X2008) adds '.aspx' to every path."""
        url = urlparse(self.path)
        path = url.path.rstrip("/")
        if path.lower().endswith(".aspx"):
            path = path[:-5]
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        return path or "/", q

    def do_GET(self):
        path, q = self.route()
        if self.force_https(path) or not self.gate(path):
            return
        sn = q.get("SN", "")
        if path.startswith("/iclock/"):
            self.rawlog("GET")
        if path == "/iclock/cdata":
            self.touch_device(sn, q.get("pushver") and "pushver=" + q["pushver"])
            return self.send_text(self.options(sn))
        if path == "/iclock/getrequest":
            self.touch_device(sn, q.get("INFO"))
            return self.send_text(self.next_command(sn))
        if path == "/iclock/ping":
            self.touch_device(sn)
            return self.send_text("OK")
        if path == "/logo.jpg":
            with open(os.path.join(HERE, "logo.jpg"), "rb") as fh:
                data = fh.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Cache-Control", "max-age=86400")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/join.pdf":
            with open(os.path.join(HERE, "joining_form.pdf"), "rb") as fh:
                data = fh.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", 'attachment; filename="HOS-Member-Consent-Form.pdf"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/join":
            with DB_LOCK, db() as conn:
                return self.send_text(J.public_page(conn), ctype="text/html")
        if path == "/staff/report":
            with DB_LOCK, db() as conn:
                U.init_staff(conn)
                return self.send_text(SH.report_page(conn, M.default_sn(conn), q), ctype="text/html")
        if path in ("/enroll", "/enroll/status"):
            with DB_LOCK, db() as conn:
                sn = M.default_sn(conn)
                if path == "/enroll/status":
                    return self.send_text(EN.status_json(conn, sn, q.get("id", "")), ctype="application/json")
                return self.send_text(EN.page(conn, sn, q), ctype="text/html")
        if path == "/member/delete":
            with DB_LOCK, db() as conn:
                return self.send_text(U.delete_page(conn, M.default_sn(conn), q), ctype="text/html")
        if path == "/search":
            with DB_LOCK, db() as conn:
                return self.send_text(U.search_json(conn, M.default_sn(conn), q), ctype="application/json")
        if path == "/birthdays":
            with DB_LOCK, db() as conn:
                return self.send_text(BD.page(conn, M.default_sn(conn), q), ctype="text/html")
        if path in ("/door", "/door/status"):
            with DB_LOCK, db() as conn:
                if path == "/door/status":
                    return self.send_text(D.status_json(conn), ctype="application/json")
                return self.send_text(D.page(conn, M.default_sn(conn), q), ctype="text/html")
        if path == "/whatsapp/status":
            st = W.status()
            return self.send_text(json.dumps({"state": st.get("state", "off"), "qr": st.get("qr", ""), "me": st.get("me", "")}),
                                  ctype="application/json")
        if path in ("/joinings", "/joinings/view", "/whatsapp"):
            q["_base"] = self.base_url()
            with DB_LOCK, db() as conn:
                sn = M.default_sn(conn)
                page = {"/joinings": J.staff_page, "/joinings/view": J.view_page, "/whatsapp": W.page}[path]
                out = page(conn, sn, q)
            return self.send_text(out, ctype="text/html")
        if path == "/login":
            return self.send_text(A.login_page(q.get("step", "email"), q.get("email", ""), q.get("m", ""), q.get("err", "")),
                                  ctype="text/html")
        if path == "/logout":
            with DB_LOCK, db() as conn:
                A.end_session(conn, A.cookie_token(self.headers.get("Cookie", "")))
            self.send_response(303)
            self.send_header("Set-Cookie", "%s=; Path=/; Max-Age=0" % A.COOKIE)
            self.send_header("Location", "/login")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path == "/" and A.role() == "trainer":
            return self.redirect("/trainer")
        if path == "/assistant":
            with DB_LOCK, db() as conn:
                return self.send_text(AS.page(conn, M.default_sn(conn), q), ctype="text/html")
        if path in ("/users", "/activity"):
            with DB_LOCK, db() as conn:
                body_ = (A.users_page(conn, U.trainers(conn), q.get("edit", "")) if path == "/users" else A.activity_page(conn, q))
                cnt = U.counts(conn, M.default_sn(conn))
            title = "Staff logins" if path == "/users" else "Activity log"
            return self.send_text(U.shell(title, path, body_, sub="Who can sign in" if path == "/users" else
                                          "Who did what, and when", msg=q.get("m", ""), cnt=cnt), ctype="text/html")
        if path in ("/r", "/remind"):
            if not self.authorized():
                return self.ask_auth()
            with DB_LOCK, db() as conn:
                if path == "/r":
                    return self.redirect(U.remind_redirect(conn, q))
                ids = parse_qs(urlparse(self.path).query).get("id", [])
                out = U.remind_queue(conn, M.default_sn(conn), q, ids)
            return self.send_text(out, ctype="text/html")
        if path in U.GET_PAGES or path in U.CSV_PAGES:
            if not self.authorized():
                return self.ask_auth()
            with DB_LOCK, db() as conn:
                ctype, out = U.handle_get(path, q, conn, M.default_sn(conn))
            if ctype == "text/csv":
                data = out.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", 'attachment; filename="hos-%s-%s.csv"' % (
                    path.strip("/").split(".")[0].replace("/", "-"), datetime.date.today().isoformat()))
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            return self.send_text(out, ctype=ctype)
        if path in ("/member", "/sync", "/today"):
            if not self.authorized():
                return self.ask_auth()
            with DB_LOCK, db() as conn:
                sn = M.default_sn(conn)
                M.layout = U.legacy_layout(conn, sn)
                page = {"/member": M.member_page}.get(path)
                if page:
                    html_ = page(conn, sn, q, q.get("m", ""))
                elif path == "/today":
                    html_ = M.today_page(conn, sn, q.get("m", ""))
                else:
                    html_ = M.sync_page(conn, sn, q.get("m", ""))
            return self.send_text(html_, ctype="text/html")
        if path == "/backup":
            if not self.authorized():
                return self.ask_auth()
            data = snapshot_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition",
                             'attachment; filename="hos-backup-%s.db"' % datetime.date.today().isoformat())
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path in ("/gate", "/admin", "/admin/command"):
            if not self.authorized():
                return self.ask_auth()
            if path != "/gate":
                return self.redirect("/gate")
            return self.send_text(self.admin_page(q.get("m", "")), ctype="text/html")
        return self.send_text("Not found", 404)

    def redirect(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        path, q = self.route()
        if self.force_https(path) or not self.gate(path):
            return
        sn = q.get("SN", "")
        body = self.read_body()
        if path.startswith("/iclock/"):
            self.rawlog("POST", body)
            self.touch_device(sn)
        if path == "/iclock/cdata":
            return self.send_text(self.handle_upload(sn, q.get("table", ""), body))
        if path == "/iclock/querydata":
            n = self.handle_querydata(sn, body)
            return self.send_text("OK: %d" % n)
        if path == "/iclock/devicecmd":
            return self.send_text(self.handle_cmd_result(body))
        if path == "/attendance/import":
            if not self.authorized():
                return self.ask_auth()
            with DB_LOCK, db() as conn:
                n, skipped, err = U.import_attendance(conn, M.default_sn(conn), body)
                A.log(conn, "import attendance", "%d check-ins" % n)
            return self.send_text(err or "Imported %d check-ins, %d rows skipped" % (n, skipped))
        if path.startswith("/login/") or path == "/users/save":
            f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
            with DB_LOCK, db() as conn:
                if path == "/users/save":
                    return self.redirect("/users?" + urlencode({"m": A.save_user(conn, f)}))
                if path == "/login/send":
                    ok, msg = A.send_code(conn, f.get("email"))
                    if ok:
                        return self.redirect("/login?" + urlencode({"step": "code", "email": f.get("email", ""), "m": msg}))
                    return self.redirect("/login?" + urlencode({"email": f.get("email", ""), "err": msg}))
                if path == "/login/verify":
                    token, err = A.verify_code(conn, f.get("email"), f.get("code"))
                    if token:
                        A.CURRENT.user = A.user_row(conn, f.get("email"))
                        A.log(conn, "login", "email code")
                        return self.set_session(token, "/")
                    return self.redirect("/login?" + urlencode({"step": "code", "email": f.get("email", ""), "err": err}))
                if path == "/login/owner":
                    if ADMIN_PASS and hmac.compare_digest(f.get("password", ""), ADMIN_PASS):
                        A.CURRENT.user = dict(A.OWNER)
                        A.log(conn, "login", "owner password")
                        return self.set_session(A.new_session(conn, "owner"), "/")
                    return self.redirect("/login?" + urlencode({"err": "Wrong owner password."}))
            return self.redirect("/login")
        if path == "/enroll/start":
            f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
            with DB_LOCK, db() as conn:
                user = A.me()
                ok, msg = EN.start(conn, M.default_sn(conn), f.get("id", ""), f.get("fid", ""), user.get("name") or user.get("email") or "",
                                   f.get("fresh") == "1")
                A.log(conn, "fingerprint enroll" if ok else "fingerprint enroll refused", "%s · %s" % (f.get("id", ""), msg))
            return self.redirect("/enroll?" + urlencode({"id": f.get("id", ""), "m": msg}))
        if path in ("/door/open", "/door/method"):
            f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
            with DB_LOCK, db() as conn:
                if path == "/door/method":
                    if not A.is_admin():
                        return self.redirect("/door")
                    M.set_setting(conn, "door_method", "2" if f.get("method") == "2" else "1")
                    A.log(conn, "door method", f.get("method", ""))
                    return self.redirect("/door?" + urlencode({"m": "Open method saved. Try Open door now."}))
                user = A.me()
                msg = D.request(conn, M.default_sn(conn), f.get("action", "open"), f.get("reason", ""),
                                user.get("name") or user.get("email") or "", A.role(), f.get("minutes", ""))
                A.log(conn, "door " + (f.get("action") or "open"), "%s · %s" % (f.get("reason", ""), msg))
            ok = msg.endswith("seconds.") and msg.startswith("Opening")
            return self.redirect("/door?" + urlencode({"m": msg, "wait": "1" if ok else ""}))
        if path == "/join/submit":
            f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
            with DB_LOCK, db() as conn:
                ok, out = J.submit(conn, f, self.client_ip())
            return self.send_text(out, code=200 if ok else 400, ctype="text/html")
        if path == "/joinings/upload":
            f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
            data, source, err = J.read_upload(f.get("file", ""), f.get("name", ""))  # may call the AI: no lock held
            with DB_LOCK, db() as conn:
                if err:
                    A.log(conn, "joining form upload failed", err)
                    return self.send_text(json.dumps({"error": err}), ctype="application/json")
                jid = J.save(conn, data, source)
                A.log(conn, "joining form uploaded", "%s (%s)" % (data.get("name", ""), source))
            miss = J.missing(data)
            msg = ("Read from the %s. Check every detail%s." % ("PDF" if source == "pdf" else "photo by AI",
                                                                 ("; missing: " + ", ".join(miss)) if miss else ""))
            return self.send_text(json.dumps({"id": jid, "msg": msg}), ctype="application/json")
        if path in ("/joinings/send", "/joinings/mark"):
            f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
            with DB_LOCK, db() as conn:
                if path == "/joinings/mark":
                    msg = J.mark(conn, f, A.is_admin(), U.staff_name())
                    A.log(conn, "joining form " + (f.get("do") or ""), msg)
                    return self.redirect("/joinings?" + urlencode({"m": msg}))
                link = self.base_url() + "/join"
                text = J.form_message(conn, link)
                if W.ready(conn):
                    ok = W.enqueue(conn, "form", 0, f.get("phone"), text, M.stamp(), doc="joining_form.pdf") \
                        if M.setting(conn, "wa_on_form", "1") == "1" else False
                    msg = "Joining form is going on WhatsApp now." if ok else "Enter a valid 10-digit mobile number."
                    A.log(conn, "joining form sent", msg)
                    return self.redirect("/joinings?" + urlencode({"m": msg}))
                wa_link = M.wa_link(f.get("phone"), text)
                A.log(conn, "joining form link opened", "")
            return self.redirect(wa_link or "/joinings?" + urlencode({"m": "Enter a valid 10-digit mobile number."}))
        if path == "/whatsapp/save":
            f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
            if f.get("do") == "logout":
                msg = W.save(None, f, A.is_admin())  # talks to the WhatsApp service; no lock needed
            else:
                with DB_LOCK, db() as conn:
                    msg = W.save(conn, f, A.is_admin())
            with DB_LOCK, db() as conn:
                A.log(conn, "whatsapp " + (f.get("do") or "save"), msg)
            return self.redirect("/whatsapp?" + urlencode({"m": msg}))
        if path in ("/inquiries/save", "/approvals/request", "/approvals/decide"):
            f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
            with DB_LOCK, db() as conn:
                if path == "/inquiries/save":
                    msg = U.save_inquiry(conn, f)
                    A.log(conn, "inquiry saved", msg)
                    return self.redirect("/inquiries?" + urlencode({"m": msg}))
                msg = U.make_request(conn, f) if path == "/approvals/request" else U.decide(conn, M.default_sn(conn), f)
                A.log(conn, "approval request" if path == "/approvals/request" else "approval decided", msg)
            return self.redirect("/approvals?" + urlencode({"m": msg}))
        if path == "/member/noexpiry":
            f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
            cid = f.get("id", "")
            with DB_LOCK, db() as conn:
                ok, msg = M.set_no_expiry(conn, M.default_sn(conn), int(cid), f.get("do") == "on") if cid.isdigit() else (False, "Member not found.")
                A.log(conn, "no expiry " + (f.get("do") or ""), "%s · %s" % (cid, msg))
            return self.redirect("/m?" + urlencode({"id": cid, "m": msg}))
        if path in ("/staff/rule", "/staff/excuse"):
            f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
            with DB_LOCK, db() as conn:
                U.init_staff(conn)
                if path == "/staff/rule":
                    msg = SH.save_rule(conn, f)
                    A.log(conn, "late rule saved", msg)
                    return self.redirect("/staff?" + urlencode({"m": msg}))
                pin, msg = SH.excuse(conn, f, U.staff_name())
                A.log(conn, "late day " + (f.get("do") or "excuse"), "%s %s" % (pin, msg))
            return self.redirect("/staff/report?" + urlencode({"pin": pin, "month": f.get("month", ""), "m": msg}))
        if path == "/staff/phone":
            f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
            with DB_LOCK, db() as conn:
                msg = U.save_staff_phone(conn, f)
                A.log(conn, "staff number", msg)
            return self.redirect("/staff?" + urlencode({"m": msg}))
        if path in ("/staff/shift", "/staff/save", "/salary/pay"):
            f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
            with DB_LOCK, db() as conn:
                if path == "/salary/pay":
                    month, msg = U.pay_salary(conn, f)
                    A.log(conn, "salary paid", msg)
                    return self.redirect("/salary?" + urlencode({"month": month, "m": msg}))
                msg = U.save_shift(conn, f) if path == "/staff/shift" else U.save_staff(conn, f)
                A.log(conn, "shift saved" if path == "/staff/shift" else "staff saved", msg)
            return self.redirect("/staff?" + urlencode({"m": msg}))
        if path == "/expenses/save":
            f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
            with DB_LOCK, db() as conn:
                msg = U.save_expense(conn, f)
                A.log(conn, "expense", msg)
            return self.redirect("/expenses?" + urlencode({"m": msg}))
        if path == "/settings/sheets":
            f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
            url = (f.get("gs_url") or "").strip()
            if url and not url.startswith("https://script.google.com/"):
                return self.redirect("/settings?" + urlencode({"m": "The link must start with https://script.google.com/"}))
            with DB_LOCK, db() as conn:
                M.set_setting(conn, "gs_url", url)
                A.log(conn, "sheets backup link saved" if f.get("do") != "sync" else "sheets backup started", "")
            if f.get("do") == "sync":
                threading.Thread(target=GS.sync, args=(DB_PATH,), daemon=True).start()
                return self.redirect("/settings?" + urlencode({"m": "Backup started. Refresh this page in a minute to see the result."}))
            return self.redirect("/settings?" + urlencode({"m": "Google Sheet link saved."}))
        if path in ("/settings/save", "/packages/save"):
            f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
            with DB_LOCK, db() as conn:
                if path == "/settings/save":
                    msg = U.save_settings(conn, f)
                    A.log(conn, "settings saved", "")
                    return self.redirect("/settings?" + urlencode({"m": msg}))
                msg = U.save_package(conn, f)
                A.log(conn, "package saved", msg)
            return self.redirect("/packages?" + urlencode({"m": msg}))
        if path in ("/attendance/manual", "/collect"):
            if not self.authorized():
                return self.ask_auth()
            f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
            with DB_LOCK, db() as conn:
                if path == "/collect":
                    inv, msg = U.save_collect(conn, f)
                    A.log(conn, "payment collected" if inv else "collect failed", msg)
                    if inv:
                        return self.redirect("/receipt?" + urlencode({"inv": inv, "m": msg}))
                    return self.redirect("/collect?" + urlencode({"id": f.get("id", ""), "m": msg}))
                msg = U.manual_checkin(conn, M.default_sn(conn), f)
                A.log(conn, "manual check-in", msg)
            return self.redirect("/attendance?" + urlencode({"m": msg}))
        if path in ("/assistant/ask", "/assistant/confirm", "/assistant/reset"):
            f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
            user = A.me()
            with DB_LOCK, db() as conn:
                sn = M.default_sn(conn)
            if path == "/assistant/reset":
                AS.reset(user)
                return self.send_text("{}", ctype="application/json")
            if path == "/assistant/ask":
                out = AS.ask(DB_PATH, sn, user, f.get("q", ""))
                with DB_LOCK, db() as conn:
                    A.log(conn, "AI assistant", (f.get("q") or "")[:200] + "".join(
                        " | proposed: " + a["label"] for a in out.get("actions", []) if a.get("type") == "confirm"))
                return self.send_text(json.dumps(out), ctype="application/json")
            with DB_LOCK, db() as conn:
                res = AS.confirm(conn, sn, user, f.get("id", ""))
                A.log(conn, "AI action confirmed", res)
            return self.send_text(json.dumps({"result": res}), ctype="application/json")
        if path == "/expenses/ai":
            f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
            out = U.expense_ai(None, f)
            with DB_LOCK, db() as conn:
                A.log(conn, "AI-fill expense", (f.get("text") or "")[:200] + (" + photo" if f.get("img") else "") +
                      (" -> " + out["error"] if out.get("error") else ""))
            return self.send_text(json.dumps(out), ctype="application/json")
        if path == "/bill/ai":
            f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
            with db() as conn:  # the AI call can take seconds; do not hold the lock during it
                out = U.ai_fill(conn, f)
            with DB_LOCK, db() as conn:
                A.log(conn, "AI-fill bill", (f.get("text") or "")[:200] + (" -> " + out["error"] if out.get("error") else ""))
            return self.send_text(json.dumps(out), ctype="application/json")
        if path == "/bill/save":
            if not self.authorized():
                return self.ask_auth()
            f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
            with DB_LOCK, db() as conn:
                inv, msg = U.save_bill(conn, M.default_sn(conn), f)
                if inv:
                    GS.soon()
                    if f.get("send_wa") == "1" and M.setting(conn, "wa_on_receipt", "1") == "1" and W.ready(conn):
                        text, m = U.receipt_text(conn, inv)
                        if m and W.enqueue(conn, "receipt", m["client_id"], m["phone"], text, inv):
                            f["send_wa"] = ""
                            msg += " Receipt is going on WhatsApp now."
                A.log(conn, "bill saved" if inv else "bill refused", "%s · %s · discount %s" % (
                    msg, f.get("member", ""), f.get("discount", "0")))
            if not inv:
                return self.redirect("/bill?" + urlencode({"m": msg}))
            return self.redirect("/receipt?" + urlencode({"inv": inv, "m": msg, "wa": f.get("send_wa", ""),
                                                          "print": f.get("print", "")}))
        if path == "/member/delete":
            f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
            cid = f.get("id", "")
            if f.get("confirm", "").strip().upper() != "DELETE":
                return self.redirect("/member/delete?" + urlencode({"id": cid, "m": "Type DELETE to confirm."}))
            with DB_LOCK, db() as conn:
                ok, msg = M.delete_member(conn, M.default_sn(conn), int(cid), A.is_admin(), f.get("bills") == "delete") \
                    if cid.isdigit() else (False, "Member not found.")
                A.log(conn, "member deleted" if ok else "member delete refused", "%s · %s" % (cid, msg))
            return self.redirect(("/members?" + urlencode({"m": msg})) if ok else ("/member?" + urlencode({"id": cid, "m": msg})))
        if path in ("/members/import", "/payments/import", "/member/save", "/member/door", "/sync"):
            if not self.authorized():
                return self.ask_auth()
            return self.handle_member_post(path, body)
        if path == "/admin/command":
            if not self.authorized():
                return self.ask_auth()
            msg = self.handle_admin_form(parse_qs(body))
            with DB_LOCK, db() as conn:
                A.log(conn, "gate command", msg)
            # Back to the main page so the auto-refresh never re-posts or 404s.
            return self.redirect("/gate?" + urlencode({"m": msg}))
        return self.send_text("OK")

    def handle_member_post(self, path, body):
        f = {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}
        with DB_LOCK, db() as conn:
            sn = M.default_sn(conn)
            if path == "/members/import":
                a, u, s = M.import_csv(conn, body)
                A.log(conn, "import members", "%d new, %d updated" % (a, u))
                return self.send_text("Imported: %d new, %d updated, %d skipped" % (a, u, s))
            if path == "/payments/import":
                n, skipped = M.import_bills(conn, body)
                A.log(conn, "import bills", "%d bills" % n)
                return self.send_text("Imported %d old bills, %d skipped" % (n, skipped))
            if path == "/member/save":
                cid_ = f.get("client_id", "")
                was_new = not (cid_.isdigit() and conn.execute("SELECT 1 FROM members WHERE client_id=?", (int(cid_),)).fetchone())
                ok, msg = M.save_member(conn, sn, f)
                if ok and f.get("join"):
                    J.linked(conn, f["join"], f.get("client_id", ""), U.staff_name())
                A.log(conn, "member saved", msg)
                cid = f.get("client_id", "")
                if ok and was_new and f.get("enroll_next") != "1":
                    return self.redirect("/bill?" + urlencode({"id": cid, "m": msg + " Now make the first bill."}))
                if ok and was_new and sn and not EN.fingers(conn, sn, cid):
                    # A new member: go straight to registering their finger on the gate machine.
                    return self.redirect("/enroll?" + urlencode({"id": cid, "m": msg + " Now register the fingerprint."}))
                return self.redirect("/m?" + urlencode({"id": cid, "m": msg}) if ok
                                     else "/member?" + urlencode({"m": msg}))
            if path == "/member/door":
                cid = f.get("id", "")
                if not sn or not cid.isdigit():
                    return self.redirect("/members")
                ok, msg = (M.unblock(conn, sn, cid) if f.get("do") == "unblock"
                           else M.block(conn, sn, cid, "manual"))
                A.log(conn, "door " + (f.get("do") or "block"), msg)
                return self.redirect("/m?" + urlencode({"id": cid, "m": msg}))
            # /sync
            do = f.get("do")
            if f.get("grace", "").isdigit():
                M.set_setting(conn, "grace_days", int(f["grace"]))
            if do == "auto_on":
                M.set_setting(conn, "auto_sync", "1")
                msg = "Automatic sync is ON."
            elif do == "auto_off":
                M.set_setting(conn, "auto_sync", "0")
                msg = "Automatic sync is OFF."
            elif do == "run" and sn:
                b, r = M.run_sync(conn, sn)
                A.log(conn, "door sync run", "%d blocked, %d restored" % (b, r))
                msg = "Sync queued: %d blocked, %d restored." % (b, r)
            else:
                msg = "Saved."
            return self.redirect("/sync?" + urlencode({"m": msg}))

    # ---------- device protocol ----------
    def options(self, sn):
        # Ask for everything: punches, user info and fingerprint templates.
        return "\n".join([
            "GET OPTION FROM: %s" % sn,
            "ATTLOGStamp=None",
            "OPERLOGStamp=None",
            "ATTPHOTOStamp=None",
            "ErrorDelay=30",
            "Delay=10",
            "TransTimes=00:00;14:05",
            "TransInterval=1",
            "TransFlag=TransData AttLog OpLog EnrollUser ChgUser EnrollFP ChgFP",
            "Realtime=1",
            "Encrypt=None",
            "",
        ])

    def next_command(self, sn):
        with DB_LOCK, db() as conn:
            D.expire_stale(conn, sn)
            EN.expire_stale(conn, sn)
            # Door opens jump the queue, then fingerprint enrolls (a person is waiting at the gate), then everything else in order.
            row = conn.execute(
                "SELECT id, cmd FROM commands WHERE sn=? AND sent_at IS NULL "
                "ORDER BY (cmd LIKE 'AC_UNLOCK%' OR cmd LIKE 'CONTROL DEVICE%') DESC, COALESCE(prio,0) DESC, id LIMIT 1",
                (sn,),
            ).fetchone()
            if not row or not D.is_door_cmd(row["cmd"]):
                hold = D.hold_command(conn)  # door held open: send another open on this poll
                if hold:
                    return "C:%d:%s\n" % hold
            if not row:
                return "OK"
            conn.execute("UPDATE commands SET sent_at=? WHERE id=?", (now(), row["id"]))
            return "C:%d:%s\n" % (row["id"], row["cmd"])

    def handle_upload(self, sn, table, body):
        lines = [l for l in body.replace("\r", "").split("\n") if l.strip()]
        n = 0
        with DB_LOCK, db() as conn:
            if table == "ATTLOG":
                for line in lines:
                    f = line.split("\t")
                    if len(f) < 2:
                        continue
                    f += [""] * 4
                    conn.execute(
                        "INSERT OR IGNORE INTO punches (sn, pin, ts, status, verify, raw, received_at) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (sn, f[0].strip(), f[1].strip(), f[2], f[3], line, now()),
                    )
                    n += 1
            else:
                # OPERLOG and friends: USER / FP / BIODATA lines, plus OPLOG noise.
                for line in lines:
                    kind, _, rest = line.partition(" ")
                    if kind in ("USER", "FP", "BIODATA", "FACE"):
                        d = kv_fields(rest)
                        pin = first(d, "PIN", "Pin")
                        idx = first(d, "FID", "No", "Index") if kind != "USER" else ""
                        conn.execute(
                            "INSERT OR REPLACE INTO records (sn, kind, pin, idx, payload, updated_at) "
                            "VALUES (?,?,?,?,?,?)",
                            (sn, kind, pin, idx, rest, now()),
                        )
                    n += 1
        return "OK: %d" % n

    def handle_querydata(self, sn, body):
        # Newer firmware answers DATA QUERY here, e.g. "user uid=1\tpin=356\tname=..."
        n = 0
        with DB_LOCK, db() as conn:
            for line in body.replace("\r", "").split("\n"):
                if not line.strip():
                    continue
                kind, _, rest = line.partition(" ")
                d = kv_fields(rest)
                pin = first(d, "pin", "PIN")
                idx = first(d, "fid", "FID", "no", "index")
                conn.execute(
                    "INSERT OR REPLACE INTO records (sn, kind, pin, idx, payload, updated_at) "
                    "VALUES (?,?,?,?,?,?)",
                    (sn, "Q:" + kind, pin, idx, rest, now()),
                )
                n += 1
        return n

    def handle_cmd_result(self, body):
        with DB_LOCK, db() as conn:
            for line in body.replace("\r", "").split("\n"):
                if not line.strip():
                    continue
                r = {k: v[0] for k, v in parse_qs(line).items()}
                if r.get("ID", "").isdigit() and D.hold_reply(conn, int(r["ID"]), r.get("Return", "")):
                    continue
                if r.get("ID", "").isdigit():
                    conn.execute(
                        "UPDATE commands SET return_code=?, done_at=? WHERE id=?",
                        (r.get("Return", ""), now(), int(r["ID"])),
                    )
        return "OK"

    # ---------- admin ----------
    def queue(self, conn, sn, cmd):
        conn.execute("INSERT INTO commands (sn, cmd, created_at) VALUES (?,?,?)", (sn, cmd, now()))

    def handle_admin_form(self, form):
        f = {k: v[0].strip() for k, v in form.items()}
        sn, action, pin = f.get("sn", ""), f.get("action", ""), f.get("pin", "")
        if not sn:
            return "Pick a machine first."
        with DB_LOCK, db() as conn:
            if action == "raw" and f.get("cmd"):
                self.queue(conn, sn, f["cmd"])
                return "Queued: " + f["cmd"]
            if action == "query_users":
                self.queue(conn, sn, "DATA QUERY USERINFO")
                return "Asked the machine for its user list."
            if action == "query_one" and pin:
                self.queue(conn, sn, "DATA QUERY USERINFO PIN=%s" % pin)
                self.queue(conn, sn, "DATA QUERY FINGERTMP PIN=%s" % pin)
                return "Asked the machine for member %s and their fingerprints." % pin
            if action == "block" and pin:
                have = conn.execute(
                    "SELECT COUNT(*) FROM records WHERE sn=? AND pin=? AND kind IN ('USER','FP','BIODATA')",
                    (sn, pin),
                ).fetchone()[0]
                fps = conn.execute(
                    "SELECT COUNT(*) FROM records WHERE sn=? AND pin=? AND kind IN ('FP','BIODATA')",
                    (sn, pin),
                ).fetchone()[0]
                if not have or not fps:
                    return ("Not blocked: no backup of member %s's fingerprint on the server yet. "
                            "Run 'Fetch one member' first and wait for it to arrive." % pin)
                self.queue(conn, sn, "DATA DELETE USERINFO PIN=%s" % pin)
                return "Block queued for %s (backup kept on server)." % pin
            if action == "unblock" and pin:
                rows = conn.execute(
                    "SELECT kind, payload FROM records WHERE sn=? AND pin=? AND kind IN ('USER','FP','BIODATA') "
                    "ORDER BY CASE kind WHEN 'USER' THEN 0 ELSE 1 END",
                    (sn, pin),
                ).fetchall()
                if not rows:
                    return "No backup for %s on the server." % pin
                table = {"USER": "USERINFO", "FP": "FINGERTMP", "BIODATA": "BIODATA"}
                for r in rows:
                    self.queue(conn, sn, "DATA UPDATE %s %s" % (table[r["kind"]], r["payload"]))
                return "Restore queued for %s (%d records)." % (pin, len(rows))
        return "Nothing to do."

    def admin_page(self, msg=""):
        e = html.escape
        with DB_LOCK, db() as conn:
            devices = conn.execute("SELECT * FROM devices ORDER BY last_seen DESC").fetchall()
            punches = conn.execute("SELECT * FROM punches ORDER BY ts DESC LIMIT 50").fetchall()
            cmds = conn.execute("SELECT * FROM commands ORDER BY id DESC LIMIT 20").fetchall()
            counts = conn.execute(
                "SELECT kind, COUNT(*) c FROM records GROUP BY kind ORDER BY kind").fetchall()
            raw = conn.execute("SELECT * FROM rawlog ORDER BY id DESC LIMIT 15").fetchall()

        def table(head, rows):
            th = "".join("<th>%s</th>" % e(h) for h in head)
            tr = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % e(str(c or "")) for c in r) for r in rows)
            return "<table><tr>%s</tr>%s</table>" % (th, tr or "<tr><td colspan=9>—</td></tr>")

        opts = "".join('<option value="%s">%s</option>' % (e(d["sn"]), e(d["sn"])) for d in devices)
        return """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="15;url=/gate"><title>HOS gate test</title>
<style>body{font-family:system-ui,sans-serif;background:#0b0b0c;color:#f4f4f5;margin:0;padding:16px}
h1{color:#ff5a5a;margin:0 0 8px}h2{margin:24px 0 8px;font-size:18px}
table{border-collapse:collapse;width:100%%;font-size:13px;display:block;overflow-x:auto}
td,th{border:1px solid #2a2a2e;padding:6px 8px;text-align:left;white-space:nowrap}th{background:#1d1d20}
form{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:6px 0}
input,select,button{min-height:40px;padding:0 10px;border-radius:8px;border:1px solid #333;background:#151517;color:#fff}
button{background:#d90b16;border:0;font-weight:600;cursor:pointer}.msg{background:#1f2a1a;padding:10px;border-radius:8px}</style>
</head><body><h1>House of Strength — gate test</h1>
<p><a href="/today" style="color:#ff7a7a">Today</a> · <a href="/members" style="color:#ff7a7a">Members</a> · <a href="/member" style="color:#ff7a7a">Add / Renew</a> · <a href="/sync" style="color:#ff7a7a">Door sync</a> · <a href="/backup" style="color:#ff7a7a">Download backup</a></p>
<p>Page refreshes every 15 seconds. Server time %s</p>%s
<h2>Machines</h2>%s
<h2>Last punches</h2>%s
<h2>Commands</h2>
<form method="post" action="/admin/command"><select name="sn">%s</select>
<input type="hidden" name="action" value="query_users"><button>Fetch user list</button></form>
<form method="post" action="/admin/command"><select name="sn">%s</select>
<input name="pin" placeholder="Biometric ID" required><select name="action">
<option value="query_one">Fetch one member + fingerprint</option>
<option value="block">Block door (delete from machine, keep backup)</option>
<option value="unblock">Unblock door (restore from backup)</option></select><button>Send</button></form>
<form method="post" action="/admin/command"><select name="sn">%s</select>
<input type="hidden" name="action" value="raw"><input name="cmd" placeholder="Raw command (advanced)" size="40" required>
<button>Queue</button></form>
%s
<h2>Stored member records</h2>%s
<h2>Raw traffic (debug)</h2>%s
</body></html>""" % (
            e(now()),
            '<p class="msg">%s</p>' % e(msg) if msg else "",
            table(["Serial", "IP", "Info", "First seen", "Last seen"],
                  [(d["sn"], d["ip"], d["info"], d["first_seen"], d["last_seen"]) for d in devices]),
            table(["Biometric ID", "Time", "Status", "Verify", "Machine", "Received"],
                  [(p["pin"], p["ts"], p["status"], p["verify"], p["sn"], p["received_at"]) for p in punches]),
            opts, opts, opts,
            table(["#", "Machine", "Command", "Queued", "Sent", "Result", "Done"],
                  [(c["id"], c["sn"], c["cmd"][:90], c["created_at"], c["sent_at"], c["return_code"], c["done_at"])
                   for c in cmds]),
            table(["Kind", "Count"], [(c["kind"], c["c"]) for c in counts]),
            table(["At", "Method", "Path", "Body"],
                  [(r["at"], r["method"], r["path"][:80], r["body"][:200]) for r in raw]),
        )


def snapshot_to(path):
    """Consistent copy of the live database (safe while the server writes)."""
    with DB_LOCK:
        src = sqlite3.connect(DB_PATH, timeout=10)
        dst = sqlite3.connect(path)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()


def snapshot_bytes():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    tmp = os.path.join(BACKUP_DIR, ".download.tmp")
    snapshot_to(tmp)
    with open(tmp, "rb") as f:
        data = f.read()
    os.remove(tmp)
    return data


def backup_loop():
    """Once a day: hos-YYYY-MM-DD.db in BACKUP_DIR, keeping the newest KEEP_BACKUPS."""
    while True:
        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)
            name = os.path.join(BACKUP_DIR, "hos-%s.db" % datetime.date.today().isoformat())
            if not os.path.exists(name):
                snapshot_to(name)
                print("%s backup written %s" % (now(), name), flush=True)
            old = sorted(f for f in os.listdir(BACKUP_DIR) if f.startswith("hos-") and f.endswith(".db"))
            for f in old[:-KEEP_BACKUPS]:
                os.remove(os.path.join(BACKUP_DIR, f))
        except Exception as exc:
            print("%s backup error: %s" % (now(), exc), flush=True)
        threading.Event().wait(3600)


def auto_sync_loop():
    """Every 30 minutes: if automatic sync is switched on, block/restore by expiry."""
    while True:
        try:
            with DB_LOCK, db() as conn:
                sn = M.default_sn(conn)
                if sn and M.setting(conn, "auto_sync", "0") == "1":
                    b, r = M.run_sync(conn, sn)
                    print("%s auto sync: blocked %d, restored %d" % (now(), b, r), flush=True)
        except Exception as exc:  # keep the loop alive
            print("%s auto sync error: %s" % (now(), exc), flush=True)
        threading.Event().wait(1800)


def main():
    if not ADMIN_PASS:
        sys.exit("Set ADMIN_PASS before starting, e.g. ADMIN_PASS=secret python3 adms_server.py")
    init_db()
    threading.Thread(target=auto_sync_loop, daemon=True).start()
    threading.Thread(target=backup_loop, daemon=True).start()
    threading.Thread(target=GS.loop, args=(DB_PATH,), daemon=True).start()
    threading.Thread(target=W.loop, args=(DB_PATH,), daemon=True).start()
    threading.Thread(target=SH.loop, args=(DB_PATH,), daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("%s listening on port %d, database %s" % (now(), PORT, DB_PATH), flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
