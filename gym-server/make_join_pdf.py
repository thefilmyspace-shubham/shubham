"""Builds joining_form.pdf: the gym's Member Consent Form as an editable (fillable) PDF.

Run once after changing the wording:  python3 make_join_pdf.py
Needs reportlab (only here, not on the server). Field names match joining.py, so a filled
copy sent back by a member is read straight into the app.
"""
import os

from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

import joining as J

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "joining_form.pdf")
W, H = A4
L, R = 48, W - 48           # box edges
X0, X1 = L + 18, R - 18     # text area
RED = HexColor("#c40000")
GREY = HexColor("#444444")
FIELD_BG = HexColor("#f3f6ff")


def wrap(c, text, font, size, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if c.stringWidth(t, font, size) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def para(c, y, text, size=10.5, font="Helvetica", lead=15, color=GREY):
    c.setFont(font, size)
    c.setFillColor(color)
    for line in wrap(c, text, font, size, X1 - X0):
        c.drawString(X0, y, line)
        y -= lead
    return y


def head(c, y, text):
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(black)
    c.drawString(X0, y, text)
    return y - 17


def field(c, name, label, x, y, w, tip=None):
    """Label then an underlined fillable box up to x + w."""
    c.setFont("Helvetica", 10.5)
    c.setFillColor(GREY)
    c.drawString(x, y, label + ":")
    lx = x + c.stringWidth(label + ":", "Helvetica", 10.5) + 6
    c.setStrokeColor(HexColor("#999999"))
    c.line(lx, y - 2, x + w, y - 2)
    c.acroForm.textfield(name=name, tooltip=tip or label, x=lx, y=y - 3, width=x + w - lx, height=15, fontSize=10.5,
                         borderWidth=0, fillColor=FIELD_BG, textColor=black, forceBorder=False)


def box(c, name, x, y, label, tip=None):
    c.acroForm.checkbox(name=name, tooltip=tip or label, x=x, y=y - 2, size=11, buttonStyle="check", borderColor=GREY,
                        fillColor=white, textColor=black, forceBorder=True)
    c.setFont("Helvetica", 10.5)
    c.setFillColor(GREY)
    c.drawString(x + 15, y, label)
    return x + 15 + c.stringWidth(label, "Helvetica", 10.5) + 14


def frame(c, top):
    c.setStrokeColor(GREY)
    c.setLineWidth(1)
    c.rect(L, 46, R - L, top - 46)
    c.setFont("Helvetica", 7.5)
    c.setFillColor(HexColor("#888888"))
    c.drawCentredString(W / 2, 32, "House of Strength Gym · 4th Floor, Gayatri Mall, Subhash Marg, Ratlam · Powered by TFS · The First Solutions")


def page1(c):
    top = H - 60
    frame(c, top)
    c.drawImage(os.path.join(HERE, "logo.jpg"), X0, top - 78, 66, 66, mask="auto")
    c.setFillColor(RED)
    c.setFont("Helvetica-Bold", 27)
    c.drawString(X0 + 78, top - 46, "HOUSE OF STRENGTH GYM")
    c.setFillColor(GREY)
    c.roundRect(X0 + 128, top - 82, 252, 28, 6, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 17)
    c.drawCentredString(X0 + 254, top - 74, "MEMBER CONSENT FORM")
    y = top - 110
    c.setFont("Helvetica", 10.5)
    c.setFillColor(GREY)
    c.drawString(X0, y, "Member Information")
    y = para(c, y - 18, J.INTRO, lead=16) - 8
    full = X1 - X0
    field(c, "name", "Full Name", X0, y, full * 0.52)
    field(c, "guardian", "Parent/Guardian Name", X0 + full * 0.54, y, full * 0.46)
    y -= 32
    field(c, "dob", "Date of Birth", X0, y, full * 0.42)
    field(c, "age", "Age", X0 + full * 0.44, y, full * 0.2)
    field(c, "gender", "Gender", X0 + full * 0.66, y, full * 0.34, "Gender: M / F")
    y -= 32
    field(c, "address", "Address", X0, y, full)
    y -= 32
    field(c, "phone", "Phone Number", X0, y, full * 0.48)
    field(c, "email", "Email", X0 + full * 0.5, y, full * 0.5)
    y -= 32
    field(c, "emergency", "Emergency Contact Name & Number", X0, y, full)
    y -= 32
    field(c, "medical", "Medical Conditions or Injuries (if any)", X0, y, full)
    y -= 36
    c.setFont("Helvetica-Bold", 10.5)
    c.setFillColor(black)
    c.drawString(X0, y, "Reference -")
    x = X0 + 66
    for k, l in J.REFS:
        x = box(c, k, x, y, l)
    y -= 34
    for h, t in J.POLICIES[:4]:
        y = head(c, y, h)
        y = para(c, y, t, lead=17) - 9
    c.showPage()


def page2(c):
    top = H - 60
    frame(c, top)
    y = top - 26
    for h, t in J.POLICIES[4:]:
        y = head(c, y, h)
        y = para(c, y, t, lead=17) - 9
    c.setFont("Helvetica", 10.5)
    c.setFillColor(GREY)
    c.drawString(X0, y, "Photo/Video Consent:")
    x = X0 + 116
    x = box(c, "photo_yes", x, y, "Yes", "Photo/Video consent: Yes")
    box(c, "photo_no", x, y, "No", "Photo/Video consent: No")
    y -= 20
    y = head(c, y, "Refund & Membership Terms")
    for t in J.REFUND:
        y = para(c, y, t, lead=16.5)
    y -= 9
    y = head(c, y, "Minor's Consent (If Under 18 Years Old)")
    y = para(c, y, "For members under 18, a parent or legal guardian must provide consent below.") - 6
    full = X1 - X0
    for k, l in J.MINOR:
        field(c, k, l.replace(" (type full name)", ""), X0, y, full if k != "minor_date" else full * 0.45)
        y -= 30
    y -= 2
    c.setFont("Helvetica-Bold", 10.5)
    c.setFillColor(black)
    c.drawString(X0, y, "Final Declaration")
    y = para(c, y - 16, J.FINAL_TEXT, lead=15) - 2
    c.acroForm.checkbox(name="agree", tooltip="I agree", x=X0, y=y - 2, size=11, buttonStyle="check", borderColor=GREY,
                        fillColor=white, textColor=black, forceBorder=True)
    c.setFont("Helvetica", 10.5)
    c.setFillColor(GREY)
    c.drawString(X0 + 15, y, "I agree.")
    y -= 18
    c.acroForm.checkbox(name="agree_biometric", tooltip="Fingerprint consent", x=X0, y=y - 2, size=11, buttonStyle="check",
                        borderColor=GREY, fillColor=white, textColor=black, forceBorder=True)
    for i, line in enumerate(wrap(c, J.BIOMETRIC_TEXT, "Helvetica", 10.5, full - 16)):
        c.drawString(X0 + 15, y - i * 14, line)
    y -= 34
    field(c, "signature", "Member Signature", X0, y, full * 0.6, "Member signature: type your full name")
    field(c, "form_date", "Date", X0 + full * 0.64, y, full * 0.36)
    y -= 32
    field(c, "auth_by", "Authorized by (HOS Gym)", X0, y, full * 0.6, "Filled by the gym")
    field(c, "auth_date", "Date", X0 + full * 0.64, y, full * 0.36, "Filled by the gym")
    c.showPage()


def build():
    c = canvas.Canvas(OUT, pagesize=A4)
    c.setTitle("House of Strength Gym - Member Consent Form")
    c.setAuthor("House of Strength Gym")
    page1(c)
    page2(c)
    c.save()
    return OUT


if __name__ == "__main__":
    print(build())
