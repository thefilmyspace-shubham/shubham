"""Automatic backup of the gym's data into a Google Sheet in the owner's Drive.

No Google Cloud keys: the owner pastes a small Apps Script (shown on the Settings page)
into their own Sheet and deploys it as a web app. This server POSTs each tab's rows,
with a shared secret, every night and shortly after every bill.
"""
import datetime
import json
import secrets
import sqlite3
import threading
import time
import urllib.request

import members as M

LOCK = threading.Lock()
_pending = threading.Event()

APPS_SCRIPT = """const SECRET = '%s';
function doPost(e) {
  const d = JSON.parse(e.postData.contents);
  if (d.secret !== SECRET) return out({ok: false, error: 'wrong secret'});
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName(d.tab) || ss.insertSheet(d.tab);
  sh.clearContents();
  if (d.rows.length) sh.getRange(1, 1, d.rows.length, d.rows[0].length).setValues(d.rows);
  sh.setFrozenRows(1);
  return out({ok: true, tab: d.tab, rows: d.rows.length});
}
function out(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }"""


def init(conn):
    if not M.setting(conn, "gs_secret"):
        M.set_setting(conn, "gs_secret", secrets.token_urlsafe(18))


def _tables(conn):
    def q(sql, *a):
        try:
            return [list(r) for r in conn.execute(sql, a).fetchall()]
        except sqlite3.OperationalError:  # table not created yet
            return []
    tabs = {
        "Members": (["Client ID", "Name", "Phone", "Gender", "Registration", "Package", "Expiry", "Pending"],
                    q("SELECT client_id, name, phone, gender, registration, package, expiry, pending FROM members ORDER BY client_id")),
        "Bills": (["Invoice", "Paid on", "Client ID", "Package", "Start", "End", "Trainer", "List price", "Discount", "Admission",
                   "GST", "Payable", "Paid", "Balance", "Mode", "Prepared by", "Note"],
                  q("SELECT invoice, paid_on, client_id, package, start, expiry, trainer, list_price, discount, admission, gst, payable, "
                    "amount, balance, mode, created_by, note FROM payments ORDER BY paid_on, id")),
        "Attendance": (["Date", "Time", "ID", "In/Out", "Source"],
                       [[r[0][:10], r[0][11:19], r[1], "Out" if r[2] == "1" else "In", r[3] or "gate"]
                        for r in q("SELECT ts, pin, status, verify FROM punches ORDER BY ts")]),
        "Expenses": (["Date", "Category", "Amount", "Paid to", "Mode", "Note", "Added by"],
                     q("SELECT spent_on, category, amount, paid_to, mode, note, created_by FROM expenses ORDER BY spent_on")),
        "Salaries": (["Month", "Staff ID", "Present", "Working days", "Salary", "Incentive", "Advance", "Deduction", "Paid", "Paid on", "Mode"],
                     q("SELECT month, pin, present, working, base, incentive, advance, deduction, payable, paid_on, mode FROM salary_pay ORDER BY month")),
        "Staff": (["Gate ID", "Name", "Role", "Phone", "Salary", "Shift ID", "Working"],
                  q("SELECT pin, name, role, phone, salary, shift_id, active FROM staff ORDER BY pin")),
        "Inquiries": (["Created", "Name", "Phone", "Interested in", "Source", "Stage", "Next follow-up", "Note"],
                      q("SELECT created_at, name, phone, interest, source, stage, next_date, note FROM inquiries ORDER BY id")),
    }
    out = {}
    for name, (head, rows) in tabs.items():
        clean = [["" if v is None else v for v in r] for r in rows]
        out[name] = [head] + clean
    return out


def _post(url, payload):
    data = json.dumps(payload, default=str).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:  # Apps Script answers through a redirect; urllib follows it
        return json.loads(r.read().decode() or "{}")


def sync(db_path, only=None):
    """Push every tab (or only the named ones). Returns a short status line."""
    with LOCK:
        conn = sqlite3.connect(db_path, timeout=10)
        try:
            url, secret = M.setting(conn, "gs_url").strip(), M.setting(conn, "gs_secret")
            if not url:
                return "Google Sheet link not set."
            tabs = _tables(conn)
        finally:
            conn.close()
        done, errors = [], []
        for name, rows in tabs.items():
            if only and name not in only:
                continue
            try:
                res = _post(url, {"secret": secret, "tab": name, "rows": rows})
                if res.get("ok"):
                    done.append("%s %d" % (name, len(rows) - 1))
                else:
                    errors.append("%s: %s" % (name, res.get("error", "failed")))
            except Exception as exc:
                errors.append("%s: %s" % (name, type(exc).__name__))
        status = "%s · %s%s" % (datetime.datetime.now().strftime("%d %b %H:%M"), ", ".join(done) or "nothing sent",
                                (" · errors: " + "; ".join(errors)) if errors else "")
        conn = sqlite3.connect(db_path, timeout=10)
        try:
            M.set_setting(conn, "gs_last", status)
            conn.commit()
        finally:
            conn.close()
        return status


def soon():
    """Ask the background loop to push Bills and Members within a minute (after a bill)."""
    _pending.set()


def loop(db_path):
    """Nightly full backup around 2 AM, plus quick Bills/Members pushes after bills."""
    last_night = None
    while True:
        try:
            now = datetime.datetime.now()
            if now.hour == 2 and last_night != now.date():
                last_night = now.date()
                print("sheets backup: %s" % sync(db_path), flush=True)
            elif _pending.is_set():
                _pending.clear()
                sync(db_path, only={"Bills", "Members"})
        except Exception as exc:
            print("sheets backup error: %s" % exc, flush=True)
        _pending.wait(60)


def settings_block(conn):
    import html
    e = html.escape
    url = M.setting(conn, "gs_url")
    return """<div class="panel" style="display:flex;flex-direction:column;gap:14px"><h2>Google Sheets backup</h2>
<p class="dim" style="margin:0">Every night (2 AM) and a minute after every bill, all data is copied into your own Google Sheet: Members, Bills,
Attendance, Expenses, Salaries, Staff, Inquiries, one tab each. Only people you share the Sheet with can open it.</p>
<ol style="margin:0;padding-left:20px;line-height:1.9">
<li>Open <b>sheets.new</b> with the gym's Google account. Name it <b>HOS Backup</b>.</li>
<li>In that Sheet: <b>Extensions → Apps Script</b>. Delete what is there and paste the code below. Press <b>Save</b>.</li>
<li><b>Deploy → New deployment</b> → type <b>Web app</b> → Execute as <b>Me</b>, Who has access <b>Anyone</b> → <b>Deploy</b> → allow access.</li>
<li>Copy the <b>Web app URL</b> (ends in <b>/exec</b>), paste it below, Save, then <b>Back up now</b>.</li></ol>
<textarea readonly style="min-height:230px;padding:12px;font:12px ui-monospace,monospace" onclick="this.select()">%s</textarea>
<form method="post" action="/settings/sheets" style="display:flex;flex-wrap:wrap;gap:10px"><input name="gs_url" value="%s" placeholder="https://script.google.com/macros/s/…/exec" style="flex:1 1 420px">
<button class="btn" name="do" value="save">Save link</button><button class="btn red" name="do" value="sync">Back up now</button></form>
<p class="dim" style="margin:0;font-size:12px">Last backup: %s. The code above holds a secret only your server knows; keep the Sheet private.</p></div>""" % (
        e(APPS_SCRIPT % M.setting(conn, "gs_secret")), e(url), e(M.setting(conn, "gs_last") or "never"))
