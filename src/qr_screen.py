#!/usr/bin/env python3
"""
QR / RFID screening for student ID cards.

Verifies a card credential and answers the operational question a driver,
gate monitor or office clerk actually has: is this the right bus?

Modes:
    python3 src/qr_screen.py --image cards/S1001_ava-boudreaux.png --bus TPB-101
    python3 src/qr_screen.py --payload "TPSD1|S1001|1F2E3D4C|a1b2c3d4e5f6" --bus TPB-101
    python3 src/qr_screen.py --rfid 1F2E3D4C              # look up card number

Results:
    CORRECT BUS      card valid, student assigned to the bus that scanned
    WRONG BUS        card valid, student belongs on a different bus
    PENDING          card valid, assignment not confirmed yet
    INVALID CARD     bad format or signature (forged, copied, or altered)
    UNKNOWN CARD     valid format, but no such student in the registry

Every non-OK result and every OK scan appends to data/qr_screening_log.csv.
"""
import argparse
import csv
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from id_card import parse_payload, rfid_uid, is_dev_key

ROOT = os.path.join(os.path.dirname(__file__), "..")
STUDENTS = os.path.join(ROOT, "students_current.csv")
ASSIGNMENTS = os.path.join(ROOT, "data", "student_assignments.csv")
LOG = os.path.join(ROOT, "data", "qr_screening_log.csv")


def load_students():
    with open(STUDENTS, newline="", encoding="utf-8") as f:
        return {r["student_id"]: r for r in csv.DictReader(f)}


def load_assignments():
    with open(ASSIGNMENTS, newline="", encoding="utf-8") as f:
        return {r["student_id"]: r for r in csv.DictReader(f)}


def decode_image(path):
    """Decode a card QR, retrying on an upscaled copy for low-resolution scans."""
    import cv2
    img = cv2.imread(path)
    if img is None:
        raise SystemExit(f"Could not read image: {path}")
    detector = cv2.QRCodeDetector()
    for candidate in (img, cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)):
        data, *_ = detector.detectAndDecode(candidate)
        if data:
            return data
    raise SystemExit(f"No QR code detected in {path}")


def screen(payload, bus_number=None, rfid=None):
    students, assignments = load_students(), load_assignments()

    if rfid:
        hits = [s for s in students if rfid_uid(s) == rfid.upper().replace("0X", "")]
        if not hits:
            return {"result": "UNKNOWN CARD", "student_id": None,
                    "detail": f"no student holds card 0x{rfid.upper()}"}
        sid = hits[0]
        return screen(payload_for(sid), bus_number)

    cred = parse_payload(payload)
    if not cred["valid"]:
        return {"result": "INVALID CARD", "student_id": cred.get("student_id"),
                "detail": cred["reason"]}

    sid = cred["student_id"]
    if sid not in students:
        return {"result": "UNKNOWN CARD", "student_id": sid,
                "detail": "card signature is valid but the student is not in the registry"}

    asg = assignments.get(sid, {})
    expected = asg.get("assigned_bus_number", "")
    name = students[sid]["full_name"]

    if asg.get("status") != "active" or not expected:
        return {"result": "PENDING", "student_id": sid,
                "detail": f"{name} has no confirmed bus assignment yet"}

    if not bus_number:
        return {"result": "LOOKUP", "student_id": sid,
                "detail": f"{name} belongs on {expected} ({asg.get('assigned_route','')})"}

    if bus_number == expected:
        return {"result": "CORRECT BUS", "student_id": sid,
                "detail": f"{name} boards {expected} ({asg.get('assigned_route','')})"}
    return {"result": "WRONG BUS", "student_id": sid,
            "detail": f"{name} is assigned to {expected} ({asg.get('assigned_route','')}), "
                      f"not {bus_number}"}


def payload_for(student_id):
    from id_card import build_payload
    return build_payload(student_id)


def log_scan(result, bus_number=None, mode="qr", payload=None):
    is_new = not os.path.exists(LOG)
    with open(LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["timestamp_utc", "mode", "result", "student_id",
                        "bus_scanned", "detail", "payload"])
        w.writerow([datetime.datetime.utcnow().isoformat(), mode, result["result"],
                    result.get("student_id") or "", bus_number or "",
                    result.get("detail", ""), payload or ""])


def main():
    ap = argparse.ArgumentParser(description="Screen a student ID card QR code or RFID number.")
    ap.add_argument("--image", help="PNG/JPG of a card to decode")
    ap.add_argument("--payload", help="raw QR payload string")
    ap.add_argument("--rfid", help="RFID card number, e.g. 1F2E3D4C")
    ap.add_argument("--bus", help="bus the card was scanned on, e.g. TPB-101")
    ap.add_argument("--no-log", action="store_true", help="do not append to the screening log")
    args = ap.parse_args()

    if is_dev_key():
        print("WARNING: TPSD_QR_SECRET is not set; using the development signing key.",
              file=sys.stderr)

    payload = args.payload
    mode = "payload"
    if args.image:
        payload, mode = decode_image(args.image), "qr-image"
    if not payload and not args.rfid:
        raise SystemExit("Provide --image, --payload or --rfid")

    result = screen(payload, args.bus, args.rfid)
    print(f"[{result['result']}] {result['detail']}")
    if not args.no_log:
        log_scan(result, args.bus, mode, payload)
    return 0 if result["result"] in ("CORRECT BUS", "LOOKUP") else 1


if __name__ == "__main__":
    sys.exit(main())
