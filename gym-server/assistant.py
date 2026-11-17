"""Owner's AI assistant: ask about the gym in plain Hinglish.

Questions are answered straight away from the database through read-only tools.
Changes (block, unblock, extend membership) are only *proposed* by the model; the
page shows a Confirm button and nothing changes until the owner presses it.
Member phone numbers are never sent to the API.

Manual tool loop on the Messages API (stable, no beta). The conversation is kept in
memory per signed-in person and only ever appended to; "New chat" starts over.
"""
import datetime
import json
import os
import secrets
import sqlite3
import threading

import ai as AI
import members as M
import ui as U

MODEL = os.environ.get("HOS_ASSISTANT_MODEL", "claude-haiku-5-5")
MAX_STEPS = 8
CHATS = {}       # email -> list of messages
PENDING = {}     # action id -> {email, kind, client_id, days, label}
LOCK = threading.Lock()

SYSTEM = """You are the House of Strength gym's assistant for the owner. Answer in short, clear Hinglish (Roman script), like a sharp manager.
Use the tools for every number; never guess. Today is {today}. Money is in rupees; write amounts like Rs 1,23,800.
For lists, give at most 15 lines (name, member ID, the key number) and say how many more there are.
To block, unblock or extend a membership, call the matching propose_* tool: it does NOT change anything, the owner must press Confirm on the screen. Say that.
If someone asks for an Excel / sheet, call excel_link. You cannot send WhatsApp messages or change bills; say how to do it in the app instead.
Do not use markdown tables or headings; plain lines and simple '-' bullets only."""


def _conn(db_path):
    c = sqlite3.connect(db_path, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def _range(a, b):
    t = M.today()
    a = M.parse_date(a) or t.replace(day=1)
    b = M.parse_date(b) or t
    return M.iso(a), M.iso(b)


def _member_row(m, last=None):
    return {"id": U.member_id(m["client_id"]), "name": U.nice(m["name"]), "package": m["package"],
            "expiry": M.show(m["expiry"]), "pending": m["pending"] or 0,
            "last_visit": M.show(M.iso(last)) if last else "none since tracking began"}


TOOLS = [
    {"name": "collection_summary", "description": "Money collected between two dates: total, number of bills, by payment mode, best days.",
     "input_schema": {"type": "object", "properties": {"from_date": {"type": "string", "description": "YYYY-MM-DD"},
                                                       "to_date": {"type": "string", "description": "YYYY-MM-DD"}},
                      "required": ["from_date", "to_date"]}},
    {"name": "profit_summary", "description": "Collection, expenses by category (incl. salaries) and profit between two dates.",
     "input_schema": {"type": "object", "properties": {"from_date": {"type": "string"}, "to_date": {"type": "string"}},
                      "required": ["from_date", "to_date"]}},
    {"name": "member_counts", "description": "Totals: members, active, expired, expiring in 7 days, pending dues, absent 7+ days.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "list_members", "description": "List members by status. kind: active, expired, expiring (within days), pending_dues, absent (not seen for days), expired_recently (within days).",
     "input_schema": {"type": "object", "properties": {"kind": {"type": "string", "enum": ["active", "expired", "expiring", "pending_dues", "absent", "expired_recently"]},
                                                       "days": {"type": "integer", "description": "Window in days where it applies; default 7"}},
                      "required": ["kind"]}},
    {"name": "find_member", "description": "Look up members by name or member ID (e.g. 676 or HOS-0676): package, expiry, dues, last visit, last bills.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "attendance_summary", "description": "Member check-ins between two dates: total visits, unique members, busiest hours.",
     "input_schema": {"type": "object", "properties": {"from_date": {"type": "string"}, "to_date": {"type": "string"}},
                      "required": ["from_date", "to_date"]}},
    {"name": "package_sales", "description": "Which packages sold between two dates, with counts and amounts, and average discount.",
     "input_schema": {"type": "object", "properties": {"from_date": {"type": "string"}, "to_date": {"type": "string"}},
                      "required": ["from_date", "to_date"]}},
    {"name": "staff_today", "description": "Staff and trainers today: who came in, at what time, on time or late versus their shift.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "excel_link", "description": "Download link for an Excel (CSV) report.",
     "input_schema": {"type": "object", "properties": {"report": {"type": "string", "enum": ["pending_dues", "renewals_this_month", "members", "attendance", "bills", "collection", "expenses"]},
                                                       "from_date": {"type": "string"}, "to_date": {"type": "string"}},
                      "required": ["report"]}},
    {"name": "propose_block", "description": "Propose blocking a member at the gate door (owner must confirm on screen).",
     "input_schema": {"type": "object", "properties": {"member": {"type": "string"}, "reason": {"type": "string"}}, "required": ["member"]}},
    {"name": "propose_unblock", "description": "Propose unblocking a member at the gate door (owner must confirm on screen).",
     "input_schema": {"type": "object", "properties": {"member": {"type": "string"}}, "required": ["member"]}},
    {"name": "propose_extend", "description": "Propose extending a member's expiry by some days, e.g. freeze for travel (owner must confirm).",
     "input_schema": {"type": "object", "properties": {"member": {"type": "string"}, "days": {"type": "integer"}}, "required": ["member", "days"]}},
]


def run_tool(conn, sn, email, name, inp, actions):
    t = M.today()
    if name == "collection_summary":
        a, b = _range(inp.get("from_date"), inp.get("to_date"))
        tot = conn.execute("SELECT COALESCE(SUM(amount),0), COUNT(*) FROM payments WHERE paid_on BETWEEN ? AND ?", (a, b)).fetchone()
        modes = conn.execute("SELECT COALESCE(NULLIF(mode,''),'not recorded'), SUM(amount), COUNT(*) FROM payments WHERE paid_on BETWEEN ? AND ? GROUP BY 1", (a, b)).fetchall()
        days = conn.execute("SELECT paid_on, SUM(amount) s FROM payments WHERE paid_on BETWEEN ? AND ? GROUP BY paid_on ORDER BY s DESC LIMIT 5", (a, b)).fetchall()
        return {"from": a, "to": b, "total": tot[0], "bills": tot[1], "by_mode": {m: {"amount": s, "bills": n} for m, s, n in modes},
                "best_days": [{"date": d, "amount": s} for d, s in days]}
    if name == "profit_summary":
        a, b = _range(inp.get("from_date"), inp.get("to_date"))
        U.init_expenses(conn)
        col = conn.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE paid_on BETWEEN ? AND ?", (a, b)).fetchone()[0]
        cats = dict(conn.execute("SELECT category, SUM(amount) FROM expenses WHERE spent_on BETWEEN ? AND ? GROUP BY 1", (a, b)).fetchall())
        exp = sum(cats.values())
        return {"from": a, "to": b, "collection": col, "expenses_by_category": cats, "expenses_total": exp, "profit": col - exp,
                "note": "Expenses are only what was entered on the Expenses page."}
    if name == "member_counts":
        ti = M.iso(t)
        q = lambda sql, *a: conn.execute(sql, a).fetchone()[0]
        return {"members": q("SELECT COUNT(*) FROM members"), "active": q("SELECT COUNT(*) FROM members WHERE expiry >= ?", ti),
                "expired": q("SELECT COUNT(*) FROM members WHERE expiry < ? OR expiry IS NULL OR expiry=''", ti),
                "expiring_7_days": q("SELECT COUNT(*) FROM members WHERE expiry BETWEEN ? AND ?", ti, M.iso(t + datetime.timedelta(days=7))),
                "with_pending_dues": q("SELECT COUNT(*) FROM members WHERE pending > 0"),
                "pending_total": q("SELECT COALESCE(SUM(pending),0) FROM members"),
                "absent_7_plus_days": len(U.absent_list(conn, sn, 7)) if sn else 0}
    if name == "list_members":
        kind, days = inp.get("kind"), int(inp.get("days") or 7)
        ti = M.iso(t)
        if kind == "absent":
            rows = [(m, last, d) for d, last, m in U.absent_list(conn, sn, days)]
            out = [dict(_member_row(m, last), days_absent=d) for m, last, d in rows]
        else:
            sql = {"active": ("SELECT * FROM members WHERE expiry >= ? ORDER BY expiry", (ti,)),
                   "expired": ("SELECT * FROM members WHERE expiry < ? ORDER BY expiry DESC", (ti,)),
                   "expiring": ("SELECT * FROM members WHERE expiry BETWEEN ? AND ? ORDER BY expiry", (ti, M.iso(t + datetime.timedelta(days=days)))),
                   "expired_recently": ("SELECT * FROM members WHERE expiry BETWEEN ? AND ? ORDER BY expiry DESC",
                                        (M.iso(t - datetime.timedelta(days=days)), M.iso(t - datetime.timedelta(days=1)))),
                   "pending_dues": ("SELECT * FROM members WHERE pending > 0 ORDER BY pending DESC", ())}[kind]
            rows = conn.execute(*sql).fetchall()
            out = [{"id": U.member_id(m["client_id"]), "name": U.nice(m["name"]), "package": m["package"],
                    "expiry": M.show(m["expiry"]), "pending": m["pending"] or 0} for m in rows]
        return {"kind": kind, "days": days, "count": len(out), "members": out[:40], "more": max(0, len(out) - 40)}
    if name == "find_member":
        qtxt = (inp.get("query") or "").strip()
        m1 = U.resolve_member(conn, qtxt)
        rows = [m1] if m1 else [r for r in conn.execute("SELECT * FROM members").fetchall()
                                if all(w in (r["name"] or "").lower() for w in qtxt.lower().split())][:8]
        res = []
        for m in rows:
            last = conn.execute("SELECT MAX(ts) FROM punches WHERE pin=?", (str(m["client_id"]),)).fetchone()[0]
            bills = conn.execute("SELECT paid_on, package, amount, balance FROM payments WHERE client_id=? ORDER BY paid_on DESC LIMIT 3",
                                 (m["client_id"],)).fetchall()
            res.append({"id": U.member_id(m["client_id"]), "name": U.nice(m["name"]), "package": m["package"], "expiry": M.show(m["expiry"]),
                        "status": "active" if (M.parse_date(m["expiry"]) or datetime.date.min) >= t else "expired",
                        "pending": m["pending"] or 0, "last_visit": last[:16] if last else "none",
                        "door_blocked": str(m["client_id"]) in M.blocked_pins(conn, sn) if sn else False,
                        "last_bills": [{"date": M.show(b[0]), "package": b[1], "paid": b[2], "balance": b[3]} for b in bills]})
        return {"matches": res} if res else {"matches": [], "note": "No member found."}
    if name == "attendance_summary":
        a, b = _range(inp.get("from_date"), inp.get("to_date"))
        base = "FROM punches WHERE substr(ts,1,10) BETWEEN ? AND ? AND CAST(pin AS INT) < 10000 AND status != '1'"
        visits = conn.execute("SELECT COUNT(DISTINCT pin || substr(ts,1,10)) " + base, (a, b)).fetchone()[0]
        uniq = conn.execute("SELECT COUNT(DISTINCT pin) " + base, (a, b)).fetchone()[0]
        hours = conn.execute("SELECT substr(ts,12,2) h, COUNT(*) n " + base + " GROUP BY h ORDER BY n DESC LIMIT 4", (a, b)).fetchall()
        return {"from": a, "to": b, "visits": visits, "unique_members": uniq, "busiest_hours": [{"hour": h + ":00", "check_ins": n} for h, n in hours]}
    if name == "package_sales":
        a, b = _range(inp.get("from_date"), inp.get("to_date"))
        rows = conn.execute("SELECT package, COUNT(*), SUM(amount), SUM(list_price), SUM(payable) FROM payments WHERE paid_on BETWEEN ? AND ? "
                            "AND kind != 'due' GROUP BY lower(package) ORDER BY 2 DESC", (a, b)).fetchall()
        lp, pb = sum(r[3] or 0 for r in rows), sum(r[4] or 0 for r in rows)
        return {"from": a, "to": b, "packages": [{"package": r[0], "bills": r[1], "paid": r[2]} for r in rows],
                "average_discount_percent": round(100 * (1 - pb / lp)) if lp else 0}
    if name == "staff_today":
        U.init_staff(conn)
        shifts = {r["id"]: r for r in conn.execute("SELECT * FROM shifts")}
        out = []
        for s in conn.execute("SELECT * FROM staff WHERE active=1"):
            st, first, last, early = U.day_status(conn, s["pin"], shifts.get(s["shift_id"]), t)
            out.append({"name": s["name"], "role": s["role"], "status": st, "in": first, "out": last, "left_early": early})
        return {"date": M.iso(t), "staff": out}
    if name == "excel_link":
        a, b = _range(inp.get("from_date"), inp.get("to_date"))
        link = {"pending_dues": "/pending.csv", "renewals_this_month": "/renewals.csv?t=month", "members": "/members.csv",
                "attendance": "/attendance.csv", "bills": "/reports/bills.csv?from=%s&to=%s" % (a, b),
                "collection": "/reports/collection.csv?from=%s&to=%s" % (a, b), "expenses": "/reports/expenses.csv?from=%s&to=%s" % (a, b)}[inp["report"]]
        actions.append({"type": "link", "label": "Download %s (Excel)" % inp["report"].replace("_", " "), "href": link})
        return {"ok": True, "note": "A download button is shown to the owner."}
    if name in ("propose_block", "propose_unblock", "propose_extend"):
        m = U.resolve_member(conn, inp.get("member"))
        if not m:
            cands = [r for r in conn.execute("SELECT * FROM members").fetchall()
                     if all(w in (r["name"] or "").lower() for w in (inp.get("member") or "").lower().split())][:6]
            if len(cands) != 1:
                return {"error": "Member not clear", "candidates": [{"id": U.member_id(r["client_id"]), "name": U.nice(r["name"])} for r in cands]}
            m = cands[0]
        kind = name.split("_")[1]
        days = int(inp.get("days") or 0)
        if kind == "extend" and not 0 < days <= 365:
            return {"error": "Days must be between 1 and 365."}
        label = {"block": "Block %s (%s) at the door", "unblock": "Unblock %s (%s) at the door",
                 "extend": "Extend %s (%s) by " + str(days) + " days"}[kind] % (U.nice(m["name"]), U.member_id(m["client_id"]))
        aid = secrets.token_urlsafe(8)
        with LOCK:
            PENDING[aid] = {"email": email, "kind": kind, "client_id": m["client_id"], "days": days, "label": label}
        actions.append({"type": "confirm", "id": aid, "label": label})
        return {"proposed": label, "status": "waiting for the owner to press Confirm on screen"}
    return {"error": "unknown tool"}


def ask(db_path, sn, user, text):
    """Returns {"reply": str, "actions": [...]} or {"error": str}."""
    if not AI.available():
        return {"error": "AI is not set up on the server yet."}
    email = user.get("email", "owner")
    with LOCK:
        msgs = CHATS.setdefault(email, [])
        if len(msgs) > 40:  # long chats get expensive; start over
            msgs.clear()
        msgs.append({"role": "user", "content": text.strip()[:1000]})
    actions = []
    client = AI._client()
    try:
        for _ in range(MAX_STEPS):
            resp = client.messages.create(model=MODEL, max_tokens=8000, output_config={"effort": "medium"},
                                          system=SYSTEM.format(today=M.today().strftime("%A %d %B %Y")),
                                          tools=TOOLS, messages=msgs)
            msgs.append({"role": "assistant", "content": resp.content})
            if resp.stop_reason == "refusal":
                return {"error": "The assistant declined that one.", "actions": actions}
            if resp.stop_reason != "tool_use":
                text_out = "\n".join(b.text for b in resp.content if b.type == "text").strip()
                return {"reply": text_out or "(no answer)", "actions": actions}
            results = []
            conn = _conn(db_path)
            try:
                for b in resp.content:
                    if b.type == "tool_use":
                        try:
                            out = run_tool(conn, sn, email, b.name, b.input or {}, actions)
                            results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(out, default=str)})
                        except Exception as exc:  # report to the model, keep going
                            results.append({"type": "tool_result", "tool_use_id": b.id, "is_error": True, "content": "Error: %s" % exc})
            finally:
                conn.close()
            msgs.append({"role": "user", "content": results})
        return {"reply": "That needed too many steps. Ask a simpler question.", "actions": actions}
    except AI.anthropic.RateLimitError:
        err = "AI is busy right now. Try again in a minute."
    except AI.anthropic.APIStatusError as exc:
        print("assistant api error %s: %s" % (exc.status_code, exc.message), flush=True)
        err = "AI is not answering right now. Try again."
    except AI.anthropic.APIConnectionError:
        err = "Server could not reach the AI. Try again."
    with LOCK:  # a half-finished turn would leave the history invalid: start the chat over
        CHATS.pop(email, None)
    return {"error": err + " (chat restarted)", "actions": actions}


def reset(user):
    with LOCK:
        CHATS.pop(user.get("email", "owner"), None)


def confirm(conn, sn, user, aid):
    with LOCK:
        act = PENDING.pop(aid, None)
    if not act or act["email"] != user.get("email", "owner"):
        return "This action has expired. Ask again."
    cid = act["client_id"]
    if act["kind"] == "block":
        ok, msg = M.block(conn, sn, cid, "manual")
    elif act["kind"] == "unblock":
        ok, msg = M.unblock(conn, sn, cid)
    else:
        m = conn.execute("SELECT * FROM members WHERE client_id=?", (cid,)).fetchone()
        new = (M.parse_date(m["expiry"]) or M.today()) + datetime.timedelta(days=act["days"])
        conn.execute("UPDATE members SET expiry=?, updated_at=? WHERE client_id=?", (M.iso(new), M.stamp(), cid))
        if sn and new >= M.today() and str(cid) in M.blocked_pins(conn, sn):
            M.unblock(conn, sn, cid)
        msg = "Expiry moved to %s." % new.strftime("%d %b %Y")
    return "%s — %s" % (act["label"], msg)


def page(conn, sn, q):
    ok = AI.available()
    body = """<div class="panel" style="display:flex;flex-direction:column;gap:14px;min-height:60vh">
<div class="ph" style="margin:0"><h2>Ask anything about the gym</h2><button class="btn sm" type="button" onclick="newChat()">New chat</button></div>
<div id="chat" style="display:flex;flex-direction:column;gap:10px;flex:1"></div>
<div class="tabs" id="sugg">%s</div>
<form id="af" style="display:flex;gap:10px;flex-wrap:wrap" onsubmit="send(event)"><input id="aq" placeholder="e.g. Is mahine ka collection kitna hua?" style="flex:1 1 360px" %s autocomplete="off">
<button class="btn red" id="ab" %s>Ask</button></form>
<p class="dim" style="margin:0;font-size:12px">Answers come from your app's data. Block, unblock or extend happens only after you press Confirm. Phone numbers are never sent to the AI. Every action is logged.</p></div>
<script>
var chat=document.getElementById('chat');
function esc(s){return s.replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function bubble(t,me){var d=document.createElement('div');d.style.cssText='max-width:820px;padding:12px 14px;border-radius:12px;white-space:pre-wrap;line-height:1.5;'+(me?'align-self:flex-end;background:#e10600;color:#fff':'background:var(--card2);border:1px solid var(--line)');
d.innerHTML=esc(t).replace(/\\*\\*(.+?)\\*\\*/g,'<b>$1</b>');chat.appendChild(d);d.scrollIntoView({block:'end'});return d}
function acts(a){(a||[]).forEach(function(x){var w=document.createElement('div');w.style.cssText='display:flex;gap:8px;align-items:center';
if(x.type==='link'){w.innerHTML='<a class="btn sm" href="'+x.href+'">'+esc(x.label)+'</a>'}
else{w.innerHTML='<span class="pill p-warn">'+esc(x.label)+'</span><button class="btn red sm">Confirm</button>';
w.querySelector('button').onclick=function(){var b=this;b.disabled=true;fetch('/assistant/confirm',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'id='+encodeURIComponent(x.id)})
.then(function(r){return r.json()}).then(function(d){b.outerHTML='<span class="pill p-ok">'+esc(d.result||d.error)+'</span>'})}}chat.appendChild(w)})}
function send(ev){if(ev){ev.preventDefault()}var q=document.getElementById('aq'),t=q.value.trim();if(!t){return}bubble(t,true);q.value='';
var b=document.getElementById('ab');b.disabled=true;var w=bubble('Thinking…',false);
fetch('/assistant/ask',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'q='+encodeURIComponent(t)})
.then(function(r){return r.json()}).then(function(d){w.remove();bubble(d.reply||d.error,false);acts(d.actions);b.disabled=false})
.catch(function(){w.textContent='Could not reach the server.';b.disabled=false})}
function ask(t){document.getElementById('aq').value=t;send()}
function newChat(){fetch('/assistant/reset',{method:'POST'});chat.innerHTML=''}
</script>""" % (
        "".join('<a href="#" onclick="ask(this.textContent);return false">%s</a>' % s for s in (
            "Is mahine ka collection kitna hua?", "Kaun 10 din se nahi aaya?", "Pending dues kitne hain?",
            "Is hafte kiska renewal hai?", "Is mahine ka profit kitna hai?", "Aaj staff me kaun late aaya?")) if ok else "",
        "" if ok else "disabled", "" if ok else "disabled")
    return U.shell("AI assistant", "/assistant", body, sub="Owner only · reports run straight away, changes need your Confirm",
                   warn="" if ok else "AI is not set up on the server yet.", cnt=U.counts(conn, sn))
