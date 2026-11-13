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
import html
import os
import sqlite3
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "8081"))
DB_PATH = os.environ.get("DB_PATH", os.path.join(HERE, "hos.db"))
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "")

DB_LOCK = threading.Lock()

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
        sys.stderr.write("%s %s - %s\n" % (now(), self.client_address[0], fmt % args))

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

    def authorized(self):
        header = self.headers.get("Authorization", "")
        if header.startswith("Basic "):
            try:
                user, _, pw = base64.b64decode(header[6:]).decode().partition(":")
            except Exception:
                return False
            return hmac.compare_digest(user, ADMIN_USER) and hmac.compare_digest(pw, ADMIN_PASS)
        return False

    def ask_auth(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="House of Strength"')
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
        if path in ("/", "/admin"):
            if not self.authorized():
                return self.ask_auth()
            return self.send_text(self.admin_page(), ctype="text/html")
        return self.send_text("Not found", 404)

    def do_POST(self):
        path, q = self.route()
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
        if path == "/admin/command":
            if not self.authorized():
                return self.ask_auth()
            msg = self.handle_admin_form(parse_qs(body))
            return self.send_text(self.admin_page(msg), ctype="text/html")
        return self.send_text("OK")

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
            row = conn.execute(
                "SELECT id, cmd FROM commands WHERE sn=? AND sent_at IS NULL ORDER BY id LIMIT 1",
                (sn,),
            ).fetchone()
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
<meta http-equiv="refresh" content="15"><title>HOS gate test</title>
<style>body{font-family:system-ui,sans-serif;background:#0b0b0c;color:#f4f4f5;margin:0;padding:16px}
h1{color:#ff5a5a;margin:0 0 8px}h2{margin:24px 0 8px;font-size:18px}
table{border-collapse:collapse;width:100%%;font-size:13px;display:block;overflow-x:auto}
td,th{border:1px solid #2a2a2e;padding:6px 8px;text-align:left;white-space:nowrap}th{background:#1d1d20}
form{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:6px 0}
input,select,button{min-height:40px;padding:0 10px;border-radius:8px;border:1px solid #333;background:#151517;color:#fff}
button{background:#d90b16;border:0;font-weight:600;cursor:pointer}.msg{background:#1f2a1a;padding:10px;border-radius:8px}</style>
</head><body><h1>House of Strength — gate test</h1>
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


def main():
    if not ADMIN_PASS:
        sys.exit("Set ADMIN_PASS before starting, e.g. ADMIN_PASS=secret python3 adms_server.py")
    init_db()
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print("%s listening on port %d, database %s" % (now(), PORT, DB_PATH), flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
