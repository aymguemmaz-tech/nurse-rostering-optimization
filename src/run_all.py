"""
Task C — Test harness
Runs the nurse rostering solver on all 24 benchmark instances
and saves the results to Results/results.csv.

Usage:
    python src/run_all.py
"""

import os
import csv
import time

from parser import parse_instance
from Solver import solve


# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
INSTANCES_DIR  = os.path.join(SCRIPT_DIR, "..", "Data", "Instances")
RESULTS_DIR    = os.path.join(SCRIPT_DIR, "..", "Results")
OUTPUT_CSV     = os.path.join(RESULTS_DIR, "results.csv")

# How many seconds CPLEX is allowed to spend on each instance.
# Small instances solve in seconds; large ones may hit this limit.
TIME_LIMIT = 120   # seconds


def main():
    # Make sure the Results folder exists
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Collect all instance .txt files, sorted by instance number
    instance_files = sorted(
        [f for f in os.listdir(INSTANCES_DIR) if f.endswith(".txt")],
        key=lambda name: int(name.replace("Instance", "").replace(".txt", ""))
    )

    print(f"Found {len(instance_files)} instances to solve.")
    print(f"Time limit per instance: {TIME_LIMIT}s")
    print(f"Results will be saved to: {OUTPUT_CSV}")
    print("=" * 60)

    # Open the CSV file for writing
    with open(OUTPUT_CSV, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)

        # Write the header row
        writer.writerow(["instance", "employees", "days", "shifts",
                         "status", "objective", "solve_time_s"])

        # Loop through every instance
        for filename in instance_files:
            instance_path = os.path.join(INSTANCES_DIR, filename)
            instance_name = filename.replace(".txt", "")  # e.g. "Instance1"

            print(f"\n[{instance_name}] Parsing...", end=" ", flush=True)

            try:
                instance = parse_instance(instance_path)
                print(f"{len(instance.employees)} employees, "
                      f"{instance.h} days, "
                      f"{len(instance.shifts)} shift types.")

                print(f"[{instance_name}] Solving (limit={TIME_LIMIT}s)...",
                      end=" ", flush=True)

                start = time.time()
                result = solve(instance, time_limit=TIME_LIMIT)
                elapsed = time.time() - start

                print(f"Done in {elapsed:.1f}s  |  "
                      f"Status: {result['status']}  |  "
                      f"Objective: {result['objective']}")

                # Write this instance's result as a row in the CSV
                writer.writerow([
                    instance_name,
                    len(instance.employees),
                    instance.h,
                    len(instance.shifts),
                    result["status"],
                    result["objective"],
                    f"{result['solve_time']:.2f}"
                ])

            except Exception as e:
                # If something goes wrong, log the error and continue
                print(f"ERROR — {e}")
                writer.writerow([instance_name, "?", "?", "?",
                                 f"ERROR: {e}", None, None])

    print("\n" + "=" * 60)
    print(f"All done! Results saved to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
