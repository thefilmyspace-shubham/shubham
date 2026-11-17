"""Members' birthdays: who has one today, this week, this month, and whose date of birth is missing.

Dates of birth come from the joining form, the member edit page (reception can fill it) and a
one-time import from the gym's own sheet. Wishes go through the gym's WhatsApp (automatic in the
morning, or picked here and sent with Remind selected).
"""
import datetime
import html
import re

import members as M

e = html.escape


def init(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(members)")}
    if "dob" not in cols:
        conn.execute("ALTER TABLE members ADD COLUMN dob TEXT DEFAULT ''")
    # Members added from a joining form get the date of birth written on it.
    try:
        rows = conn.execute("SELECT j.client_id, j.data FROM joinings j JOIN members m ON m.client_id = j.client_id "
                            "WHERE j.status='added' AND COALESCE(m.dob,'')=''").fetchall()
    except Exception:
        rows = []
    import json
    for cid, data in rows:
        try:
            d = parse_dob(json.loads(data or "{}").get("dob", ""))
        except ValueError:
            d = None
        if d:
            conn.execute("UPDATE members SET dob=? WHERE client_id=?", (d.isoformat(), cid))


def parse_dob(v):
    """'25/8/89', '25-08-1989', '1989-08-25' -> date, or None."""
    v = str(v or "").strip()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", v)
    if m:
        y, mo, d = map(int, m.groups())
    else:
        m = re.match(r"^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})$", v)
        if not m:
            return None
        d, mo, y = map(int, m.groups())
        if y < 100:
            y += 2000 if y <= datetime.date.today().year % 100 else 1900
    try:
        out = datetime.date(y, mo, d)
    except ValueError:
        return None
    return out if 1930 <= out.year <= datetime.date.today().year - 3 else None


def next_birthday(dob, t):
    """This year's (or next year's) birthday on or after t. 29 Feb counts as 28 Feb in other years."""
    for y in (t.year, t.year + 1):
        try:
            b = dob.replace(year=y)
        except ValueError:
            b = datetime.date(y, 2, 28)
        if b >= t:
            return b
    return None


def upcoming(conn, days):
    """[(days away, birthday date, turning age, member row)] for members with a birthday in the next `days` days."""
    t = M.today()
    out = []
    for m in conn.execute("SELECT * FROM members WHERE COALESCE(dob,'') != '' AND client_id < ?", (M.STAFF_FROM,)):
        d = M.parse_date(m["dob"])
        if not d:
            continue
        b = next_birthday(d, t)
        if b and (b - t).days <= days:
            out.append(((b - t).days, b, b.year - d.year, m))
    out.sort(key=lambda x: (x[0], (x[3]["name"] or "").lower()))
    return out


def today_count(conn):
    try:
        return len(upcoming(conn, 0))
    except Exception:
        return 0


def page(conn, sn, q):
    import ui as U
    t = M.today()
    tab = q.get("t", "week")
    sets = {"today": upcoming(conn, 0), "week": upcoming(conn, 7),
            "month": [x for x in upcoming(conn, 31) if x[1].month == t.month and x[1].year == t.year]}
    missing = conn.execute("SELECT * FROM members WHERE COALESCE(dob,'')='' AND expiry >= ? AND client_id < ? ORDER BY name",
                           (M.iso(t), M.STAFF_FROM)).fetchall()
    with_dob = conn.execute("SELECT COUNT(*) FROM members WHERE COALESCE(dob,'') != ''").fetchone()[0]
    sent = U.last_reminders(conn, "birthday")
    if tab == "missing":
        trs = "".join(
            '<tr><td><a class="mem" href="/m?id=%d"><span class="av">%s</span>%s</a></td><td>%s</td><td>%s</td>'
            '<td style="text-align:right"><a class="btn sm" href="/member?id=%d#dob">Add date of birth</a></td></tr>' % (
                m["client_id"], U.initials(m["name"]), e(U.nice(m["name"])), e(m["package"] or ""), U.status_pill(m["expiry"]),
                m["client_id"]) for m in missing) or '<tr><td class="dim" colspan="4">Every active member has a date of birth.</td></tr>'
        table = '<div class="panel"><div class="tw"><table><tr><th>Member</th><th>Package</th><th>Status</th><th></th></tr>%s</table></div></div>' % trs
    else:
        rows = sets.get(tab, sets["week"])
        trs = "".join(
            '<tr><td>%s</td><td><a class="mem" href="/m?id=%d"><span class="av">%s</span>%s</a></td><td><b>%s</b></td><td>%s</td>'
            '<td>%s</td><td>%s</td><td class="dim">%s</td><td style="text-align:right">%s</td></tr>' % (
                U.sel_box(m["client_id"]), m["client_id"], U.initials(m["name"]), e(U.nice(m["name"])), b.strftime("%d %b"),
                '<span class="pill p-bad">Today 🎂</span>' if days == 0 else ('<span class="pill p-warn">Tomorrow</span>' if days == 1
                                                                            else '<span class="pill p-dim">in %d days</span>' % days),
                "Turns %d" % age, U.status_pill(m["expiry"]),
                ("Wished %s" % M.parse_date(sent[m["client_id"]][:10]).strftime("%d %b")) if m["client_id"] in sent
                and sent[m["client_id"]][:4] == str(t.year) else "Not wished",
                U.remind_btn(m, "birthday")) for days, b, age, m in rows) or (
            '<tr><td colspan="8" class="dim">No birthdays in this list.%s</td></tr>' % (
                " Add dates of birth in the <a href=\"/birthdays?t=missing\">Missing</a> tab." if not with_dob else ""))
        table = """<form class="panel" method="get" action="/remind"><input type="hidden" name="k" value="birthday"><div class="ph">
<h2>%s</h2><div class="acts"><button class="btn red sm">Remind selected on WhatsApp</button></div></div>
<div class="tw"><table><tr><th><input type="checkbox" aria-label="Select all" title="Select all" style="width:18px;height:18px;min-height:0;accent-color:#e10600" onclick="var on=this.checked;this.form.querySelectorAll('input[name=id]').forEach(function(c){c.checked=on})"></th>
<th>Member</th><th>Birthday</th><th>When</th><th>Age</th><th>Membership</th><th>Wish</th><th></th></tr>%s</table></div></form>""" % (
            {"today": "Today", "week": "Next 7 days", "month": t.strftime("%B")}.get(tab, "Next 7 days"), trs)
    tabs = "".join('<a href="/birthdays?t=%s"%s>%s %d</a>' % (k, ' class="on"' if k == tab else "", l, n) for k, l, n in (
        ("today", "Today", len(sets["today"])), ("week", "This week", len(sets["week"])), ("month", "This month", len(sets["month"])),
        ("missing", "Date of birth missing", len(missing))))
    body = """<div class="kpis"><a class="kpi hot" href="/birthdays?t=today"><div class="l">Today</div><div class="v">%d</div><div class="s">birthdays 🎂</div></a>
<a class="kpi" href="/birthdays?t=week"><div class="l">Next 7 days</div><div class="v">%d</div><div class="s">coming up</div></a>
<a class="kpi" href="/birthdays?t=month"><div class="l">%s</div><div class="v">%d</div><div class="s">this month</div></a>
<a class="kpi" href="/birthdays?t=missing"><div class="l">No date of birth</div><div class="v">%d</div><div class="s">active members · %d have one</div></a></div>
<div class="tabs">%s</div>%s
<p class="dim" style="font-size:12px;margin:0">When WhatsApp sending is on, wishes also go by themselves in the morning. Dates of birth come from the
joining form, or add them on a member's Edit page.</p>""" % (
        len(sets["today"]), len(sets["week"]), t.strftime("%B"), len(sets["month"]), len(missing), with_dob, tabs, table)
    return U.shell("Birthdays", "/birthdays", body, sub="Whose birthday is when, and one-tap wishes", msg=q.get("m", ""),
                   cnt=U.counts(conn, sn))
