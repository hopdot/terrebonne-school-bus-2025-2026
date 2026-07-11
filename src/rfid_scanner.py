#!/usr/bin/env python3
"""
RFID boarding scanner. Each scan returns a result with:
- ok: bool (True if boarding is correct, False for wrong bus / unknown ID / etc)
- screen: str (display line for the bus terminal)
- message: str (alert message if flagged)
"""
import csv
import os

ASSIGNMENTS_PATH = "data/student_assignments.csv"

def load_assignments(path):
    assignments = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            assignments[row["student_id"]] = row
    return assignments

def scan(student_id, bus_number, assignments):
    if student_id not in assignments:
        return {
            "ok": False,
            "screen": "UNKNOWN ID",
            "message": f"Card {student_id} not recognized. Flagged for office follow-up."
        }
    
    record = assignments[student_id]
    assigned_bus = record["assigned_bus_number"]
    assigned_route = record["assigned_route"]
    zone = record["zone"]
    
    if bus_number != assigned_bus:
        return {
            "ok": False,
            "screen": "WRONG BUS",
            "message": f"{record['full_name']} is assigned to {assigned_bus} ({assigned_route}), not this bus."
        }
    
    return {
        "ok": True,
        "screen": "BOARDING OK",
        "message": f"Welcome aboard, {record['full_name']}! Route: {assigned_route} ({zone})"
    }
