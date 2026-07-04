# Terrebonne Parish School Bus Routing — 2025-2026

Student-to-bus assignment and RFID boarding verification system for the
2025-2026 school year.

## What this does

1. **Student registration** — students are registered with a `student_id`
   (also used as their RFID card ID), home address, and attendance `zone`.
2. **Bus assignment** — `src/assign_bus.py` matches each registered student
   to the correct bus/route based on their zone, and writes the assignment
   back to the Student record (`assigned_bus_number`, `assigned_route`,
   `assigned_stop`).
3. **Onboard RFID screen** — `src/rfid_scanner.py` simulates the screen
   mounted on each bus. Driver/monitor scans a student's ID card; the
   screen looks up the student and shows:
   - ✅ **Correct bus** — green confirmation, student name + stop
   - ⚠️ **Wrong bus** — red warning with the student's correct bus number
   - ❌ **Unknown ID** — flagged for office follow-up
4. **Nightly sync** — `src/nightly_update.py` re-runs assignment for any
   new/changed student registrations and bus routes, so overnight
   registration changes are live before the morning routes run. This is
   wired to a scheduled automation that also pushes the updated
   `data/routes.csv` and `data/students.csv` snapshots to this repo.

## Files

- `data/routes.csv` — 2025-2026 bus routes (bus_number, route_name, zone, stop list)
- `data/students.csv` — sample student registrations
- `src/assign_bus.py` — zone-based bus assignment engine
- `src/rfid_scanner.py` — boarding scan simulator / verification logic
- `src/nightly_update.py` — nightly reassignment + data refresh entrypoint

## Zone matching

Assignment is zone-based: each route in `routes.csv` covers one or more
zones. A student's `zone` field (set at registration) is matched to the
route whose zone list contains it. If no exact zone match is found, the
closest route by same-school zone prefix is used and the assignment is
marked `status: pending` for manual confirmation by the transportation
office.

## Running locally

```bash
python3 src/assign_bus.py         # reassign all students from data/students.csv + routes.csv
python3 src/rfid_scanner.py S1042 # simulate a boarding scan for student ID S1042
python3 src/nightly_update.py     # full nightly refresh
```
