#!/usr/bin/env python3
"""
Student ID card model: signed QR credential + printable card rendering.

The QR payload is a short, signed string:

    TPSD1|<student_id>|<rfid_uid>|<sig>

`sig` is the first 12 hex characters of HMAC-SHA256(secret, "<student_id>|<rfid_uid>").
A scanner can therefore reject a copied or hand-written code that does not
carry a valid signature, without touching the network.

The card deliberately prints only what a hall monitor or driver needs:
name, school, grade, zone, route, bus, RFID number and the QR code.
Home address and guardian phone are never rendered on the card.

The signing key comes from the TPSD_QR_SECRET environment variable. The
development fallback below is not a secret and must be replaced before
production use (see README).
"""
import hashlib
import hmac
import os

PAYLOAD_VERSION = "TPSD1"
DEV_SECRET = "tpsd-development-only-change-me"

def signing_key():
    key = os.getenv("TPSD_QR_SECRET", "").strip()
    return key or DEV_SECRET

def is_dev_key():
    return not os.getenv("TPSD_QR_SECRET", "").strip()

def rfid_uid(student_id):
    """Stable 8-hex-digit card UID derived from the student id."""
    digest = hashlib.sha256(("tpsd-rfid:" + student_id).encode()).hexdigest()
    return digest[:8].upper()

def sign(student_id, uid, key=None):
    key = key or signing_key()
    mac = hmac.new(key.encode(), f"{student_id}|{uid}".encode(), hashlib.sha256).hexdigest()
    return mac[:12]

def build_payload(student_id, key=None):
    uid = rfid_uid(student_id)
    return f"{PAYLOAD_VERSION}|{student_id}|{uid}|{sign(student_id, uid, key)}"

def parse_payload(payload, key=None):
    """Return a dict describing the credential and whether it is valid."""
    parts = (payload or "").strip().split("|")
    if len(parts) != 4 or parts[0] != PAYLOAD_VERSION:
        return {"valid": False, "reason": "unrecognized card format", "payload": payload}
    _, student_id, uid, sig = parts
    expected = sign(student_id, uid, key)
    if not hmac.compare_digest(sig.lower(), expected.lower()):
        return {"valid": False, "reason": "signature mismatch (forged or altered card)",
                "student_id": student_id, "rfid_uid": uid, "payload": payload}
    if uid != rfid_uid(student_id):
        return {"valid": False, "reason": "card UID does not match student record",
                "student_id": student_id, "rfid_uid": uid, "payload": payload}
    return {"valid": True, "student_id": student_id, "rfid_uid": uid, "payload": payload}

# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------
CARD_W, CARD_H = 1012, 638          # CR80 at 300 dpi
NAVY = (18, 58, 92)
INK = (20, 32, 43)
MUTED = (96, 112, 128)
LINE = (216, 226, 234)
WHITE = (255, 255, 255)

LEVEL_ACCENT = {
    "elementary": (15, 111, 108),   # teal
    "middle": (168, 104, 27),       # amber
    "high": (18, 58, 92),           # navy
}

FONT_DIR = "/usr/share/fonts/truetype/dejavu"

def _font(name, size):
    from PIL import ImageFont
    path = os.path.join(FONT_DIR, name)
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def grade_level(grade_span_or_grade):
    """Classify a grade ('3') or span ('PK-5', '6-8') into a card accent band."""
    g = str(grade_span_or_grade or "").upper().replace("PK", "0").replace("K", "0")
    numbers = [int(n) for n in __import__("re").findall(r"\d+", g)]
    if not numbers:
        return "elementary"
    top = max(numbers)
    if top <= 5:
        return "elementary"
    if top <= 8:
        return "middle"
    return "high"

def _fit(d, text, font_name, max_size, min_size, max_width):
    """Return the largest font at or below max_size whose text fits max_width."""
    size = max_size
    while size > min_size:
        f = _font(font_name, size)
        if d.textlength(text, font=f) <= max_width:
            return f
        size -= 2
    return _font(font_name, min_size)

def render_card(student, route, out_path, qr_payload, bus_number, accent="elementary"):
    """Draw one CR80 card PNG."""
    import qrcode
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (CARD_W, CARD_H), WHITE)
    d = ImageDraw.Draw(img)
    f_badge = _font("DejaVuSans-Bold.ttf", 19)
    f_name = _font("DejaVuSans-Bold.ttf", 54)
    f_school = _font("DejaVuSans.ttf", 26)
    f_meta = _font("DejaVuSans.ttf", 22)
    f_label = _font("DejaVuSans-Bold.ttf", 15)
    f_mono = _font("DejaVuSansMono-Bold.ttf", 30)
    f_tiny = _font("DejaVuSans.ttf", 17)

    color = LEVEL_ACCENT.get(accent, NAVY)

    # header band
    d.rectangle([0, 0, CARD_W, 96], fill=NAVY)
    d.rectangle([0, 96, CARD_W, 102], fill=color)
    d.text((36, 20), "TERREBONNE PARISH SCHOOL DISTRICT", font=f_badge, fill=WHITE)
    d.text((36, 52), "STUDENT IDENTIFICATION CARD  ·  2025-2026", font=f_meta, fill=(196, 214, 230))

    # photo placeholder block (no student photographs are stored by this system)
    d.rounded_rectangle([36, 134, 236, 334], radius=10, outline=LINE, width=2)
    d.text((60, 220), "PHOTO", font=f_meta, fill=MUTED)
    d.text((60, 250), "ON FILE", font=f_meta, fill=MUTED)

    # identity block — text auto-fits the space left of the QR panel
    name = (student.get("full_name") or "").strip()
    school = (student.get("school") or "").strip()
    f_name = _fit(d, name, "DejaVuSans-Bold.ttf", 54, 30, 460)
    f_school = _fit(d, school, "DejaVuSans.ttf", 26, 17, 460)
    d.text((268, 140), name, font=f_name, fill=INK)
    d.text((268, 210), school, font=f_school, fill=color)
    d.text((268, 250), f"Grade {student.get('grade','')}   ·   Zone: {student.get('zone','')}"[:56],
           font=f_meta, fill=MUTED)
    d.text((268, 284), f"Student ID {student.get('student_id','')}", font=f_meta, fill=MUTED)

    # bus pill
    pill = f"BUS {bus_number}  ·  {route.get('route_name','')}  ·  {route.get('route_number','')}"
    tw = d.textlength(pill, font=f_meta)
    d.rounded_rectangle([268, 330, 268 + tw + 36, 378], radius=24, fill=color)
    d.text((286, 342), pill, font=f_meta, fill=WHITE)

    # RFID line
    uid = rfid_uid(student.get("student_id", ""))
    d.text((268, 400), "RFID CARD NUMBER", font=f_label, fill=MUTED)
    d.text((268, 420), f"0x{uid}", font=f_mono, fill=INK)
    d.text((268, 470), "Tap this card on the bus reader, or scan the QR code", font=f_tiny, fill=MUTED)
    d.text((268, 492), "at the gate to verify the correct bus assignment.", font=f_tiny, fill=MUTED)

    # QR panel
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_Q,
                       box_size=10, border=2)
    qr.add_data(qr_payload)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB").resize((248, 248))
    img.paste(qr_img, (CARD_W - 286, 124))
    d.rounded_rectangle([CARD_W - 288, 122, CARD_W - 36, 374], radius=8, outline=LINE, width=2)
    d.text((CARD_W - 196, 384), "SCREEN QR", font=f_label, fill=MUTED)

    # footer
    d.line([0, CARD_H - 78, CARD_W, CARD_H - 78], fill=LINE, width=2)
    d.text((36, CARD_H - 60), "Property of Terrebonne Parish School District.",
           font=f_tiny, fill=MUTED)
    d.text((36, CARD_H - 38), "If found, return to Transportation. Replace if lost or damaged.",
           font=f_tiny, fill=MUTED)
    d.text((CARD_W - 250, CARD_H - 60), f"issued {student.get('issued','')}", font=f_tiny, fill=MUTED)

    img.save(out_path, "PNG", dpi=(300, 300))
    return out_path
