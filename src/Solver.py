import os
import pulp
from parser import parse_instance, Instance
from model import build_model
from ros_writer import write_ros


def solve(instance: Instance, time_limit: int = 500):
    """
    Build and solve the ILP model for the given instance using PuLP + CPLEX Academic.

    Args:
        instance   : parsed Instance object
        time_limit : max seconds CPLEX can spend solving

    Returns:
        dict with keys: status, objective, solve_time, schedule
        (schedule is None if no feasible solution was found)
    """
    prob, x, t, y_under, y_over = build_model(instance)

    # Use the Academic CPLEX engine directly
    cplex_path = r"C:\Program Files\IBM\ILOG\CPLEX_Studio2212\cplex\bin\x64_win64\cplex.exe"
    
    solver = pulp.CPLEX_CMD(
        path=cplex_path,
        timeLimit=time_limit,
        msg=False          # Set to True to see CPLEX output
    )

    prob.solve(solver)

    status = pulp.LpStatus[prob.status]   # e.g. "Optimal", "Infeasible", "Not Solved"
    
    try:
        obj = pulp.value(prob.objective)
    except:
        obj = None
        
    solve_time = prob.solutionTime

    if prob.status != 1:                  # 1 = Optimal / feasible solution found
        return {
            "status"    : status,
            "objective" : None,
            "solve_time": solve_time,
            "schedule"  : None,
        }

    return {
        "status"    : status,
        "objective" : obj,
        "solve_time": solve_time,
        "schedule"  : extract_schedule(instance, x),
    }


def extract_schedule(instance: Instance, x: dict):
    """
    Read the solved x variables and build a {employee: {day: shift_or_OFF}} table.
    """
    schedule = {}
    for e in instance.employees:
        schedule[e] = {}
        for j in range(instance.h):
            assigned_shift = "OFF"
            for p in instance.shifts:
                val = pulp.value(x[(e, j, p)])
                if val is not None and val > 0.5:   # binary, allow float tolerance
                    assigned_shift = p
                    break
            schedule[e][j] = assigned_shift
    return schedule


def print_schedule(schedule, instance: Instance):
    """Pretty-print the schedule as a grid."""
    days_header = "Emp |" + "".join(f"{j:>3}" for j in range(instance.h))
    print(days_header)
    print("-" * len(days_header))

    for e in instance.employees:
        row = f"{e:>3} |"
        for j in range(instance.h):
            shift = schedule[e][j]
            cell  = "." if shift == "OFF" else shift
            row  += f"{cell:>3}"
        print(row)


if __name__ == "__main__":
    script_dir    = os.path.dirname(os.path.abspath(__file__))
    instance_path = os.path.join(script_dir, "..", "Data", "Instances", "Instance14.txt")

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

        instance_name = os.path.splitext(
            os.path.basename(instance_path)
        )[0]

        output_name = f"{instance_name}_solution.ros"
        
        write_ros(
        result["schedule"],
        instance,
        output_name
        )