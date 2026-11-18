#!/usr/bin/env python3
"""
Generate printable student ID cards with RFID numbers and screening QR codes.

Reads the registry snapshot (students_current.csv), the route table
(data/routes.csv) and the assignment output (data/student_assignments.csv),
then writes:

    cards/<student_id>_<slug>.png   one CR80 card per student, 300 dpi
    cards/all_student_cards.pdf     print sheet, one card per page
    data/card_registry.csv          student_id, rfid_uid, qr_payload, bus, route

Usage:
    python3 src/make_id_cards.py [--students PATH] [--routes PATH] [--out DIR]
"""
import argparse
import csv
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from id_card import build_payload, rfid_uid, render_card, grade_level

ROOT = os.path.join(os.path.dirname(__file__), "..")
DEFAULT_STUDENTS = os.path.join(ROOT, "students_current.csv")
DEFAULT_ROUTES = os.path.join(ROOT, "data", "routes.csv")
DEFAULT_ASSIGN = os.path.join(ROOT, "data", "student_assignments.csv")
DEFAULT_OUT = os.path.join(ROOT, "cards")
REGISTRY = os.path.join(ROOT, "data", "card_registry.csv")


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def slug(name):
    keep = [c.lower() if c.isalnum() else "-" for c in name]
    out = "".join(keep)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


def main():
    ap = argparse.ArgumentParser(description="Generate student ID cards with QR credentials.")
    ap.add_argument("--students", default=DEFAULT_STUDENTS)
    ap.add_argument("--routes", default=DEFAULT_ROUTES)
    ap.add_argument("--assignments", default=DEFAULT_ASSIGN)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    students = load_csv(args.students)
    routes = {r["bus_number"]: r for r in load_csv(args.routes)}
    assignments = {a["student_id"]: a for a in load_csv(args.assignments)}
    os.makedirs(args.out, exist_ok=True)
    issued = datetime.date.today().isoformat()

    made, registry = [], []
    for s in students:
        sid = s["student_id"]
        bus = assignments.get(sid, {}).get("assigned_bus_number") or s.get("assigned_bus_number", "")
        route = routes.get(bus, {"route_name": s.get("assigned_route", ""), "route_number": ""})
        payload = build_payload(sid)
        card = dict(s)
        card["issued"] = issued
        accent = grade_level(s.get("grade"))
        path = os.path.join(args.out, f"{sid}_{slug(s['full_name'])}.png")
        render_card(card, route, path, payload, bus or "UNASSIGNED", accent)
        made.append(path)
        registry.append({
            "student_id": sid,
            "full_name": s["full_name"],
            "school": s.get("school", ""),
            "grade": s.get("grade", ""),
            "rfid_uid": rfid_uid(sid),
            "assigned_bus_number": bus,
            "assigned_route": s.get("assigned_route", ""),
            "qr_payload": payload,
            "issued": issued,
        })

    with open(REGISTRY, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(registry[0].keys()))
        w.writeheader()
        w.writerows(registry)

    # print sheet: one card per page at exact CR80 size
    from PIL import Image
    pages = [Image.open(p).convert("RGB") for p in made]
    if pages:
        pages[0].save(os.path.join(args.out, "all_student_cards.pdf"),
                      save_all=True, append_images=pages[1:], resolution=300.0)

    print(f"Generated {len(made)} student ID cards in {args.out}")
    print(f"Card registry written to {REGISTRY}")
    print(f"RFID numbers issued: {', '.join(r['rfid_uid'] for r in registry)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
