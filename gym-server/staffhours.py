"""Staff hours and the late rule, from the gate machine's punches (staff IDs 10000+).

Hours: for each part of the shift (one part, or two for a split shift such as 6-10 AM and
5-9 PM) the time from the first to the last punch in that part. So staff must also punch
when they leave; a part with only one punch counts as "no out punch" and adds no hours.

Late rule (owner can change the numbers in the app):
  arriving more than 14 minutes after a part's start is a late day;
  in each calendar month the 1st late day is a Notice, the 2nd a Warning, and the 3rd and
  every later one cuts 1 hour of pay (salary / (working days x shift hours)).
Each late day sends the person a WhatsApp message and shows on the salary sheet, where
the owner can excuse it (an excused day is never cut and does not count).
"""
import datetime
import html
import sqlite3
import time

import members as M

e = html.escape
STEPS = {"notice": "Notice", "warning": "Warning", "deduct": "Pay cut"}


def init(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS staff_late (
        id INTEGER PRIMARY KEY, pin TEXT, day TEXT, minutes INTEGER, step TEXT, hours_cut REAL DEFAULT 0,
        excused INTEGER DEFAULT 0, excused_by TEXT, created_at TEXT, UNIQUE (pin, day))""")
    have = {r[1] for r in conn.execute("PRAGMA table_info(shifts)")} if conn.execute(
        "SELECT 1 FROM sqlite_master WHERE name='shifts'").fetchone() else set()
    for col in ("start2", "end2"):
        if have and col not in have:
            conn.execute("ALTER TABLE shifts ADD COLUMN %s TEXT DEFAULT ''" % col)
    for k, v in (("late_grace", "14"), ("late_cut_hours", "1"), ("late_from", M.iso(M.today()))):
        conn.execute("INSERT OR IGNORE INTO settings VALUES (?, ?)", (k, v))


def hm(t):
    try:
        h, m = (t or "").split(":")[:2]
        return int(h) * 60 + int(m)
    except ValueError:
        return None


def clock(mins):
    if mins is None:
        return "—"
    return datetime.time(mins // 60 % 24, mins % 60).strftime("%I:%M %p").lstrip("0")


def dur(mins):
    if not mins:
        return "0h"
    return "%dh %02dm" % (mins // 60, mins % 60) if mins % 60 else "%dh" % (mins // 60)


def parts(shift):
    """[(start_min, end_min)] for the shift: one part, or two for a split shift."""
    if not shift:
        return []
    out = []
    keys = shift.keys() if hasattr(shift, "keys") else []
    for a, b in (("start", "end"), ("start2", "end2")):
        if a in keys and hm(shift[a]) is not None and hm(shift[b]) is not None:
            s_, e_ = hm(shift[a]), hm(shift[b])
            out.append((s_, e_ + 1440 if e_ <= s_ else e_))  # ends after midnight (e.g. 7:30 PM - 12:00 AM)
    return out


def shift_minutes(shift):
    return sum(max(0, b - a) for a, b in parts(shift))


def grace(conn):
    v = M.setting(conn, "late_grace", "14")
    return int(v) if str(v).isdigit() else 14


def _raw(conn, pin, d):
    return [m for (t,) in conn.execute("SELECT substr(ts,12,5) FROM punches WHERE pin=? AND substr(ts,1,10)=? ORDER BY ts",
                                       (pin, M.iso(d))) for m in [hm(t)] if m is not None]


def punches(conn, pin, d, shift=None):
    """Minutes of the day this person punched, with double taps (within 3 minutes) removed.
    For a shift that ends after midnight, punches up to 2 hours after its end on the next date
    belong to this day (counted as 24:xx), and this date's early punches belong to the day before."""
    ps = _raw(conn, pin, d)
    pr = parts(shift)
    if pr and pr[-1][1] >= 1440:
        cutoff = pr[-1][1] - 1440 + 120
        ps = [m for m in ps if m >= cutoff] + [m + 1440 for m in _raw(conn, pin, d + datetime.timedelta(days=1)) if m < cutoff]
    out = []
    for m in ps:
        if not out or m - out[-1] > 3:
            out.append(m)
    return out


def day_info(conn, pin, shift, d, grace_min=None):
    """Everything about one person's day: first/last punch, minutes worked, minutes late, status text."""
    g = grace(conn) if grace_min is None else grace_min
    ps = punches(conn, pin, d, shift)
    info = {"first": ps[0] if ps else None, "last": ps[-1] if len(ps) > 1 else None, "worked": 0, "late": 0,
            "no_out": False, "missed": [], "status": "", "workday": True}
    pr = parts(shift)
    if shift and str(d.weekday()) not in (shift["days"] or "0123456"):
        info["workday"] = False
        info["status"] = "Came on off day" if ps else "Off day"
    if not ps:
        info["status"] = info["status"] or "Not in"
        return info
    if not pr:  # no shift: first to last punch
        info["worked"] = (ps[-1] - ps[0]) if len(ps) > 1 else 0
        info["no_out"] = len(ps) < 2
        info["status"] = info["status"] or "Present"
        return info
    # put each punch in the part it belongs to (split shift: before / after the gap's middle)
    groups = [[] for _ in pr]
    for m in ps:
        i = 0
        if len(pr) == 2 and m >= (pr[0][1] + pr[1][0]) / 2:
            i = 1
        groups[i].append(m)
    late, late_start = 0, None
    for (start, end), g_ps in zip(pr, groups):
        if not g_ps:
            info["missed"].append(clock(start))
            continue
        if g_ps[0] - start > late:
            late, late_start = g_ps[0] - start, start
        if len(g_ps) > 1:
            info["worked"] += g_ps[-1] - g_ps[0]
        else:
            info["no_out"] = True
    info["late"] = late if late > g and info["workday"] else 0
    info["late_start"] = late_start
    if not info["status"]:
        info["status"] = ("Late %dm" % info["late"]) if info["late"] else "On time"
    return info


def hourly_rate(salary, shift, month_first):
    """Salary for one hour: monthly salary / (working days in the whole month x shift hours a day)."""
    nxt = (month_first + datetime.timedelta(days=32)).replace(day=1)
    days = (shift["days"] if shift else "0123456") or "0123456"
    n, d = 0, month_first
    while d < nxt:
        n += str(d.weekday()) in days
        d += datetime.timedelta(days=1)
    hours = shift_minutes(shift) / 60 or 8
    return (salary or 0) / (n * hours) if n else 0


# ---------------- the late rule ----------------

def _staff_text(conn, name, d, minutes, start, step, n, cut_hours, amount):
    """The WhatsApp text for a late day: one of the versions on the WhatsApp page."""
    import whatsapp as W
    return W.text("staff_" + step if step in ("notice", "warning", "deduct") else "staff_notice",
                  name=(name or "").split(" ")[0].title(), date=d.strftime("%d-%m-%Y"), minutes=minutes, shift=start,
                  n=n, hours="%g" % cut_hours, amount="₹%d" % round(amount))


def check_day(conn, d, notify=True):
    """Record late days for date d (once per person per day) and queue the WhatsApp. Returns how many were new."""
    if M.iso(d) < M.setting(conn, "late_from", M.iso(M.today())):
        return 0
    try:
        import whatsapp as W
    except ImportError:
        W = None
    g = grace(conn)
    cut_hours = float(M.setting(conn, "late_cut_hours", "1") or 1)
    shifts = {r["id"]: r for r in conn.execute("SELECT * FROM shifts")}
    new = 0
    for s in conn.execute("SELECT * FROM staff WHERE active=1 AND shift_id IS NOT NULL").fetchall():
        sh = shifts.get(s["shift_id"])
        if not sh or conn.execute("SELECT 1 FROM staff_late WHERE pin=? AND day=?", (s["pin"], M.iso(d))).fetchone():
            continue
        info = day_info(conn, s["pin"], sh, d, g)
        if not info["late"]:
            continue
        month = M.iso(d)[:7]
        n = conn.execute("SELECT COUNT(*) FROM staff_late WHERE pin=? AND substr(day,1,7)=? AND excused=0 AND day < ?",
                         (s["pin"], month, M.iso(d))).fetchone()[0] + 1
        step = "notice" if n == 1 else ("warning" if n == 2 else "deduct")
        hours = cut_hours if step == "deduct" else 0
        conn.execute("INSERT INTO staff_late (pin, day, minutes, step, hours_cut, created_at) VALUES (?,?,?,?,?,?)",
                     (s["pin"], M.iso(d), info["late"], step, hours, M.stamp()))
        new += 1
        if notify and W and s["phone"] and M.setting(conn, "wa_on_staff", "1") == "1":
            amount = hours * hourly_rate(s["salary"], sh, d.replace(day=1))
            start = clock(info.get("late_start"))
            W.enqueue(conn, "staff", 0, s["phone"], _staff_text(conn, s["name"], d, info["late"], start, step, n, cut_hours, amount),
                      "%s-%s" % (s["pin"], M.iso(d)))
    return new


def loop(db_path):
    """Every 5 minutes, look at today's punches for late arrivals."""
    while True:
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            conn.row_factory = sqlite3.Row
            try:
                init(conn)
                if conn.execute("SELECT 1 FROM sqlite_master WHERE name='staff'").fetchone():
                    n = check_day(conn, M.today())
                    conn.commit()
                    if n:
                        print("staff late: %d new" % n, flush=True)
            finally:
                conn.close()
        except Exception as exc:
            print("staff late loop error: %s" % exc, flush=True)
        time.sleep(300)


def month_summary(conn, pin, shift, salary, first, last):
    """Totals for the salary sheet: days present, minutes worked, late days, excused, hours and rupees cut."""
    present = worked = no_out = 0
    d = first
    while d <= last:
        info = day_info(conn, pin, shift, d)
        if info["first"] is not None:
            present += 1
            worked += info["worked"]
            no_out += info["no_out"]
        d += datetime.timedelta(days=1)
    rows = conn.execute("SELECT * FROM staff_late WHERE pin=? AND day BETWEEN ? AND ?", (pin, M.iso(first), M.iso(last))).fetchall()
    late = [r for r in rows if not r["excused"]]
    hours_cut = sum(r["hours_cut"] or 0 for r in late)
    rate = hourly_rate(salary, shift, first)
    return {"present": present, "worked": worked, "no_out": no_out, "late": len(late), "excused": len(rows) - len(late),
            "hours_cut": hours_cut, "cut": round(hours_cut * rate), "rate": rate}


def excuse(conn, f, who):
    r = conn.execute("SELECT * FROM staff_late WHERE id=?", (f.get("id", ""),)).fetchone() if (f.get("id") or "").isdigit() else None
    if not r:
        return "", "Not found."
    v = 0 if f.get("do") == "undo" else 1
    conn.execute("UPDATE staff_late SET excused=?, excused_by=? WHERE id=?", (v, who if v else "", r["id"]))
    return r["pin"], ("Late on %s excused; no pay cut." % r["day"]) if v else ("Late on %s counts again." % r["day"])


def save_rule(conn, f):
    g = (f.get("late_grace") or "").strip()
    h = (f.get("late_cut_hours") or "").strip()
    if g.isdigit() and 0 < int(g) <= 120:
        M.set_setting(conn, "late_grace", g)
    try:
        if 0 <= float(h) <= 8:
            M.set_setting(conn, "late_cut_hours", "%g" % float(h))
    except ValueError:
        pass
    return "Late rule saved: late after %s min, pay cut %s hour from the 3rd late day." % (
        M.setting(conn, "late_grace", "14"), M.setting(conn, "late_cut_hours", "1"))


def rule_panel(conn):
    return """<form class="panel" method="post" action="/staff/rule" style="display:flex;flex-direction:column;gap:12px">
<div class="ph" style="margin:0"><h2>Late rule</h2><span class="dim" style="font-size:12px">counted from %s</span></div>
<p class="dim" style="margin:0">Late = arriving more than the minutes below after the shift starts. Each month: 1st late day <b>Notice</b>,
2nd <b>Warning</b>, 3rd and every later one <b>cuts pay</b> for the hours below. Each one goes to the person on WhatsApp.</p>
<div class="grid"><label>Late after (minutes)<input name="late_grace" value="%s" inputmode="numeric"></label>
<label>Pay cut from 3rd late (hours)<input name="late_cut_hours" value="%s" inputmode="decimal"></label></div>
<button class="btn red" style="align-self:flex-start">Save rule</button></form>""" % (
        e(M.setting(conn, "late_from", "")), e(M.setting(conn, "late_grace", "14")), e(M.setting(conn, "late_cut_hours", "1")))


def report_page(conn, sn, q):
    """One person's month, day by day."""
    import ui as U
    s = conn.execute("SELECT * FROM staff WHERE pin=?", (q.get("pin", ""),)).fetchone()
    if not s:
        return U.shell("Staff report", "/staff", '<div class="panel">Staff not found. <a href="/staff">Back</a></div>')
    t = M.today()
    month = q.get("month") or t.strftime("%Y-%m")
    try:
        first = datetime.datetime.strptime(month + "-01", "%Y-%m-%d").date()
    except ValueError:
        first = t.replace(day=1)
        month = first.strftime("%Y-%m")
    nxt = (first + datetime.timedelta(days=32)).replace(day=1)
    last = min(nxt - datetime.timedelta(days=1), t)
    sh = conn.execute("SELECT * FROM shifts WHERE id=?", (s["shift_id"],)).fetchone() if s["shift_id"] else None
    lates = {r["day"]: r for r in conn.execute("SELECT * FROM staff_late WHERE pin=? AND substr(day,1,7)=?", (s["pin"], month))}
    admin = U.A.is_admin()
    rows = ""
    d = last
    while d >= first:
        info = day_info(conn, s["pin"], sh, d)
        lr = lates.get(M.iso(d))
        pill = {"On time": "p-ok", "Present": "p-ok", "Not in": "p-bad", "Off day": "p-dim"}.get(info["status"], "p-warn")
        if info["status"] == "Not in" and not info["workday"]:
            pill = "p-dim"
        late_cell = ""
        if lr:
            late_cell = '<span class="pill %s">%s%s</span>' % (
                "p-dim" if lr["excused"] else ("p-bad" if lr["step"] == "deduct" else "p-warn"),
                STEPS.get(lr["step"], lr["step"]) + (" · %gh" % lr["hours_cut"] if lr["step"] == "deduct" else ""),
                " (excused)" if lr["excused"] else "")
            if admin:
                late_cell += ('<form method="post" action="/staff/excuse" style="display:inline;margin-left:6px"><input type="hidden" name="id" value="%d">'
                              '<input type="hidden" name="month" value="%s"><button class="btn sm" name="do" value="%s">%s</button></form>' % (
                                  lr["id"], month, "undo" if lr["excused"] else "excuse", "Undo" if lr["excused"] else "Excuse"))
        rows += '<tr><td>%s</td><td><span class="pill %s">%s</span></td><td>%s</td><td>%s</td><td>%s%s</td><td>%s</td></tr>' % (
            d.strftime("%a %d %b"), pill, e(info["status"]), clock(info["first"]), clock(info["last"]),
            dur(info["worked"]) if info["worked"] else "—", ' <span class="dim" style="font-size:12px">no out punch</span>' if info["no_out"] else "",
            late_cell + ((' <span class="dim" style="font-size:12px">missed %s</span>' % ", ".join(info["missed"])) if info["missed"] and info["first"] else ""))
        d -= datetime.timedelta(days=1)
    sm = month_summary(conn, s["pin"], sh, s["salary"], first, last)
    prev = (first - datetime.timedelta(days=1)).strftime("%Y-%m")
    body = """<div class="ph"><div class="tabs"><a href="/staff/report?pin=%s&month=%s">← %s</a><a class="on" href="#">%s</a>%s</div></div>
<div class="kpis"><div class="kpi hot"><div class="l">Hours worked</div><div class="v">%s</div><div class="s">%d days present%s</div></div>
<div class="kpi"><div class="l">Shift</div><div class="v" style="font-size:20px">%s</div><div class="s">%s a day</div></div>
<div class="kpi"><div class="l">Late days</div><div class="v">%d</div><div class="s">%d excused</div></div>
<div class="kpi"><div class="l">Pay cut</div><div class="v">%s</div><div class="s">%g h × %s/h</div></div></div>
<div class="panel"><div class="tw"><table><tr><th>Date</th><th>Status</th><th>In</th><th>Out</th><th>Hours</th><th>Late rule</th></tr>%s</table></div>
<p class="dim" style="font-size:12px;margin:12px 0 0">Hours count only when the person also punches when leaving.</p></div>""" % (
        e(s["pin"]), prev, datetime.datetime.strptime(prev + "-01", "%Y-%m-%d").strftime("%b"), first.strftime("%B %Y"),
        ('<a href="/staff/report?pin=%s&month=%s">%s →</a>' % (e(s["pin"]), nxt.strftime("%Y-%m"), nxt.strftime("%b"))) if nxt <= t else "",
        dur(sm["worked"]), sm["present"], (" · %d without out punch" % sm["no_out"]) if sm["no_out"] else "",
        e(sh["name"]) if sh else "No shift", dur(shift_minutes(sh)) if sh else "—", sm["late"], sm["excused"],
        U.money(sm["cut"]) if admin else "—", sm["hours_cut"], U.money(sm["rate"]) if admin else "—", rows)
    return U.shell(s["name"] or "Staff", "/staff", body, sub='<a href="/staff">Staff</a> › %s · %s' % (e(s["name"] or ""), e(s["role"] or "")),
                   msg=q.get("m", ""), cnt=U.counts(conn, sn))
