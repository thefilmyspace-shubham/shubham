"""Joining form (the gym's "Member Consent Form"): an online page anyone can open (/join)
and an editable PDF (/join.pdf), both in the same format as the gym's paper form.

A filled form lands in the `joinings` table as "new"; the front desk checks it, enrolls the
finger on the gate machine and taps "Add as member", which opens the usual member form
prefilled. A filled PDF is read on this server (no AI). A photo or scan of a paper form is
read by Claude, because there are no form fields to read.
"""
import base64
import datetime
import html
import io
import json
import re
import threading
import time

import members as M

e = html.escape

# key, label, type, required online. type: text | tel | email | [choices] | refs
INFO = [
    ("name", "Full Name", "text", True), ("guardian", "Parent/Guardian Name", "text", False),
    ("dob", "Date of Birth (DD-MM-YYYY)", "text", False), ("age", "Age", "num", False),
    ("gender", "Gender", ["Male", "Female", "Other"], True), ("address", "Address", "text", False),
    ("phone", "Phone Number", "tel", True), ("email", "Email", "email", False),
    ("emergency", "Emergency Contact Name & Number", "text", True),
    ("medical", "Medical Conditions or Injuries (if any)", "text", False),
]
REFS = [("ref_social", "Social media"), ("ref_friend", "Friend"), ("ref_other", "Other")]
MINOR = [("minor_guardian", "Parent/Guardian Name"), ("minor_relation", "Relationship to Member"),
         ("minor_signature", "Signature of Guardian (type full name)"), ("minor_date", "Date")]
FINAL_TEXT = ("I have read and understood the terms in this form. I agree to abide by the rules of HOS Gym and accept all "
              "responsibilities as outlined above.")
BIOMETRIC_TEXT = ("I allow my fingerprint to be saved on the gym's door machine only to let me in. It is removed when I ask.")

INTRO = ("Please fill in the following details accurately. This information helps us tailor your fitness experience and "
         "ensures safety during training sessions.")
POLICIES = [
    ("General Consent & Gym Policies", "By becoming a member of HOS Gym, you agree to the following terms and conditions designed "
     "to ensure a safe, respectful, and effective training environment for all."),
    ("Voluntary Participation", "You acknowledge that your participation in gym activities is voluntary and that you understand "
     "the risks involved in physical exercise."),
    ("Medical Declaration", "You confirm that you are medically fit to exercise or have consulted a physician before starting "
     "your fitness program."),
    ("Assumption of Risk", "You accept responsibility for your own safety and release HOS Gym from liability for injuries or "
     "health issues resulting from your activities."),
    ("Personal Belongings", "You understand that the gym is not liable for lost, stolen, or damaged personal items."),
    ("Code of Conduct", "You agree to follow all gym rules, respect staff and members, and use equipment responsibly."),
    ("Trainer & Nutrition Guidance", "You understand that all fitness and diet plans are for general guidance and do not replace "
     "professional medical advice."),
    ("Media Release & Administrative Policies", "You may optionally allow us to use your photo or video for promotional content. "
     "Membership terms and refund policies are outlined below."),
]
REFUND = ["Memberships are non-refundable and non-transferable.", "Freeze allowed only for medical emergencies with valid documentation.",
          "Missed sessions will not be extended unless pre-approved.", "Discounts are valid only during official promotional periods."]

ALL_KEYS = ([k for k, _, _, _ in INFO] + [k for k, _ in REFS] + ["photo"] + [k for k, _ in MINOR]
            + ["agree", "agree_biometric", "signature", "form_date", "auth_by", "auth_date"])
BOOL_KEYS = {k for k, _ in REFS} | {"agree", "agree_biometric"}
LABELS = dict([(k, l) for k, l, _, _ in INFO] + REFS + MINOR + [
    ("photo", "Photo/Video Consent"), ("agree", "Final declaration"), ("agree_biometric", "Fingerprint consent"),
    ("signature", "Member Signature"), ("form_date", "Date"), ("auth_by", "Authorized by (HOS Gym)"), ("auth_date", "Date")])
NO_ISSUE = re.compile(r"^\s*(no|none|nil|na|n/a|nahi|nahin|nothing|-+|\.|no\.?)\s*$", re.I)

SOURCES = {"online": "Online link", "pdf": "Filled PDF", "photo": "Photo / scan", "desk": "Entered at desk"}

_RATE = {}
_RATE_LOCK = threading.Lock()


def init(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS joinings (
        id INTEGER PRIMARY KEY, created_at TEXT, source TEXT, status TEXT DEFAULT 'new', data TEXT,
        client_id INTEGER, ip TEXT, handled_by TEXT, handled_at TEXT)""")


def _truthy(v):
    return str(v or "").strip().lower() in ("1", "yes", "on", "true", "/yes", "/on", "y", "x", "✓")


def clean(raw):
    """Keep only known fields, trimmed and capped; tick boxes become '1' or ''."""
    out = {}
    for k in ALL_KEYS:
        v = raw.get(k)
        out[k] = ("1" if _truthy(v) else "") if k in BOOL_KEYS else re.sub(r"\s+", " ", str(v or "")).strip()[:200]
    # The PDF has two boxes for photo consent.
    if not out["photo"]:
        out["photo"] = "Yes" if _truthy(raw.get("photo_yes")) else ("No" if _truthy(raw.get("photo_no")) else "")
    p = out["photo"].lower()
    out["photo"] = "Yes" if p in ("yes", "y", "1", "true", "haan") else ("No" if p in ("no", "n", "0", "false", "nahi") else "")
    d = re.sub(r"\D", "", out["phone"])
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    out["phone"] = d[-10:] if len(d) >= 10 else d
    g = out["gender"].lower()
    out["gender"] = "Male" if g.startswith("m") else "Female" if g.startswith("f") else ("Other" if g else "")
    out["age"] = re.sub(r"\D", "", out["age"])[:3]
    if not out["age"]:
        b = M.parse_date(out["dob"].replace("/", "-").replace(".", "-"))
        if b:
            t = M.today()
            out["age"] = str(t.year - b.year - ((t.month, t.day) < (b.month, b.day)))
    return out


def is_minor(d):
    return d.get("age", "").isdigit() and int(d["age"]) < 18


def missing(d):
    need = [k for k, _, _, req in INFO if req] + ["signature"]
    out = [LABELS[k] for k in need if not d.get(k)]
    if is_minor(d):
        out += ["Minor's consent: " + LABELS[k] for k in ("minor_guardian", "minor_signature") if not d.get(k)]
    return out


def save(conn, data, source, ip=""):
    conn.execute("INSERT INTO joinings (created_at, source, data, ip) VALUES (?,?,?,?)",
                 (M.stamp(), source, json.dumps(data), ip))
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def rate_ok(ip):
    """At most 5 online forms an hour from one address."""
    now = time.time()
    with _RATE_LOCK:
        hits = [t for t in _RATE.get(ip, []) if now - t < 3600]
        if len(hits) >= 5:
            _RATE[ip] = hits
            return False
        _RATE[ip] = hits + [now]
        return True


def health_flags(d):
    m = (d.get("medical") or "").strip()
    return [m] if m and not NO_ISSUE.match(m) else []


def reference(d):
    return ", ".join(l for k, l in REFS if d.get(k)) or "—"


# ---------------- reading filled forms ----------------

def read_pdf(raw):
    """Field values from a filled PDF. Returns (dict, error); error 'empty' when nothing was typed."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return None, "PDF reader is not installed on the server (pip install pypdf)."
    try:
        fields = PdfReader(io.BytesIO(raw)).get_fields() or {}
    except Exception:
        return None, "This PDF could not be opened."
    vals = {}
    for k, f in fields.items():
        v = f.get("/V")
        if v is None:
            continue
        v = str(v)
        vals[k] = "1" if v in ("/Yes", "/On", "/1") else ("" if v == "/Off" else v)
    if not any(vals.get(k) for k in ("name", "phone")):
        return None, "empty"
    return vals, ""


def read_with_ai(raw, media_type):
    import ai as AI
    keys = [k for k in ALL_KEYS]
    props = {k: ({"type": "boolean"} if k in BOOL_KEYS else {"type": "string"}) for k in keys}
    props["photo"] = {"type": "string", "enum": ["Yes", "No", ""]}
    schema = {"type": "object", "properties": props, "required": keys, "additionalProperties": False}
    key_help = "\n".join("- %s: %s" % (k, LABELS.get(k, k)) for k in keys)
    system = ("You copy a filled gym form (House of Strength Gym, Ratlam: 'Member Consent Form') into fields. It is usually "
              "handwritten. Copy exactly what is written; never guess. Leave a field empty (or false for tick boxes) if it is blank "
              "or unreadable. ref_social / ref_friend / ref_other are the Reference tick boxes; photo is the Photo/Video Consent tick "
              "(Yes or No). minor_* are the Minor's Consent lines. signature is true-ish: write the member's name if a signature is "
              "present, else empty. agree is true when the member signed the final declaration. agree_biometric stays false unless "
              "a fingerprint consent box is ticked. auth_by is who signed for the gym. Dates as DD-MM-YYYY.\nFields:\n" + key_help)
    b64 = base64.b64encode(raw).decode()
    if media_type == "application/pdf":
        block = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}}
    else:
        block = {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}}
    data, err = AI._ask(system, [block, {"type": "text", "text": "Copy this form."}], schema)
    if err:
        return None, err
    return {k: ("1" if v is True else "" if v is False else v) for k, v in data.items()}, ""


def read_upload(b64, filename):
    """A filled PDF or a photo -> (cleaned dict, source, error)."""
    b64 = re.sub(r"[^A-Za-z0-9+/=]", "", b64 or "")
    if not b64:
        return None, "", "Choose the filled form (PDF or photo)."
    if len(b64) > 11000000:
        return None, "", "File is too large (max 8 MB)."
    raw = base64.b64decode(b64)
    if raw[:5] == b"%PDF-":
        vals, err = read_pdf(raw)
        if vals:
            return clean(vals), "pdf", ""
        if err != "empty":
            return None, "", err
        vals, err = read_with_ai(raw, "application/pdf")  # printed, filled by hand, then scanned
        return (clean(vals), "photo", "") if vals else (None, "", err)
    media = "image/png" if raw[:4] == b"\x89PNG" else "image/jpeg"
    vals, err = read_with_ai(raw, media)
    return (clean(vals), "photo", "") if vals else (None, "", err)


# ---------------- public page ----------------

PUBLIC_CSS = """:root{color-scheme:dark;--bg:#0b0b0c;--card:#151517;--line:#2a2a2e;--text:#f4f4f5;--dim:#a1a1aa;--red:#e10600}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.5 Inter,system-ui,sans-serif}
.wrap{max-width:640px;margin:0 auto;padding:20px 16px 40px}.head{display:flex;gap:14px;align-items:center;margin-bottom:6px}
.head img{width:64px;height:64px;border-radius:12px}.head h1{font:700 24px Oswald,sans-serif;margin:0;letter-spacing:.5px}
.head p{margin:2px 0 0;color:var(--dim);font-size:13px}.badge{display:inline-block;background:#2a2a2e;border-radius:8px;
padding:4px 12px;font:600 15px Oswald,sans-serif;letter-spacing:1px;margin:10px 0 14px}
fieldset{border:1px solid var(--line);border-radius:14px;background:var(--card);padding:16px;margin:0 0 16px}
legend{font:600 15px Oswald,sans-serif;letter-spacing:.5px;padding:0 6px;color:#fff}
label{display:flex;flex-direction:column;gap:6px;font-size:14px;color:var(--dim);margin-bottom:12px}
input,select{font:16px Inter,sans-serif;color:var(--text);background:#0f0f11;border:1px solid var(--line);border-radius:10px;
min-height:46px;padding:0 12px;width:100%}input:focus,select:focus{outline:2px solid var(--red);border-color:transparent}
.chk{flex-direction:row;align-items:flex-start;gap:10px;color:var(--text);margin-bottom:10px}.chk input{width:22px;min-height:22px;
height:22px;margin:1px 0 0;accent-color:var(--red);flex:none}.row{display:flex;flex-wrap:wrap;gap:4px 18px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:0 10px}.q{color:var(--dim);font-size:14px;margin:0 0 8px}
.terms{font-size:13.5px;color:#d4d4d8;max-height:280px;overflow:auto;border:1px solid var(--line);border-radius:10px;padding:4px 12px;background:#0f0f11}
.terms b{display:block;color:#fff;margin-top:10px}.terms p{margin:2px 0 6px}
button{font:600 17px Inter,sans-serif;width:100%;min-height:52px;border:0;border-radius:12px;background:var(--red);color:#fff;cursor:pointer}
.err{background:#3a0d0d;border:1px solid #7f1d1d;border-radius:10px;padding:10px 12px;margin-bottom:14px}
.foot{color:var(--dim);font-size:12px;text-align:center;margin-top:22px}.hp{position:absolute;left:-5000px}.req{color:var(--red)}"""


def _input(k, label, typ, req, d):
    star = ' <span class="req">*</span>' if req else ""
    if isinstance(typ, list):
        opts = "".join('<option%s>%s</option>' % (" selected" if d.get(k) == o else "", o) for o in typ)
        return '<label><span>%s%s</span><select name="%s"%s><option value="">Choose</option>%s</select></label>' % (
            e(label), star, k, " required" if req else "", opts)
    kind = {"tel": ' type="tel" inputmode="numeric" maxlength="13"', "email": ' type="email"',
            "num": ' type="text" inputmode="numeric" maxlength="3"'}.get(typ, ' type="text"')
    return '<label><span>%s%s</span><input%s name="%s" value="%s"%s></label>' % (e(label), star, kind, k, e(d.get(k, "")), " required" if req else "")


def _box(k, text, d, req=False):
    return '<label class="chk"><input type="checkbox" name="%s" value="1"%s%s>%s</label>' % (
        k, " checked" if d.get(k) else "", " required" if req else "", e(text))


def terms_html():
    out = "".join("<b>%s</b><p>%s</p>" % (e(h), e(t)) for h, t in POLICIES)
    out += "<b>Refund &amp; Membership Terms</b>" + "".join("<p>%s</p>" % e(t) for t in REFUND)
    return out


def public_page(conn, d=None, err=""):
    d = d or {}
    gym = M.setting(conn, "gym_name", "House of Strength") or "House of Strength"
    addr = M.setting(conn, "gym_address", "")
    info = "".join(_input(k, l, t, r, d) for k, l, t, r in INFO)
    refs = '<p class="q">Reference</p><div class="row">%s</div>' % "".join(_box(k, l, d) for k, l in REFS)
    photo = '<p class="q">Photo/Video Consent: may we use your photo or video for promotional content?</p><div class="row">%s</div>' % "".join(
        '<label class="chk"><input type="radio" name="photo" value="%s"%s>%s</label>' % (v, " checked" if d.get("photo") == v else "", v)
        for v in ("Yes", "No"))
    minor = "".join(_input(k, l, "text", False, d) for k, l in MINOR)
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Member Consent Form · %s</title><link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>%s</style></head><body><div class="wrap"><div class="head"><img src="/logo.jpg" alt=""><div><h1>HOUSE OF STRENGTH GYM</h1><p>%s</p></div></div>
<div class="badge">MEMBER CONSENT FORM</div>%s
<form method="post" action="/join/submit"><input class="hp" name="website" tabindex="-1" autocomplete="off" aria-hidden="true">
<fieldset><legend>Member Information</legend><p class="q">%s</p>%s%s</fieldset>
<fieldset><legend>Terms</legend><div class="terms">%s</div><div style="margin-top:14px">%s</div></fieldset>
<fieldset><legend>Minor's Consent (If Under 18 Years Old)</legend><p class="q">For members under 18, a parent or legal guardian must provide consent below.</p>%s</fieldset>
<fieldset><legend>Final Declaration</legend>%s%s<div class="grid">%s%s</div></fieldset><button>Submit form</button></form>
<p class="foot">Your details go only to %s. <span class="req">*</span> required.<br>Powered by TFS · The First Solutions</p></div></body></html>""" % (
        e(gym), PUBLIC_CSS, e(addr), ('<div class="err">%s</div>' % e(err)) if err else "", e(INTRO), info, refs, terms_html(), photo,
        minor, _box("agree", FINAL_TEXT, d, True), _box("agree_biometric", BIOMETRIC_TEXT, d),
        _input("signature", "Member Signature (type your full name)", "text", True, d), _input("form_date", "Date", "text", False,
                                                                                               d or {"form_date": M.today().strftime("%d-%m-%Y")}),
        e(gym))


def thanks_page(conn, name):
    gym = M.setting(conn, "gym_name", "House of Strength") or "House of Strength"
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Thank you · %s</title><style>%s</style></head><body><div class="wrap" style="text-align:center;padding-top:60px">
<img src="/logo.jpg" alt="" style="width:96px;height:96px;border-radius:16px"><h1 style="font:700 28px Oswald,sans-serif">THANK YOU%s</h1>
<p style="color:var(--dim)">Your form has reached %s. At the reception, tell them your name; they will finish your membership
and register your fingerprint for the door.</p><p class="foot">Powered by TFS · The First Solutions</p></div></body></html>""" % (
        e(gym), PUBLIC_CSS, (", " + e(name.split()[0].upper())) if name else "", e(gym))


def submit(conn, form, ip):
    """Returns (ok, html)."""
    if form.get("website"):  # bots fill the hidden box
        return True, thanks_page(conn, "")
    d = clean(form)
    d["auth_by"] = d["auth_date"] = ""  # the gym fills these, not the member
    miss = missing(d)
    if len(d["phone"]) != 10:
        miss.append("a 10-digit phone number")
    if not d["agree"]:
        miss.append("the final declaration tick")
    if miss:
        return False, public_page(conn, d, "Please fill: " + ", ".join(miss) + ".")
    if not rate_ok(ip):
        return False, public_page(conn, d, "Too many forms from this phone. Please ask at the reception.")
    save(conn, d, "online", ip)
    return True, thanks_page(conn, d["name"])


# ---------------- staff pages ----------------

def get(conn, jid):
    r = conn.execute("SELECT * FROM joinings WHERE id=?", (jid,)).fetchone() if str(jid).isdigit() else None
    if not r:
        return None, {}
    try:
        return r, json.loads(r["data"] or "{}")
    except ValueError:
        return r, {}


def next_id(conn):
    """Next free member ID below the staff range: the ID to enroll on the gate machine."""
    top = conn.execute("SELECT MAX(client_id) FROM members WHERE client_id < ?", (M.STAFF_FROM,)).fetchone()[0] or 0
    try:  # also IDs already enrolled on the gate machine but not in the app yet
        pins = [int(r[0]) for r in conn.execute("SELECT DISTINCT pin FROM records WHERE kind='USER'") if str(r[0]).isdigit()]
        top = max([top] + [p for p in pins if p < M.STAFF_FROM])
    except Exception:
        pass
    return top + 1


def add_link(conn, r, d):
    from urllib.parse import urlencode
    return "/member?" + urlencode({"client_id": next_id(conn), "name": d.get("name", ""), "phone": d.get("phone", ""),
                                   "gender": d.get("gender", ""), "join": r["id"]})


STATUS = {"new": ("p-warn", "New"), "added": ("p-ok", "Member added"), "rejected": ("p-bad", "Did not join")}


def staff_page(conn, sn, q):
    import ui as U
    import whatsapp as W
    base = q.get("_base", "")
    link = base + "/join"
    rows = conn.execute("SELECT * FROM joinings ORDER BY status='new' DESC, id DESC LIMIT 200").fetchall()
    trs = ""
    for r in rows:
        try:
            d = json.loads(r["data"] or "{}")
        except ValueError:
            d = {}
        flags = health_flags(d)
        cls, st = STATUS.get(r["status"], ("", r["status"]))
        trs += ('<tr><td class="dim">%s</td><td><a href="/joinings/view?id=%d"><b>%s</b></a></td><td>%s</td><td class="dim">%s</td>'
                '<td>%s</td><td>%s</td><td><span class="pill %s">%s</span>%s</td><td style="white-space:nowrap">%s</td></tr>') % (
            e((r["created_at"] or "")[:16]), r["id"], e(U.nice(d.get("name", "")) or "—"), e(d.get("phone", "")),
            e(SOURCES.get(r["source"], r["source"] or "")),
            ('<span class="pill p-bad">%s</span>' % e(", ".join(flags)[:60])) if flags else '<span class="dim">None</span>',
            e(d.get("package", "") or "—"), cls, st,
            (' <a href="/m?id=%d">%s</a>' % (r["client_id"], U.member_id(r["client_id"]))) if r["client_id"] else "",
            ('<a class="btn red sm" href="%s">Add as member</a>' % e(add_link(conn, r, d))) if r["status"] == "new" else
            '<a class="btn sm" href="/joinings/view?id=%d">View</a>' % r["id"])
    wa_on = W.ready(conn)
    new = sum(1 for r in rows if r["status"] == "new")
    body = """<div class="two"><div class="panel" style="display:flex;flex-direction:column;gap:12px"><div class="ph" style="margin:0"><h2>Share the form</h2></div>
<p class="dim" style="margin:0">New members fill it on their phone, or fill the PDF. Print this QR and keep it at the reception.</p>
<div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap"><div id="jqr" style="background:#fff;padding:8px;border-radius:10px;width:146px;height:146px"></div>
<div style="display:flex;flex-direction:column;gap:8px;flex:1;min-width:200px"><input id="jlink" value="%s" readonly onclick="this.select()">
<div style="display:flex;gap:8px;flex-wrap:wrap"><button type="button" class="btn sm" onclick="navigator.clipboard&&navigator.clipboard.writeText(document.getElementById('jlink').value);this.textContent='Copied'">Copy link</button>
<a class="btn sm" href="/join.pdf" download="HOS-joining-form.pdf">%sEditable PDF</a><a class="btn sm" href="/join" target="_blank" rel="noopener">Open form</a></div></div></div>
<form method="post" action="/joinings/send" target="%s" style="display:flex;gap:8px;flex-wrap:wrap;align-items:flex-end;margin:0">
<label style="flex:1 1 200px">Send on WhatsApp to<input name="phone" inputmode="numeric" placeholder="10-digit mobile" required></label>
<button class="btn red">%s</button></form><p class="dim" style="margin:0;font-size:12px">%s</p></div>
<div class="panel" style="display:flex;flex-direction:column;gap:12px"><div class="ph" style="margin:0"><h2>Got a filled form back?</h2></div>
<p class="dim" style="margin:0">Upload the filled PDF from WhatsApp, or take a photo of a paper form. A filled PDF is read here on the server;
a photo or scan is read by AI. You check everything before adding the member.</p>
<label class="btn" style="flex-direction:row;cursor:pointer;align-self:flex-start">Choose PDF or photo<input type="file" id="jfile" accept="application/pdf,image/*" hidden></label>
<div id="jmsg" class="dim" style="font-size:13px"></div></div></div>
<div class="panel"><div class="ph"><h2>Joining forms</h2><span class="pill p-warn">%d new</span></div><div class="tw"><table>
<tr><th>Received</th><th>Name</th><th>Mobile</th><th>How</th><th>Health</th><th>Package</th><th>Status</th><th></th></tr>%s</table></div></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<script>try{new QRCode(document.getElementById('jqr'),{text:%s,width:130,height:130,correctLevel:QRCode.CorrectLevel.M})}catch(x){}
(function(){var m=document.getElementById('jmsg');document.getElementById('jfile').addEventListener('change',function(ev){var file=ev.target.files[0];if(!file){return}
function post(b64){m.textContent='Reading the form…';fetch('/joinings/upload',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},
body:'file='+encodeURIComponent(b64)+'&name='+encodeURIComponent(file.name)}).then(function(r){return r.json()}).then(function(d){
if(d.error){m.textContent=d.error;return}location.href='/joinings/view?id='+d.id+'&m='+encodeURIComponent(d.msg||'')}).catch(function(){m.textContent='Could not reach the server.'})}
var r=new FileReader();if(file.type==='application/pdf'){if(file.size>8e6){m.textContent='PDF is too large (max 8 MB).';return}
r.onload=function(){post(r.result.split(',')[1])};r.readAsDataURL(file);return}
r.onload=function(){var im=new Image();im.onload=function(){var k=Math.min(1,2000/Math.max(im.width,im.height));var c=document.createElement('canvas');
c.width=Math.round(im.width*k);c.height=Math.round(im.height*k);c.getContext('2d').drawImage(im,0,0,c.width,c.height);post(c.toDataURL('image/jpeg',0.85).split(',')[1])};
im.src=r.result};r.readAsDataURL(file)})})();</script>""" % (
        e(link), U.icon("down", 16), "_self" if wa_on else "_blank",
        "Send form" if wa_on else "Open WhatsApp",
        "Goes from the gym's WhatsApp number with the PDF and the link." if wa_on else
        "Opens WhatsApp with the link typed in; you press Send. (Automatic sending starts once WhatsApp is linked.)",
        new, trs or '<tr><td colspan="8" class="dim">No forms yet. Share the link or the QR.</td></tr>', json.dumps(link))
    return U.shell("Joining forms", "/joinings", body, sub="New members fill the form; you check it and add them",
                   msg=q.get("m", ""), cnt=U.counts(conn, sn))


def view_page(conn, sn, q):
    import ui as U
    r, d = get(conn, q.get("id", ""))
    if not r:
        return U.shell("Joining form", "/joinings", '<div class="panel">Form not found. <a href="/joinings">Back</a></div>')
    kv = lambda k, v=None: "<div><span>%s</span><b>%s</b></div>" % (e(LABELS[k]), e(d.get(k, "") or "—") if v is None else v)
    flags = health_flags(d)
    info = "".join(kv(k) for k, _, _, _ in INFO if k != "medical")
    info += kv("medical", '<span style="color:var(--red)">%s</span>' % e(flags[0]) if flags else e(d.get("medical") or "None"))
    info += "<div><span>Reference</span><b>%s</b></div>" % e(reference(d))
    yes = lambda k: "Agreed" if d.get(k) else '<span style="color:var(--red)">Not ticked</span>'
    auth = d.get("auth_by") or (r["handled_by"] if r["status"] == "added" else "")
    auth_d = d.get("auth_date") or ((r["handled_at"] or "")[:10] if r["status"] == "added" else "")
    sec = ['<div class="panel"><div class="ph"><h2>Member Information</h2></div><div class="kv">%s</div></div>' % info,
           '<div class="panel"><div class="ph"><h2>Consent</h2></div><div class="kv">%s%s%s%s%s<div><span>Authorized by (HOS Gym)</span><b>%s</b></div>'
           '<div><span>Date</span><b>%s</b></div></div></div>' % (
               kv("photo", e(d.get("photo") or "Not answered")), kv("agree", yes("agree")), kv("agree_biometric", yes("agree_biometric")),
               kv("signature"), kv("form_date"), e(auth or "—"), e(auth_d or "—"))]
    if is_minor(d) or any(d.get(k) for k, _ in MINOR):
        sec.append('<div class="panel"><div class="ph"><h2>Minor\'s Consent</h2></div><div class="kv">%s</div></div>' % "".join(kv(k) for k, _ in MINOR))
    cls, st = STATUS.get(r["status"], ("", r["status"]))
    acts = '<button class="btn" onclick="window.print()">%sPrint</button>' % U.icon("print", 16)
    if r["status"] == "new":
        acts += '<a class="btn red" href="%s">%sAdd as member</a>' % (e(add_link(conn, r, d)), U.icon("plus", 16))
        acts += ('<form method="post" action="/joinings/mark" style="display:inline"><input type="hidden" name="id" value="%d">'
                 '<button class="btn" name="do" value="rejected">Did not join</button></form>' % r["id"])
    if r["client_id"]:
        acts += '<a class="btn" href="/m?id=%d">Open member %s</a>' % (r["client_id"], U.member_id(r["client_id"]))
    if U.A.is_admin():
        acts += ('<form method="post" action="/joinings/mark" style="display:inline" onsubmit="return confirm(\'Delete this form?\')">'
                 '<input type="hidden" name="id" value="%d"><button class="btn" name="do" value="delete">Delete</button></form>' % r["id"])
    miss = missing(d)
    warn = ("Missing: " + ", ".join(miss) + ". Ask the member before adding.") if miss else ""
    body = """<div class="panel"><div class="hero"><div class="big">%s</div><div style="flex:1;min-width:220px"><h2>%s</h2>
<div class="dim" style="margin-top:6px">%s · received %s · <span class="pill %s">%s</span></div></div><div class="acts noprint">%s</div></div></div>%s
<p class="dim" style="font-size:12px">Powered by TFS · The First Solutions</p>""" % (
        U.initials(d.get("name") or "?"), e(U.nice(d.get("name", "")) or "—"), e(SOURCES.get(r["source"], r["source"] or "")),
        e((r["created_at"] or "")[:16]), cls, st, acts, "".join(sec))
    return U.shell("Joining form", "/joinings", body, sub='<a href="/joinings">Joining forms</a> › %s' % e(U.nice(d.get("name", ""))),
                   msg=q.get("m", ""), warn=e(warn), cnt=U.counts(conn, sn))


def mark(conn, f, is_admin, who):
    r, _ = get(conn, f.get("id", ""))
    if not r:
        return "Form not found."
    if f.get("do") == "delete":
        if not is_admin:
            return "Only the owner can delete."
        conn.execute("DELETE FROM joinings WHERE id=?", (r["id"],))
        return "Form deleted."
    if f.get("do") == "rejected":
        conn.execute("UPDATE joinings SET status='rejected', handled_by=?, handled_at=? WHERE id=?", (who, M.stamp(), r["id"]))
        return "Marked as did not join."
    return "Nothing changed."


def linked(conn, jid, client_id, who):
    """Called after the member form saves with ?join=ID."""
    if str(jid).isdigit() and str(client_id).isdigit():
        conn.execute("UPDATE joinings SET status='added', client_id=?, handled_by=?, handled_at=? WHERE id=?",
                     (int(client_id), who, M.stamp(), int(jid)))


def for_member(conn, client_id):
    r = conn.execute("SELECT * FROM joinings WHERE client_id=? ORDER BY id DESC LIMIT 1", (client_id,)).fetchone()
    if not r:
        return None, {}
    try:
        return r, json.loads(r["data"] or "{}")
    except ValueError:
        return r, {}


def form_message(conn, link):
    import whatsapp as W
    return W.text("form", name="", link=link)
