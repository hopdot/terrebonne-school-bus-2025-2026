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

## Student ID cards with QR screening

`src/make_id_cards.py` prints one CR80 card per student (300 dpi PNG, plus a
one-card-per-page print sheet) and writes `data/card_registry.csv`.

Each card carries four things and nothing more:

- **RFID card number** — the 8 hex digit UID the bus reader matches on (`0xB920B58A`)
- **Screening QR** — a signed credential, `TPSD1|<student_id>|<uid>|<sig>`
- **Bus pill** — assigned bus, route name, route number
- **Identity block** — name, school, grade, zone

Home address and guardian phone are deliberately never rendered on the card.

The signature is HMAC-SHA256 over the student id and card UID, truncated to 12
hex characters. A scanner therefore rejects a hand-written, copied, or altered
code without any network call. The key comes from the `TPSD_QR_SECRET`
environment variable; **the built-in development key must be replaced before
production use**, since anyone holding it can mint cards:

```bash
export TPSD_QR_SECRET="$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')"
python3 src/make_id_cards.py       # reprint cards under the new key
```

Changing the key invalidates every card already printed, so rotate it between
school years, not mid-term.

### Screening

```bash
# scan the printed QR (photo, gate camera frame, or the PNG itself)
python3 src/qr_screen.py --image cards/S1001_ava-boudreaux.png --bus TPB-101

# type or paste the payload from a handheld scanner
python3 src/qr_screen.py --payload "TPSD1|S1001|B920B58A|e762167f620f" --bus TPB-101

# bus reader tapped the RFID number instead
python3 src/qr_screen.py --rfid 0xB920B58A
```

Results: `CORRECT BUS`, `WRONG BUS` (names the correct bus), `PENDING`,
`INVALID CARD` (bad signature), `UNKNOWN CARD` (valid signature, not enrolled),
`LOOKUP` (no bus supplied, reports the expected bus).

Every scan appends to `data/qr_screening_log.csv` with a UTC timestamp, so a
gate or office can audit who scanned what and when.

`cards/` and `data/card_registry.csv` are gitignored: they contain student
names and live card credentials and should only be stored in a private,
access-controlled location.
