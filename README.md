# Nurse Rostering Optimization

An Integer Linear Programming (ILP) model for the nurse rostering problem,
solved with IBM CPLEX. Group project for the *Optimization Fundamentals*
course in the EUNICE IT4SSM program at Poznań University of Technology.

## Problem

Given a set of nurses, a planning horizon (in days), and a set of shift types,
build a schedule that:
- satisfies the hard constraints (at most one shift per day, forbidden shift
  sequences, bounded working time, max/min consecutive working days, minimum
  days off, weekend limits, requested days off, shift coverage);
- minimizes the soft-constraint penalties (unfulfilled employee requests,
  understaffing, overstaffing).

## Repository structure

```
├── Data/
│   ├── Instances/      # 24 benchmark instance files (.txt + .ros)
│   └── Solutions/      # generated solutions (.ros)
├── src/
│   ├── parser.py       # reads an instance file into an Instance object
│   ├── model.py        # builds the ILP (variables, 10 hard constraints, objective)
│   ├── Solver.py       # solves the model with CPLEX and extracts the schedule
│   ├── feasibility.py  # independently re-checks all 10 hard constraints
│   ├── ros_writer.py   # exports a schedule to .ros format for RosterViewer
│   └── run_all.py      # runs the solver over all 24 instances
└── Results/            # solver outputs (results.csv, *_schedule.csv, *.ros)
```

## Mandatory functions (project brief)

| Required function                  | Location                                   |
|------------------------------------|--------------------------------------------|
| Read an instance from a text file  | `parse_instance` in `parser.py`            |
| Build a feasible schedule          | `build_model` + `solve` (`model.py`, `Solver.py`) |
| Compute the value of a solution    | objective value returned by `solve`        |
| Check if a solution is feasible    | `feasibility.py`                           |
| Save a solution to a `.ros` file   | `ros_writer.py`                            |

## Tech stack

- Python 3.12
- PuLP (modelling layer)
- IBM ILOG CPLEX 22.1.2 (solver, academic edition), called via `pulp.CPLEX_CMD`

## How to run

1. Install the Python dependency:
   ```
   pip install pulp
   ```
2. Install IBM CPLEX (academic edition) and set the path to the CPLEX
   executable in `src/Solver.py` (`cplex_path`).
3. Solve all 24 instances:
   ```
   python src/run_all.py
   ```
   Results are written to `Results/results.csv` and one
   `Results/InstanceN_schedule.csv` file per solved instance.
4. Check feasibility of the generated schedules:
   ```
   python src/feasibility.py
   ```
5. Export schedules to `.ros` for RosterViewer:
   ```
   python src/ros_writer.py
   ```

## Authors

Group project — see the report for detailed individual contributions.

- Aymen Charef Eddine Guemmaz
- Daffa Ahmad Rivaldi
- Belhiba Fahd
- Wiktoria Król
- Piotr Ciborowski
