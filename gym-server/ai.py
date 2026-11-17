"""Claude-powered helpers for the House of Strength app.

AI-fill billing: staff type one line ("Rohit 3 month, 1500 discount, 5000 UPI se diya");
Claude turns it into bill fields. Nothing is saved here: the page fills the form and a
person checks it and taps Save. Member lookup happens on our server - the member list
and phone numbers are never sent to the API, only the line the staff typed.

Needs the `anthropic` package and ANTHROPIC_API_KEY in the service environment.
"""
import json
import os

try:
    import anthropic
except ImportError:  # the app still runs; AI buttons say it is not set up
    anthropic = None

MODEL = os.environ.get("HOS_AI_MODEL", "claude-haiku-5-5")
MODES = ["UPI", "Cash", "Card", "Online"]


def available():
    return anthropic is not None and bool(os.environ.get("ANTHROPIC_API_KEY"))


def _client():
    return anthropic.Anthropic(timeout=60, max_retries=2)


def _ask(system, text, schema):
    """One structured-output request; returns (dict or None, error message)."""
    if not available():
        return None, "AI is not set up on the server yet."
    try:
        # Claude Haiku 5.5: no server-side fallback exists for it, so a refusal is handled below.
        resp = _client().messages.create(
            model=MODEL,
            max_tokens=4000,
            system=system,
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": text}],  # text: a string, or content blocks (image + text)
        )
    except anthropic.AuthenticationError:
        return None, "The AI key on the server is not valid."
    except anthropic.RateLimitError:
        return None, "AI is busy right now. Try again in a minute."
    except anthropic.BadRequestError as exc:
        print("ai bad request: %s" % exc.message, flush=True)
        return None, "AI could not read that. Fill the form by hand."
    except anthropic.APIStatusError as exc:
        print("ai api error %s: %s" % (exc.status_code, exc.message), flush=True)
        return None, "AI is not answering right now. Fill the form by hand."
    except anthropic.APIConnectionError:
        return None, "Server could not reach the AI. Check the internet and try again."
    if resp.stop_reason == "refusal":
        return None, "AI declined this one. Fill the form by hand."
    if resp.stop_reason == "max_tokens":
        return None, "AI answer was cut off. Try a shorter line."
    texts = [b.text for b in resp.content if b.type == "text"]
    if not texts:
        return None, "AI gave no answer. Fill the form by hand."
    try:
        return json.loads(texts[0]), ""
    except ValueError:
        return None, "AI answer could not be read. Fill the form by hand."


def bill_fill(text, packages, trainers, today_iso):
    """packages: [(name, days, price, kind)], trainers: [name]. Returns (fields, error)."""
    pk_names = [p[0] for p in packages]
    schema = {
        "type": "object",
        "properties": {
            "member": {"type": "string", "description": "Member name or ID exactly as written, e.g. 'Rohit' or '676'"},
            "bill_type": {"type": "string", "enum": ["gym", "pt"]},
            "package": {"type": "string", "enum": pk_names + [""]},
            "start_date": {"type": "string", "description": "YYYY-MM-DD, or empty if not said"},
            "trainer": {"type": "string", "enum": trainers + [""]},
            "discount": {"type": "number"},
            "admission": {"type": "number"},
            "paid": {"type": "number", "description": "Amount paid now; -1 if not said"},
            "mode": {"type": "string", "enum": MODES + [""]},
            "unclear": {"type": "string", "description": "Short note on anything that was unclear, else empty"},
        },
        "required": ["member", "bill_type", "package", "start_date", "trainer", "discount", "admission", "paid", "mode",
                     "unclear"],
        "additionalProperties": False,
    }
    catalogue = "\n".join("- %s: %d days, Rs %g (%s)" % (n, d, p, "personal training" if k == "pt" else "gym") for n, d, p, k in packages)
    system = (
        "You fill a gym bill form for House of Strength (India) from one short line typed by the front desk, "
        "often Hinglish (e.g. 'Rohit 3 month, 1500 discount, 5000 UPI se diya').\n"
        "Today is %s.\n\nPackages (pick the closest by name and duration; 'mahina'/'month' = month, 'saal'/'year' = 1 Year, "
        "'PT' = personal training):\n%s\n\nTrainers: %s\n\n"
        "Rules: amounts are rupees, '1.5k' = 1500. 'discount'/'off'/'kam' is a discount amount; a percentage means that percent "
        "of the package price. 'diya'/'paid'/'jama' is the amount paid now; if the line says fully paid without an amount, "
        "use package price minus discount plus admission. Use 0 when discount or admission is not mentioned and -1 when the "
        "paid amount is not mentioned. 'gpay'/'phonepe'/'paytm' = UPI, 'nakad'/'cash' = Cash. 'kal se' = tomorrow, 'aaj se' = today. "
        "Never invent a member, package or trainer; leave a field empty if it is not in the line, and say what was unclear."
    ) % (today_iso, catalogue, ", ".join(trainers) or "none")
    data, err = _ask(system, text.strip()[:500], schema)
    return data, err


def expense_fill(text, image_b64, media_type, categories, today_iso):
    """A typed line and/or a photo of a bill -> expense fields. Returns (fields, error)."""
    schema = {
        "type": "object",
        "properties": {
            "spent_on": {"type": "string", "description": "YYYY-MM-DD"},
            "category": {"type": "string", "enum": categories},
            "amount": {"type": "number"},
            "paid_to": {"type": "string"},
            "mode": {"type": "string", "enum": ["UPI", "Cash", "Bank", "Card", ""]},
            "note": {"type": "string"},
            "unclear": {"type": "string"},
        },
        "required": ["spent_on", "category", "amount", "paid_to", "mode", "note", "unclear"],
        "additionalProperties": False,
    }
    system = (
        "You fill a gym's expense form from a short Hinglish line and/or a photo of a bill or receipt. Today is %s. "
        "Categories: %s ('bijli'/'light'/'MPEB' = Electricity, 'kiraya' = Rent, 'safai' = Cleaning, 'repair'/'theek' = Repairs, "
        "'ads'/'flyer'/'Instagram' = Marketing, machines/weights = Equipment, staff pay = Salaries). "
        "Amount is the total paid in rupees ('8.4k' = 8400); from a bill use the grand total. 'aaj' = today, 'kal' = yesterday "
        "unless the line clearly means a future date. Use the bill's date if a photo shows one and the line gives none. "
        "paid_to is the shop, company or person paid. Leave a field empty or 0 if unknown and say what was unclear."
    ) % (today_iso, ", ".join(categories))
    content = []
    if image_b64:
        content.append({"type": "image", "source": {"type": "base64", "media_type": media_type or "image/jpeg", "data": image_b64}})
    content.append({"type": "text", "text": (text or "Read this bill.").strip()[:500]})
    return _ask(system, content, schema)
