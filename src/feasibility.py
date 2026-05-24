"""
Simple feasibility checker for a nurse roster.

This file checks whether a finished schedule respects the 10 hard constraints
from model.py.  It is intentionally written in a simple style so it is easy to
explain in a report or presentation.
"""

import argparse
import csv
from dataclasses import dataclass, field

from parser import Instance, parse_instance


OFF = {"", ".", "-", "OFF", "off", "Off", None}


@dataclass
class FeasibilityReport:
    """Stores the result of the feasibility check."""

    is_feasible: bool = True
    violations: list[tuple[str, str]] = field(default_factory=list)
    coverage_deltas: list[tuple[int, str, int, int, int, int]] = field(default_factory=list)

    def add(self, constraint: str, message: str) -> None:
        self.is_feasible = False
        self.violations.append((constraint, message))


def check_feasibility(
    instance: Instance,
    schedule: dict,
) -> FeasibilityReport:
    """
    Check all hard constraints C1-C10.

    schedule format:
        {
            "A": {0: "D", 1: "OFF", 2: "D"},
            "B": {0: "OFF", 1: "D", 2: "D"},
        }

    Coverage differences are only reported because model.py allows
    shortage/surplus variables y_under and y_over.
    """

    report = FeasibilityReport()
    roster = normalize_schedule(instance, schedule, report)

    for e in instance.employees:
        # C1: one employee can work at most one shift per day.
        for j in range(instance.h):
            if len(roster[e][j]) > 1:
                report.add("C1", f"{e} works more than one shift on day {j}")

        # C2: forbidden shift sequence from one day to the next.
        for j in range(instance.h - 1):
            today = first_shift(roster[e][j])
            tomorrow = first_shift(roster[e][j + 1])
            if today and tomorrow in instance.forbidden_followups[today]:
                report.add("C2", f"{e}: {tomorrow} cannot follow {today} on day {j + 1}")

        # C3: maximum number of times each shift type can be assigned.
        for p in instance.shifts:
            count = sum(p in roster[e][j] for j in range(instance.h))
            maximum = instance.max_shifts[(e, p)]
            if count > maximum:
                report.add("C3", f"{e} works shift {p} {count} times, max {maximum}")

        # C4: total working time must be between min and max.
        total_minutes = sum(
            instance.shift_duration[p]
            for j in range(instance.h)
            for p in roster[e][j]
        )
        if total_minutes < instance.min_total_min[e]:
            report.add("C4", f"{e} works {total_minutes} minutes, below minimum")
        if total_minutes > instance.max_total_min[e]:
            report.add("C4", f"{e} works {total_minutes} minutes, above maximum")

        # C5-C7: consecutive work/off rules.
        for start, length, is_work in consecutive_blocks(instance, roster, e):
            end = start + length - 1
            touches_border = start == 0 or end == instance.h - 1

            # C5: maximum consecutive working days.
            if is_work and length > instance.max_consec[e]:
                report.add("C5", f"{e} works {length} days in a row, max {instance.max_consec[e]}")

            # C6: minimum consecutive working days.
            # Border blocks are ignored to match the formulation in model.py.
            if is_work and not touches_border and length < instance.min_consec[e]:
                report.add("C6", f"{e} works only {length} day(s) from day {start} to {end}")

            # C7: minimum consecutive days off.
            # Border blocks are ignored to match the formulation in model.py.
            if not is_work and not touches_border and length < instance.min_off[e]:
                report.add("C7", f"{e} has only {length} day(s) off from day {start} to {end}")

        # C8: maximum number of worked weekends.
        worked_weekends = 0
        for w in range(instance.num_weekends):
            saturday = 7 * w + 5
            sunday = 7 * w + 6
            if works(roster, e, saturday) or works(roster, e, sunday):
                worked_weekends += 1
        if worked_weekends > instance.max_weekends[e]:
            report.add("C8", f"{e} works {worked_weekends} weekends, max {instance.max_weekends[e]}")

        # C9: requested days off must be respected.
        for j in instance.days_off.get(e, set()):
            if works(roster, e, j):
                report.add("C9", f"{e} works on requested day off {j}")

    # C10: compare assigned staff with required coverage for every day/shift.
    for j in range(instance.h):
        for p in instance.shifts:
            assigned = sum(p in roster[e][j] for e in instance.employees)
            required = instance.coverage[(j, p)]
            shortage = max(0, required - assigned)
            surplus = max(0, assigned - required)
            report.coverage_deltas.append((j, p, required, assigned, shortage, surplus))

    return report


def normalize_schedule(instance: Instance, schedule: dict, report: FeasibilityReport) -> dict:
    """
    Convert the schedule into one standard shape:
        roster[employee][day] = list of shifts
    OFF days become an empty list.
    """

    roster = {}
    for e in instance.employees:
        if e not in schedule:
            report.add("INPUT", f"missing employee {e} in schedule")
            roster[e] = {j: [] for j in range(instance.h)}
            continue

        roster[e] = {}
        for j in range(instance.h):
            value = get_day_value(schedule[e], j)
            shifts = to_shift_list(value)

            for p in shifts:
                if p not in instance.shifts:
                    report.add("INPUT", f"unknown shift {p} for {e} on day {j}")

            roster[e][j] = [p for p in shifts if p in instance.shifts]

    return roster


def get_day_value(employee_schedule, day: int):
    """Read one day from either a dict schedule or a list schedule."""

    if isinstance(employee_schedule, dict):
        return employee_schedule.get(day, employee_schedule.get(str(day), "OFF"))
    if isinstance(employee_schedule, list):
        return employee_schedule[day] if day < len(employee_schedule) else "OFF"
    return "OFF"


def to_shift_list(value) -> list[str]:
    """Convert one schedule cell into a list of shifts."""

    if is_off(value):
        return []
    if isinstance(value, str):
        return [
            item.strip()
            for item in value.replace("|", ",").replace(";", ",").split(",")
            if item.strip() and not is_off(item.strip())
        ]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if not is_off(item)]
    return [str(value)]


def is_off(value) -> bool:
    """Return True if a cell means the employee is not working."""

    try:
        return value in OFF
    except TypeError:
        return False


def first_shift(shifts: list[str]):
    """Return the shift if there is exactly one shift, otherwise None."""

    return shifts[0] if len(shifts) == 1 else None


def works(roster: dict, employee: str, day: int) -> bool:
    """Return True if the employee works at least one shift on that day."""

    return len(roster[employee][day]) > 0


def consecutive_blocks(instance: Instance, roster: dict, employee: str):
    """
    Split an employee schedule into blocks of work days and off days.

    Example:
        Work, Work, Off, Off, Work
        gives blocks: 2 work days, 2 off days, 1 work day.
    """

    start = 0
    current = works(roster, employee, 0)

    for j in range(1, instance.h):
        new_value = works(roster, employee, j)
        if new_value != current:
            yield start, j - start, current
            start = j
            current = new_value

    yield start, instance.h - start, current


def load_schedule_csv(path: str) -> dict:
    """
    Load a schedule from CSV.

    Expected simple format:
        employee,0,1,2,3
        A,D,OFF,D,D
        B,OFF,D,D,OFF
    """

    with open(path, newline="") as file:
        rows = list(csv.reader(file))

    schedule = {}
    for row in rows[1:]:
        employee = row[0].strip()
        schedule[employee] = {
            day: shift.strip()
            for day, shift in enumerate(row[1:])
        }
    return schedule


def print_report(report: FeasibilityReport) -> None:
    """Print the result in a readable way."""

    if report.is_feasible:
        print("Schedule is feasible.")
    else:
        print("Schedule is NOT feasible.")

    for constraint, message in report.violations:
        print(f"{constraint}: {message}")

    differences = [
        delta for delta in report.coverage_deltas
        if delta[4] > 0 or delta[5] > 0
    ]
    if differences:
        print("\nCoverage differences:")
        for day, shift, required, assigned, shortage, surplus in differences:
            print(
                f"day {day}, shift {shift}: required={required}, "
                f"assigned={assigned}, shortage={shortage}, surplus={surplus}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Check schedule feasibility.")
    parser.add_argument("instance", help="path to the instance .txt file")
    parser.add_argument("schedule", help="path to the schedule CSV file")
    args = parser.parse_args()

    instance = parse_instance(args.instance)
    schedule = load_schedule_csv(args.schedule)
    report = check_feasibility(instance, schedule)
    print_report(report)

    return 0 if report.is_feasible else 1


if __name__ == "__main__":
    raise SystemExit(main())
