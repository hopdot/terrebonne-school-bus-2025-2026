#!/usr/bin/env python3
"""
Zone-based student -> bus assignment engine for Terrebonne Parish
School Bus Routing, 2025-2026.

Reads data/routes.csv and data/students.csv, matches each student's
`zone` to the route that covers it, and writes an updated
data/student_assignments.csv with the resolved bus/route/stop for
every student. Unmatched students are marked status=pending so the
transportation office can confirm manually.

Usage:
    python3 assign_bus.py [--routes PATH] [--students PATH] [--out PATH]
"""
import csv
import argparse
import os
import sys

DEFAULT_ROUTES = os.path.join(os.path.dirname(__file__), "..", "data", "routes.csv")
DEFAULT_STUDENTS = os.path.join(os.path.dirname(__file__), "..", "data", "students.csv")
DEFAULT_OUT = os.path.join(os.path.dirname(__file__), "..", "data", "student_assignments.csv")


def load_routes(path):
    """Return a dict of zone_name -> route dict, plus the full route list."""
    zone_to_route = {}
    routes = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            routes.append(row)
            zones = [z.strip() for z in row["zones"].split(";") if z.strip()]
            for z in zones:
                zone_to_route[z.lower()] = row
    return zone_to_route, routes


def load_students(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def assign(students, zone_to_route):
    assignments = []
    unmatched = 0
    for s in students:
        zone_key = s.get("zone", "").strip().lower()
        route = zone_to_route.get(zone_key)

        if route is None:
            # Fallback: try a loose match on zone name containing a known zone token
            route = next(
                (r for z, r in zone_to_route.items() if z in zone_key or zone_key in z),
                None,
            )

        if route:
            assignments.append({
                "student_id": s["student_id"],
                "full_name": s["full_name"],
                "school": s["school"],
                "zone": s["zone"],
                "assigned_bus_number": route["bus_number"],
                "assigned_route": route["route_name"],
                "assigned_stop": f"{s['zone']} area stop",
                "status": "active",
            })
        else:
            unmatched += 1
            assignments.append({
                "student_id": s["student_id"],
                "full_name": s["full_name"],
                "school": s["school"],
                "zone": s["zone"],
                "assigned_bus_number": "",
                "assigned_route": "",
                "assigned_stop": "",
                "status": "pending",
            })
    return assignments, unmatched


def write_assignments(assignments, out_path):
    fieldnames = [
        "student_id", "full_name", "school", "zone",
        "assigned_bus_number", "assigned_route", "assigned_stop", "status",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(assignments)


def main():
    parser = argparse.ArgumentParser(description="Assign students to bus routes by zone.")
    parser.add_argument("--routes", default=DEFAULT_ROUTES)
    parser.add_argument("--students", default=DEFAULT_STUDENTS)
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args()

    zone_to_route, routes = load_routes(args.routes)
    students = load_students(args.students)
    assignments, unmatched = assign(students, zone_to_route)
    write_assignments(assignments, args.out)

    print(f"Assigned {len(assignments) - unmatched}/{len(assignments)} students "
          f"across {len(routes)} routes.")
    if unmatched:
        print(f"WARNING: {unmatched} student(s) need manual zone confirmation "
              f"(status=pending) — see {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
