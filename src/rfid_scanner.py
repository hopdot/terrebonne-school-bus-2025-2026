#!/usr/bin/env python3
"""
Onboard RFID boarding-screen simulator.

Each bus is equipped with a screen + RFID reader at the door. When a
student taps their ID card (student_id doubles as their RFID tag id),
this looks up their assignment and shows what the screen would display.

Usage:
    python3 rfid_scanner.py <student_id> [--bus TPB-103]

If --bus is omitted, it just shows the student's correct assignment.
If --bus is given, it verifies the student is boarding the right bus
and returns a boarding decision (matches what the physical screen
would render).
"""
import csv
import argparse
import os
import sys

ASSIGNMENTS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "student_assignments.csv")


def load_assignments(path):
    if not os.path.exists(path):
        print("No assignment data found — run assign_bus.py first.")
        sys.exit(1)
    with open(path, newline="", encoding="utf-8") as f:
        return {row["student_id"]: row for row in csv.DictReader(f)}


def scan(student_id, bus_number, assignments):
    record = assignments.get(student_id)

    if record is None:
        return {
            "screen": "UNKNOWN ID",
            "message": f"Card {student_id} not recognized. Flagged for office follow-up.",
            "ok": False,
        }

    if record["status"] == "pending":
        return {
            "screen": "PENDING ASSIGNMENT",
            "message": f"{record['full_name']} has no confirmed route yet. Contact transportation office.",
            "ok": False,
        }

    correct_bus = record["assigned_bus_number"]

    if bus_number is None:
        return {
            "screen": "LOOKUP",
            "message": f"{record['full_name']} ({student_id}) rides {correct_bus} — {record['assigned_route']}, stop: {record['assigned_stop']}",
            "ok": True,
        }

    if bus_number.strip().upper() == correct_bus.strip().upper():
        return {
            "screen": "BOARDING OK",
            "message": f"Welcome aboard, {record['full_name']}! Stop: {record['assigned_stop']}",
            "ok": True,
        }

    return {
        "screen": "WRONG BUS",
        "message": f"{record['full_name']} is assigned to {correct_bus} ({record['assigned_route']}), not this bus.",
        "ok": False,
    }


def main():
    parser = argparse.ArgumentParser(description="Simulate an onboard RFID boarding scan.")
    parser.add_argument("student_id")
    parser.add_argument("--bus", default=None, help="Bus number this scan happened on")
    args = parser.parse_args()

    assignments = load_assignments(ASSIGNMENTS_PATH)
    result = scan(args.student_id, args.bus, assignments)

    print(f"[{result['screen']}] {result['message']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
