import os
from parser import parse_instance, Instance
from model import build_model


def solve(instance: Instance, time_limit: int = 60):
    """
    Build and solve the ILP model for the given instance.
    
    Args:
        instance: parsed Instance object
        time_limit: max seconds CPLEX can spend solving
    
    Returns:
        a dict with keys: status, objective, solve_time, schedule
        (schedule is None if no solution was found)
    """
    m = build_model(instance)
    
    # Set a time limit so CPLEX doesn't run forever on hard instances
    m.parameters.timelimit = time_limit
    
    # Solve
    solution = m.solve(log_output=False)
    
    if solution is None:
        return {
            "status": "infeasible_or_no_solution",
            "objective": None,
            "solve_time": m.solve_details.time,
            "schedule": None,
        }
    
    return {
        "status": str(m.solve_details.status),
        "objective": solution.objective_value,
        "solve_time": m.solve_details.time,
        "schedule": extract_schedule(instance, solution),
    }


def extract_schedule(instance: Instance, solution):
    """
    Read the solved x variables and build a {employee: {day: shift_or_OFF}} table.
    """
    schedule = {}
    for e in instance.employees:
        schedule[e] = {}
        for j in range(instance.h):
            assigned_shift = "OFF"
            for p in instance.shifts:
                # Look up the value CPLEX assigned to x[e, j, p]
                var = solution.get_value(f"x_{e}_{j}_{p}")
                if var > 0.5:  # binary, but allow float tolerance
                    assigned_shift = p
                    break
            schedule[e][j] = assigned_shift
    return schedule


def print_schedule(schedule, instance: Instance):
    """Pretty-print the schedule as a grid."""
    # Header: day numbers
    days_header = "Emp |" + "".join(f"{j:>3}" for j in range(instance.h))
    print(days_header)
    print("-" * len(days_header))
    
    for e in instance.employees:
        row = f"{e:>3} |"
        for j in range(instance.h):
            shift = schedule[e][j]
            cell = "." if shift == "OFF" else shift
            row += f"{cell:>3}"
        print(row)


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    instance_path = os.path.join(
        script_dir, "..", "Data", "Instances", "Instance1.txt"
    )
    
    instance = parse_instance(instance_path)
    print(f"\nSolving {os.path.basename(instance_path)}...")
    print(f"  ({len(instance.employees)} employees, {instance.h} days, "
          f"{len(instance.shifts)} shift types)\n")
    
    result = solve(instance, time_limit=60)
    
    print(f"Status:        {result['status']}")
    print(f"Objective:     {result['objective']}")
    print(f"Solve time:    {result['solve_time']:.2f}s")
    
    if result["schedule"] is not None:
        print("\nSchedule:")
        print_schedule(result["schedule"], instance)