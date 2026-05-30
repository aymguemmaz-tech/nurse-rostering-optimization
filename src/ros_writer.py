"""
.ros writer for RosterViewer (based on Wiktoria's format, extended).

Reads the schedule CSV files the solver produced and converts each into a
.ros file RosterViewer opens directly as an INSTANCE. The solved schedule
is embedded as <FixedAssignments>, and the soft-constraint data
(requests + coverage) is included so RosterViewer computes the same
penalty/objective as the solver.

Usage:
    python src/ros_writer.py
"""

import os
import csv
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from parser import parse_instance, Instance


def write_ros(schedule, instance, filename):
    """
    Export solved schedule to .ros XML format compatible with RosterViewer.
    Schedule is embedded as <FixedAssignments>; soft constraints are
    included so RosterViewer reproduces the objective value.
    """

    # ── Root ──────────────────────────────────────────────────────────────
    root = ET.Element("SchedulingPeriod")

    # ── Dates ─────────────────────────────────────────────────────────────
    start_date = datetime(2099, 1, 1)
    end_date   = start_date + timedelta(days=instance.h - 1)
    ET.SubElement(root, "StartDate").text = start_date.strftime("%Y-%m-%d")
    ET.SubElement(root, "EndDate").text   = end_date.strftime("%Y-%m-%d")

    # ── Shift types ───────────────────────────────────────────────────────
    shift_types = ET.SubElement(root, "ShiftTypes")
    shift_colors = {"D": "Chartreuse", "E": "Yellow", "L": "Orange", "N": "SkyBlue"}
    shift_times  = {"D": "6:0", "E": "14:0", "L": "22:0", "N": "22:0"}

    for shift in instance.shifts:
        shift_xml = ET.SubElement(shift_types, "Shift", ID=shift)
        ET.SubElement(shift_xml, "Color").text     = shift_colors.get(shift, "Gray")
        ET.SubElement(shift_xml, "StartTime").text = shift_times.get(shift, "6:0")
        ET.SubElement(shift_xml, "Duration").text  = str(instance.shift_duration.get(shift, 480))

    # ── Contracts ─────────────────────────────────────────────────────────
    contracts_xml = ET.SubElement(root, "Contracts")
    all_contract = ET.SubElement(contracts_xml, "Contract", ID="All")
    ET.SubElement(all_contract, "MinRestTime",
                  label="At least 840 minutes rest after a shift").text = "840"

    for employee in instance.employees:
        contract = ET.SubElement(contracts_xml, "Contract", ID=employee)
        ET.SubElement(contract, "MaxSeq",
                      label="Max consecutive shifts",
                      value=str(instance.max_consec[employee]), shift="$")
        ET.SubElement(contract, "MinSeq",
                      label="Min consecutive shifts",
                      value=str(instance.min_consec[employee]), shift="$")
        # ValidShifts = only the shift types this employee is allowed to work,
        # i.e. those with a positive MaxShifts limit. A limit of 0 means the
        # shift is forbidden for this employee, so it is left out here.
        allowed = [
            s for s in instance.shifts
            if instance.max_shifts.get((employee, s), 0) > 0
        ]
        if not allowed:                      # fallback: never write an empty list
            allowed = list(instance.shifts)
        valid = ET.SubElement(contract, "ValidShifts")
        valid.set("shift", ",".join(allowed))

    # ── Employees ─────────────────────────────────────────────────────────
    employees_xml = ET.SubElement(root, "Employees")
    for employee in instance.employees:
        emp_xml = ET.SubElement(employees_xml, "Employee", ID=employee)
        # Each employee uses their own contract (which carries their limits
        # and valid shifts). Only one ContractID per employee.
        ET.SubElement(emp_xml, "ContractID").text = employee

    # ── Fixed assignments (the solved schedule) ───────────────────────────
    fixed_xml = ET.SubElement(root, "FixedAssignments")
    for employee in instance.employees:
        for day in range(instance.h):
            shift = schedule.get(employee, {}).get(day, "OFF")
            if shift in ("OFF", "off", "Off", "", ".", "-", None):
                continue
            employee_xml = ET.SubElement(fixed_xml, "Employee")
            ET.SubElement(employee_xml, "EmployeeID").text = employee
            assign = ET.SubElement(employee_xml, "Assign")
            ET.SubElement(assign, "Shift").text = shift
            ET.SubElement(assign, "Day").text   = str(day)

    # ── Shift-OFF requests (negative requests) ────────────────────────────
    # instance.off_requests: {(employee, day, shift): weight}
    shift_off_xml = ET.SubElement(root, "ShiftOffRequests")
    for (employee, day, shift), weight in instance.off_requests.items():
        off = ET.SubElement(shift_off_xml, "ShiftOff", weight=str(weight))
        ET.SubElement(off, "Shift").text      = shift
        ET.SubElement(off, "EmployeeID").text = employee
        ET.SubElement(off, "Day").text        = str(day)

    # ── Shift-ON requests (positive requests) ─────────────────────────────
    # instance.on_requests: {(employee, day, shift): weight}
    shift_on_xml = ET.SubElement(root, "ShiftOnRequests")
    for (employee, day, shift), weight in instance.on_requests.items():
        on = ET.SubElement(shift_on_xml, "ShiftOn", weight=str(weight))
        ET.SubElement(on, "Shift").text      = shift
        ET.SubElement(on, "EmployeeID").text = employee
        ET.SubElement(on, "Day").text        = str(day)

    # ── Cover requirements (staffing needs + penalties) ───────────────────
    # instance.coverage:      {(day, shift): required}
    # instance.under_penalty: {(day, shift): weight}  (shortage cost)
    # instance.over_penalty:  {(day, shift): weight}  (surplus cost)
    cover_xml = ET.SubElement(root, "CoverRequirements")
    # Group by day so each day gets one <DateSpecificCover> block
    days_with_cover = sorted({day for (day, shift) in instance.coverage.keys()})
    for day in days_with_cover:
        date_cover = ET.SubElement(cover_xml, "DateSpecificCover")
        ET.SubElement(date_cover, "Day").text = str(day)
        for shift in instance.shifts:
            key = (day, shift)
            if key not in instance.coverage:
                continue
            required   = instance.coverage[key]
            under_w    = instance.under_penalty.get(key, 0)
            over_w     = instance.over_penalty.get(key, 0)
            cover = ET.SubElement(date_cover, "Cover")
            ET.SubElement(cover, "Shift").text = shift
            ET.SubElement(cover, "Min", weight=str(under_w)).text = str(required)
            ET.SubElement(cover, "Max", weight=str(over_w)).text  = str(required)

    # ── Save ──────────────────────────────────────────────────────────────
    parent = os.path.dirname(filename)
    if parent:
        os.makedirs(parent, exist_ok=True)

    tree = ET.ElementTree(root)
    tree.write(filename, encoding="utf-8", xml_declaration=True)


def load_schedule_csv(path: str) -> dict:
    """Load schedule from CSV produced by run_all.py."""
    schedule = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    if not rows:
        return schedule

    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        employee = row[0].strip()
        schedule[employee] = {
            day_index: shift.strip()
            for day_index, shift in enumerate(row[1:])
        }
    return schedule


def convert_all_results() -> None:
    """Convert every Results/*_schedule.csv into a matching .ros file."""

    script_dir    = os.path.dirname(os.path.abspath(__file__))
    results_dir   = os.path.join(script_dir, "..", "Results")
    instances_dir = os.path.join(script_dir, "..", "Data", "Instances")

    if not os.path.isdir(results_dir):
        print(f"No Results folder found at {results_dir}")
        return

    csv_files = [f for f in os.listdir(results_dir) if f.endswith("_schedule.csv")]

    if not csv_files:
        print("No *_schedule.csv files found in Results/")
        print("Run run_all.py (or Solver.py) first to produce schedules.")
        return

    print(f"Found {len(csv_files)} schedule files to convert.\n")

    for csv_file in csv_files:
        instance_name = csv_file.replace("_schedule.csv", "")
        instance_path = os.path.join(instances_dir, f"{instance_name}.txt")

        if not os.path.exists(instance_path):
            print(f"  [skip] {csv_file} — {instance_name}.txt not found")
            continue

        schedule_path = os.path.join(results_dir, csv_file)
        ros_path      = os.path.join(results_dir, f"{instance_name}.ros")

        try:
            instance = parse_instance(instance_path)
            schedule = load_schedule_csv(schedule_path)
            write_ros(schedule, instance, ros_path)
            print(f"  [ok]   {csv_file} -> {os.path.basename(ros_path)}")
        except Exception as ex:
            print(f"  [err]  {csv_file} — {ex}")

    print("\nDone. In RosterViewer: File -> Open Instance -> select a .ros file.")


if __name__ == "__main__":
    convert_all_results()