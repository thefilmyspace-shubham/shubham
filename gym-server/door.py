"""Open the gym door from the app, for a visitor, a trial or a member whose finger does not read.

The gate machine asks this server for work every 10 seconds, so the door opens within
about 10 seconds of the tap. Every open is written to the door log with who asked and why.

Commands (ZKTeco push protocol):
  AC_UNLOCK                    open the lock for the machine's own lock time (a few seconds)
  CONTROL DEVICE 010101SS      open door 1 for SS seconds (hex); FF = stay open, 00 = lock now
Some machines take only one of the two forms, so the owner can switch the method if
"Open" does not work. An open that the machine has not picked up within a minute is
dropped, so a door never opens late on its own.
"""
import datetime
import html
import json

import members as M

e = html.escape
STALE_SECONDS = 60
DOOR_PREFIXES = ("AC_UNLOCK", "CONTROL DEVICE")
METHODS = {"1": "AC_UNLOCK", "2": "CONTROL DEVICE 01010105"}
ACTIONS = {"open": "Open for a few seconds", "hold": "Keep open", "lock": "Lock again"}


def init(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS door_log (
        id INTEGER PRIMARY KEY, at TEXT, action TEXT, reason TEXT, by_name TEXT, by_role TEXT, command_id INTEGER)""")
    conn.execute("INSERT OR IGNORE INTO settings VALUES ('door_method', '1')")


def is_door_cmd(cmd):
    return (cmd or "").startswith(DOOR_PREFIXES)


def expire_stale(conn, sn):
    """Drop door commands the machine never picked up: a visitor who left must not get an open door later."""
    cut = (datetime.datetime.now() - datetime.timedelta(seconds=STALE_SECONDS)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE commands SET sent_at=?, return_code='expired', done_at=? WHERE sn=? AND sent_at IS NULL "
                 "AND (cmd LIKE 'AC_UNLOCK%' OR cmd LIKE 'CONTROL DEVICE%') AND created_at < ?",
                 (cut, cut, sn, cut))


def command_for(conn, action):
    if action == "hold":
        return "CONTROL DEVICE 010101FF"
    if action == "lock":
        return "CONTROL DEVICE 01010100"
    return METHODS.get(M.setting(conn, "door_method", "1"), "AC_UNLOCK")


def request(conn, sn, action, reason, who, role):
    """Queue a door command. Returns a message for the page."""
    if not sn:
        return "No gate machine is connected yet."
    if action not in ACTIONS:
        action = "open"
    reason = " ".join((reason or "").split())[:120]
    if not reason:
        return "Write who it is for (e.g. 'Visitor: Rahul, trial')."
    if action in ("hold", "lock") and role != "admin":
        return "Only the owner can keep the door open."
    cmd = command_for(conn, action)
    conn.execute("INSERT INTO commands (sn, cmd, created_at) VALUES (?,?,?)",
                 (sn, cmd, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    cid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("INSERT INTO door_log (at, action, reason, by_name, by_role, command_id) VALUES (?,?,?,?,?,?)",
                 (M.stamp(), action, reason, who, role, cid))
    return {"open": "Opening the door… it opens within about 10 seconds.",
            "hold": "Door will stay open until you press Lock again.",
            "lock": "Locking the door…"}[action]


def state_of(row):
    if row["return_code"] == "expired":
        return "p-bad", "Machine did not answer"
    if row["done_at"]:
        return ("p-ok", "Done") if row["return_code"] in ("0", "") else ("p-bad", "Machine said no (%s)" % row["return_code"])
    if row["sent_at"]:
        return "p-warn", "Sent to machine…"
    return "p-warn", "Waiting for machine…"


def recent(conn, n=15):
    return conn.execute("SELECT d.*, c.sent_at, c.done_at, c.return_code, c.cmd FROM door_log d LEFT JOIN commands c "
                        "ON c.id = d.command_id ORDER BY d.id DESC LIMIT ?", (n,)).fetchall()


def status_json(conn):
    rows = recent(conn, 1)
    if not rows:
        return json.dumps({})
    cls, text = state_of(rows[0])
    return json.dumps({"id": rows[0]["id"], "cls": cls, "text": text, "done": cls != "p-warn"})


def page(conn, sn, q):
    import ui as U
    online = U.gate_online(conn)
    admin = U.A.is_admin()
    rows = recent(conn)
    trs = ""
    for r in rows:
        cls, text = state_of(r)
        trs += '<tr><td class="dim">%s</td><td>%s</td><td>%s</td><td>%s</td><td><span class="pill %s">%s</span></td></tr>' % (
            e((r["at"] or "")[:16]), e(ACTIONS.get(r["action"], r["action"])), e(r["reason"] or ""), e(r["by_name"] or ""), cls, e(text))
    method = M.setting(conn, "door_method", "1")
    extra = ""
    if admin:
        extra = """<div class="panel" style="display:flex;flex-direction:column;gap:12px"><div class="ph" style="margin:0"><h2>Owner only</h2></div>
<form method="post" action="/door/open" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin:0">
<label style="flex:1 1 220px">Reason<input name="reason" placeholder="e.g. Event / cleaning" required></label>
<button class="btn" name="action" value="hold">Keep door open</button><button class="btn red" name="action" value="lock">Lock again</button></form>
<form method="post" action="/door/method" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin:0">
<label style="flex:1 1 220px">Open method (if the door does not open, try the other one)<select name="method">
<option value="1"%s>Method 1 (AC_UNLOCK)</option><option value="2"%s>Method 2 (CONTROL DEVICE)</option></select></label>
<button class="btn">Save method</button></form>
<p class="dim" style="margin:0;font-size:12px">“Keep door open” and “Lock again” work only on machines that take Method 2 commands.
If the machine says no, the door stays as it is.</p></div>""" % (" selected" if method == "1" else "", " selected" if method == "2" else "")
    body = """<div class="two"><div class="panel" style="display:flex;flex-direction:column;gap:14px">
<div class="ph" style="margin:0"><h2>Open the gate</h2><span class="pill %s">%s</span></div>
<p class="dim" style="margin:0">For a visitor, a trial, or a member whose finger does not read. The door opens for a few seconds,
within about 10 seconds of tapping. Every open is saved with your name.</p>
<form method="post" action="/door/open" id="doorf" style="display:flex;flex-direction:column;gap:12px;margin:0">
<label>Who is it for?<input name="reason" list="dreasons" placeholder="e.g. Visitor: Rahul (trial)" required autocomplete="off"></label>
<datalist id="dreasons"><option value="Visitor"><option value="Trial"><option value="Finger not reading"><option value="Delivery"><option value="Staff"></datalist>
<button class="btn red" name="action" value="open" style="min-height:64px;font-size:20px">%sOPEN DOOR</button></form>
<div id="dstate" style="font-size:15px"></div></div>%s</div>
<div class="panel"><div class="ph"><h2>Door log</h2><span class="dim" style="font-size:12px">Last 15</span></div><div class="tw"><table>
<tr><th>When</th><th>What</th><th>For</th><th>By</th><th>Result</th></tr>%s</table></div></div>
<script>(function(){var box=document.getElementById('dstate');if(!%s){return}var n=0;
function tick(){fetch('/door/status',{cache:'no-store'}).then(function(r){return r.json()}).then(function(d){if(!d.id){return}
box.innerHTML='<span class="pill '+d.cls+'">'+d.text+'</span>';if(d.done){setTimeout(function(){location.href='/door'},1500);return}
if(++n<40){setTimeout(tick,1500)}})}tick()})();</script>""" % (
        "p-ok" if online else "p-bad", "Machine online" if online else "Machine offline", U.icon("door", 22), extra,
        trs or '<tr><td colspan="5" class="dim">No openings yet.</td></tr>', "true" if q.get("wait") == "1" else "false")
    return U.shell("Open gate", "/door", body, sub="Let someone in without a fingerprint", msg=q.get("m", ""),
                   warn="" if online else "The gate machine has not talked to the server in the last 5 minutes. Check its power and internet.",
                   cnt=U.counts(conn, sn))
