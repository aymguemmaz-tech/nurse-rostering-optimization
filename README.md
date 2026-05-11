# Nurse Rostering Optimization

An Integer Linear Programming (ILP) model for the nurse rostering problem,
solved with IBM CPLEX. Group project for the *Optimization Fundamentals*
course in the EUNICE IT4SSM program at Poznań University of Technology.

## Problem

Given a set of nurses, a planning horizon (in days), and a set of shift types,
build a schedule that:
- satisfies hard constraints (max consecutive working days, minimum days off,
  shift incompatibilities, weekend limits, ...)
- minimizes soft-constraint violations (unfulfilled employee requests,
  understaffing, overstaffing).

## Repository structure

├── Data/
│   ├── Instances/      # 24 benchmark instance files (.txt + .ros)
│   └── Solutions/      # generated solutions (.ros)
├── src/
│   ├── parser.py       # parses instance files into Python data structures
│   └── model.py        # builds the CPLEX ILP model
└── Results/            # solver outputs and analysis

## Tech stack

- Python 3.12
- IBM ILOG CPLEX 22.x (via `docplex`)

## Status

🚧 In progress — model implementation phase.

## Authors

Group project — see report for individual contributions.

Aymen Charef Eddine Guemmaz · IT4SSM 2026