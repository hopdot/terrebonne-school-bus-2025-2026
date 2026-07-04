#!/usr/bin/env python3
"""
Live boarding scan monitor. Runs a batch of RFID taps and flags any
non-OK result (wrong bus / unknown ID / pending) as an alert-worthy
event. Flagged events are appended to data/flagged_scans.csv with a
timestamp so they can be committed and pushed to GitHub immediately,
and printed as ALERT: lines for the calling agent/automation to relay
as a real-time notification.
"""
import sys, os, csv, datetime
sys.path.insert(0, os.path.dirname(__file__))
from rfid_scanner import load_assignments, scan, ASSIGNMENTS_PATH

FLAGGED_LOG = os.path.join(os.path.dirname(__file__), "..", "data", "flagged_scans.csv")


def log_flags(alerts):
    """Append flagged events to data/flagged_scans.csv (creates header if new)."""
    is_new = not os.path.exists(FLAGGED_LOG)
    with open(FLAGGED_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["timestamp_utc", "screen", "message"])
        for a in alerts:
            writer.writerow([datetime.datetime.utcnow().isoformat(), a["screen"], a["message"]])


def run_batch(taps):
    assignments = load_assignments(ASSIGNMENTS_PATH)
    alerts = []
    for student_id, bus_number in taps:
        result = scan(student_id, bus_number, assignments)
        line = f"[{result['screen']}] {result['message']}"
        print(line)
        if not result["ok"]:
            alerts.append(result)
    if alerts:
        log_flags(alerts)
    return alerts


if __name__ == "__main__":
    # Live simulation batch — mix of correct + incorrect boardings
    taps = [
        ("S1001", "TPB-101"),  # correct
        ("S1011", "TPB-105"),  # wrong bus (should be TPB-106)
        ("S1099", "TPB-102"),  # unknown card
        ("S1005", "TPB-103"),  # correct
        ("S1008", "TPB-108"),  # wrong bus (should be TPB-104)
    ]
    alerts = run_batch(taps)
    print("\n--- ALERT SUMMARY ---")
    if alerts:
        for a in alerts:
            print(f"ALERT: [{a['screen']}] {a['message']}")
        print(f"\n{len(alerts)} flagged event(s) logged to data/flagged_scans.csv — ready to push.")
    else:
        print("No alerts.")
