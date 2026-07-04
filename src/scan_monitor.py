#!/usr/bin/env python3
"""
Live boarding scan monitor. Runs a batch of RFID taps and flags any
non-OK result (wrong bus / unknown ID / pending) as an alert-worthy
event, printing an ALERT: line the calling automation/agent can parse
and forward as a real-time notification.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from rfid_scanner import load_assignments, scan, ASSIGNMENTS_PATH

def run_batch(taps):
    assignments = load_assignments(ASSIGNMENTS_PATH)
    alerts = []
    for student_id, bus_number in taps:
        result = scan(student_id, bus_number, assignments)
        line = f"[{result['screen']}] {result['message']}"
        print(line)
        if not result["ok"]:
            alerts.append(line)
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
            print("ALERT:", a)
    else:
        print("No alerts.")
