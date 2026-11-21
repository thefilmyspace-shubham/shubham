"""Register a member's fingerprint from the app.

The app puts the member on the gate machine (USERINFO with their ID and name) and sends the
machine's remote-enroll command (ENROLL_FP). The machine then shows its enroll screen: the
member places the same finger three times, and the machine uploads the new template, which
this server keeps like every other fingerprint (so door sync can restore it later).

The machine asks for work about every 10 seconds. An enroll it has not picked up within
3 minutes is dropped. Some firmware does not allow remote enroll; then the page says so and
shows the steps to do it on the machine itself.
"""
import datetime
import html
import json
import re

import members as M

e = html.escape
# ZKTeco finger numbers: 0-4 left hand (little .. thumb), 5-9 right hand (thumb .. little)
FINGERS = [(6, "Right index"), (5, "Right thumb"), (7, "Right middle"), (3, "Left index"), (4, "Left thumb"), (2, "Left middle")]
FINGER_NAME = dict([(0, "Left little"), (1, "Left ring"), (2, "Left middle"), (3, "Left index"), (4, "Left thumb"), (5, "Right thumb"),
                    (6, "Right index"), (7, "Right middle"), (8, "Right ring"), (9, "Right little")])
STALE_MIN = 3


def init(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS enroll_log (
        id INTEGER PRIMARY KEY, client_id INTEGER, fid INTEGER, user_cmd INTEGER, enroll_cmd INTEGER,
        fp_before INTEGER, at TEXT, by_name TEXT, fresh INTEGER DEFAULT 0, cleaned INTEGER DEFAULT 0)""")
    lcols = {r[1] for r in conn.execute("PRAGMA table_info(enroll_log)")}
    for col in ("fresh", "cleaned"):
        if col not in lcols:
            conn.execute("ALTER TABLE enroll_log ADD COLUMN %s INTEGER DEFAULT 0" % col)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(commands)")}
    if "prio" not in cols:
        conn.execute("ALTER TABLE commands ADD COLUMN prio INTEGER DEFAULT 0")


def fingers(conn, sn, pin):
    """Finger numbers the server holds a template for."""
    out = []
    for (idx,) in conn.execute("SELECT idx FROM records WHERE sn=? AND pin=? AND kind IN ('FP','BIODATA')", (sn, str(pin))):
        if str(idx).isdigit():
            out.append(int(idx))
    return sorted(set(out))


def on_machine(conn, sn, pin):
    return bool(conn.execute("SELECT 1 FROM records WHERE sn=? AND pin=? AND kind='USER'", (sn, str(pin))).fetchone())


def _q(conn, sn, cmd):
    conn.execute("INSERT INTO commands (sn, cmd, created_at, prio) VALUES (?,?,?,1)",
                 (sn, cmd, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def machine_name(name):
    """The machine shows plain letters only, up to 24."""
    s = re.sub(r"[^A-Za-z0-9 .]", "", " ".join(w.capitalize() for w in (name or "").split()))
    return s[:24].strip() or "Member"


def expire_stale(conn, sn):
    cut = (datetime.datetime.now() - datetime.timedelta(minutes=STALE_MIN)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE commands SET sent_at=?, return_code='expired', done_at=? WHERE sn=? AND sent_at IS NULL "
                 "AND prio=1 AND created_at < ?", (cut, cut, sn, cut))


def start(conn, sn, cid, fid, who, fresh=False):
    """Queue the enroll. Returns (ok, message)."""
    if not sn:
        return False, "No gate machine is connected yet."
    m = conn.execute("SELECT * FROM members WHERE client_id=?", (cid,)).fetchone() if str(cid).isdigit() else None
    staff = None
    if not m and str(cid).isdigit() and int(cid) >= M.STAFF_FROM:
        staff = conn.execute("SELECT * FROM staff WHERE pin=?", (str(cid),)).fetchone()
    if not m and not staff:
        return False, "Member not found. Save the member first."
    fid = int(fid) if str(fid).isdigit() and 0 <= int(fid) <= 9 else 6
    pin = str(cid)
    if pin in M.blocked_pins(conn, sn):
        return False, "This member is blocked at the door (membership ended). Renew first, then register the finger."
    name = machine_name((m or staff)["name"])
    user_cmd = _q(conn, sn, "DATA UPDATE USERINFO PIN=%s\tName=%s\tPri=0" % (pin, name)) if not on_machine(conn, sn, pin) else None
    if fresh:
        # Calibrate from scratch: the machine forgets this person's old fingers before the new scan.
        _q(conn, sn, "DATA DELETE FINGERTMP PIN=%s" % pin)
    enroll_cmd = _q(conn, sn, "ENROLL_FP PIN=%s\tFID=%d\tRETRY=3\tOVERWRITE=1" % (pin, fid))
    conn.execute("INSERT INTO enroll_log (client_id, fid, user_cmd, enroll_cmd, fp_before, at, by_name, fresh) VALUES (?,?,?,?,?,?,?,?)",
                 (int(cid), fid, user_cmd, enroll_cmd, len(fingers(conn, sn, pin)), M.stamp(), who, 1 if fresh else 0))
    return True, "Sent to the gate machine: %s (ID %s), %s finger%s." % (
        name, pin, FINGER_NAME.get(fid, ""), " (old fingerprints removed first)" if fresh else "")


def status(conn, sn, cid):
    """Where the latest enroll for this member stands, for the page to show."""
    r = conn.execute("SELECT * FROM enroll_log WHERE client_id=? ORDER BY id DESC LIMIT 1", (cid,)).fetchone() if str(cid).isdigit() else None
    fps = fingers(conn, sn, cid)
    out = {"fingers": [FINGER_NAME.get(f, str(f)) for f in fps], "state": "none", "text": "", "done": True}
    if not r:
        return out
    c = conn.execute("SELECT * FROM commands WHERE id=?", (r["enroll_cmd"],)).fetchone()
    # Success = the machine sent a template for that finger after the enroll was asked for.
    got_new = bool(conn.execute("SELECT 1 FROM records WHERE sn=? AND pin=? AND kind IN ('FP','BIODATA') AND idx=? AND updated_at >= ?",
                                (sn, str(cid), str(r["fid"]), r["at"])).fetchone())
    if got_new:
        if r["fresh"] and not r["cleaned"]:
            # Fresh calibration: forget the server's copies of the old fingers too, so a later door unblock
            # does not put them back.
            conn.execute("DELETE FROM records WHERE sn=? AND pin=? AND kind IN ('FP','BIODATA') AND updated_at < ?", (sn, str(cid), r["at"]))
            conn.execute("UPDATE enroll_log SET cleaned=1 WHERE id=?", (r["id"],))
            out["fingers"] = [FINGER_NAME.get(f, str(f)) for f in fingers(conn, sn, cid)]
        out.update(state="ok", text="Fingerprint saved ✅ (%s). The member can use the door now." % FINGER_NAME.get(r["fid"], ""))
    elif not c:
        out.update(state="bad", text="Enroll request was lost. Try again.")
    elif c["return_code"] == "expired":
        out.update(state="bad", text="The gate machine did not answer. Check it is on and online, then try again.")
    elif c["done_at"] and c["return_code"] == "0":
        out.update(state="wait", text="The machine says done; waiting for it to send the fingerprint…", done=False)
    elif c["done_at"]:
        out.update(state="bad", text="The machine said no (code %s). If it keeps saying no, this machine does not allow "
                                     "registering from the app: register on the machine instead (steps below)." % c["return_code"])
    elif c["sent_at"]:
        out.update(state="wait", text="On the machine now: ask the member to place the %s finger on the scanner 3 times."
                                      % FINGER_NAME.get(r["fid"], "").lower(), done=False)
    else:
        out.update(state="wait", text="Waiting for the gate machine to pick it up (it checks every 10 seconds)…", done=False)
    return out


def page(conn, sn, q):
    import ui as U
    cid = q.get("id", "")
    m = conn.execute("SELECT * FROM members WHERE client_id=?", (cid,)).fetchone() if cid.isdigit() else None
    staff = conn.execute("SELECT * FROM staff WHERE pin=?", (cid,)).fetchone() if (not m and cid.isdigit()) else None
    who = m or staff
    if not who:
        return U.shell("Register fingerprint", "/members", '<div class="panel">Member not found. <a href="/members">Back</a></div>')
    online = U.gate_online(conn)
    st = status(conn, sn, cid)
    have = st["fingers"]
    opts = "".join('<option value="%d"%s>%s</option>' % (f, " selected" if i == (1 if have else 0) else "", l) for i, (f, l) in enumerate(FINGERS))
    back = ("/m?id=%s" % cid) if m else "/staff"
    body = """<div class="two"><div class="panel" style="display:flex;flex-direction:column;gap:14px">
<div class="ph" style="margin:0"><h2>%s · ID %s</h2><span class="pill %s">%s</span></div>
<div class="kv"><div><span>Fingers saved</span><b>%s</b></div><div><span>On the gate machine</span><b>%s</b></div></div>
<form method="post" action="/enroll/start" style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end;margin:0">
<input type="hidden" name="id" value="%s"><label style="flex:1 1 180px">Finger<select name="fid">%s</select></label>
<button class="btn red" style="min-height:52px;font-size:16px"%s>%s%s</button>%s</form>
<div id="enst" style="font-size:15px;line-height:1.5"></div>
<p class="dim" style="margin:0;font-size:12px">Register two fingers (say, both index fingers), so the door still opens if one finger has a cut.
<b>Finger not reading at the door?</b> Calibrate: scan the same finger again, pressing flat and covering the whole scanner.</p>%s</div>
<div class="panel" style="display:flex;flex-direction:column;gap:10px"><div class="ph" style="margin:0"><h2>How it works</h2></div>
<ol style="margin:0;padding-left:20px;line-height:1.9"><li>Member stands at the gate machine.</li><li>Tap <b>Register on gate machine</b>. Within about 10 seconds
the machine shows its enroll screen.</li><li>Member places the chosen finger on the scanner <b>3 times</b>, lifting it each time.</li>
<li>This page shows <b>Fingerprint saved</b>. Done: the door opens for them.</li></ol>
<p class="dim" style="margin:6px 0 0;font-size:12px"><b>If the machine never shows the enroll screen</b> (some machines don't allow it from the app):
on the machine press <b>M/OK → User Mgt → New User</b>, set User ID <b>%s</b>, choose <b>FP</b>, place the finger 3 times, save.
It reaches this app by itself.</p><a class="btn" href="%s" style="align-self:flex-start">Back</a></div></div>
<script>(function(){var box=document.getElementById('enst'),n=0,cls={ok:'p-ok',bad:'p-bad',wait:'p-warn'};
function tick(){fetch('/enroll/status?id=%s',{cache:'no-store'}).then(function(r){return r.json()}).then(function(d){
if(d.state==='none'){box.innerHTML='';return}box.innerHTML='<span class="pill '+(cls[d.state]||'')+'" style="white-space:normal;line-height:1.5;padding:8px 12px;display:inline-block">'+d.text+'</span>';
if(!d.done&&++n<150){setTimeout(tick,2000)}else if(d.state==='ok'&&n>0){setTimeout(function(){location.reload()},2500)}})}tick()})();</script>""" % (
        e(U.nice(who["name"])), e(cid), "p-ok" if online else "p-bad", "Machine online" if online else "Machine offline",
        e(", ".join(have)) if have else '<span style="color:var(--red)">None yet</span>', "Yes" if on_machine(conn, sn, cid) else "Not yet",
        e(cid), opts, "" if online else " disabled", U.icon("finger", 18),
        "Calibrate: scan again" if have else "Register on gate machine",
        ('<label class="chk" style="flex-basis:100%%;font-size:13px"><input type="checkbox" name="fresh" value="1">Start fresh: remove this '
         'person\'s old fingerprints from the machine first (use when the finger keeps failing)</label>') if have else "",
        ('<a class="btn" href="/bill?id=%s" style="align-self:flex-start">Next: make the first bill →</a>' % e(cid))
        if m and not conn.execute("SELECT 1 FROM payments WHERE client_id=?", (m["client_id"],)).fetchone() else "",
        e(cid), back, e(cid))
    return U.shell("Calibrate fingerprint" if have else "Register fingerprint", "/members", body, sub='<a href="%s">%s</a> › Fingerprint' % (back, e(U.nice(who["name"]))),
                   msg=q.get("m", ""), warn="" if online else "The gate machine is offline. Turn it on and check its internet first.",
                   cnt=U.counts(conn, sn))


def status_json(conn, sn, cid):
    return json.dumps(status(conn, sn, cid))
