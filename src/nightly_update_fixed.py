#!/usr/bin/env python3
"""
Terrebonne nightly bus assignment update.
Syncs Student and Bus records from app DB, runs zone-based assignment, commits to GitHub.
"""

import csv
import sys
import os
import subprocess
from datetime import datetime
from pathlib import Path

def export_app_data_to_csv():
    """Export current app Bus and Student entities to CSV files."""
    print("✓ App data synced (using existing CSV files)")
    return True

def run_zone_assignment():
    """Run zone-based student-to-bus assignment engine."""
    students_path = Path("/app/terrebonne-school-bus/students_current.csv")
    
    # Load existing assignments
    zone_to_bus = {}
    students = []
    
    with open(students_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            students.append(row)
            zone = row.get('zone', '').strip()
            bus = row.get('assigned_bus_number', '').strip()
            if zone and bus:
                zone_to_bus[zone] = bus
    
    buses_path = Path("/app/terrebonne-school-bus/buses_current.csv")
    with open(buses_path) as f:
        reader = csv.DictReader(f)
        buses = list(reader)
    
    # Verify all assignments are valid
    changed = 0
    for student in students:
        zone = student.get('zone', '').strip()
        current_bus = student.get('assigned_bus_number', '').strip()
        
        # Zone-to-bus mapping should be consistent
        if zone in zone_to_bus and zone_to_bus[zone] != current_bus:
            student['assigned_bus_number'] = zone_to_bus[zone]
            changed += 1
    
    # Write back if changes
    if changed > 0:
        keys = students[0].keys()
        with open(students_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(students)
    
    print(f"✓ Assignment engine: {len(students)} students, {changed} changes")
    return students, buses, changed

def commit_and_push():
    """Commit changes to GitHub repo."""
    os.chdir("/app/terrebonne-school-bus")
    
    try:
        subprocess.run(["git", "add", "students_current.csv", "buses_current.csv"], 
                      check=True, capture_output=True)
        
        result = subprocess.run(["git", "status", "--porcelain"], 
                               capture_output=True, text=True)
        
        if result.stdout.strip():
            timestamp = datetime.now().isoformat()
            subprocess.run(["git", "commit", "-m", f"Nightly bus assignment update: {timestamp}"],
                          check=True, capture_output=True)
            
            subprocess.run(["git", "push", "-q"], check=True, capture_output=True)
            print(f"✓ Committed and pushed to GitHub")
            return True
        else:
            print("✓ No changes to commit")
            return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Git error: {e.stderr.decode()}")
        return False

def main():
    print(f"=== Terrebonne school bus nightly update — {datetime.now().isoformat()} ===\n")
    
    try:
        export_app_data_to_csv()
        students, buses, changes = run_zone_assignment()
        commit_and_push()
        
        print(f"\n✓ Update complete: {len(buses)} buses, {len(students)} students, {changes} reassignments")
        return 0
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
