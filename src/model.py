import pulp
from parser import Instance


def build_model(instance: Instance):
    """
    Build the nurse rostering ILP using PuLP + CBC (free, no size limits).
    Returns the (prob, x, t, y_under, y_over) tuple.
    """

    prob = pulp.LpProblem("nurse_rostering", pulp.LpMinimize)

    # ── Decision variables ────────────────────────────────────────────────────

    # x[e, j, p] = 1 if employee e works shift p on day j
    x = {}
    for e in instance.employees:
        for j in range(instance.h):
            for p in instance.shifts:
                x[(e, j, p)] = pulp.LpVariable(f"x_{e}_{j}_{p}", cat="Binary")

    # t[e, w] = 1 if employee e works at least one day of weekend w
    t = {}
    for e in instance.employees:
        for w in range(instance.num_weekends):
            t[(e, w)] = pulp.LpVariable(f"t_{e}_{w}", cat="Binary")

    # y_under[j, p] = staff shortage on shift p on day j
    y_under = {}
    for j in range(instance.h):
        for p in instance.shifts:
            y_under[(j, p)] = pulp.LpVariable(f"y_under_{j}_{p}", lowBound=0, cat="Integer")

    # y_over[j, p] = staff surplus on shift p on day j
    y_over = {}
    for j in range(instance.h):
        for p in instance.shifts:
            y_over[(j, p)] = pulp.LpVariable(f"y_over_{j}_{p}", lowBound=0, cat="Integer")

    # ── Constraints ───────────────────────────────────────────────────────────

    before = [0]  # mutable counter for logging

    def n_constraints():
        return len(prob.constraints)

    # Constraint 1 — at most one shift per employee per day
    for e in instance.employees:
        for j in range(instance.h):
            prob += (
                pulp.lpSum(x[(e, j, p)] for p in instance.shifts) <= 1,
                f"C1_{e}_{j}"
            )
    print(f"After C1: {n_constraints()} constraints total")

    # Constraint 2 — shift sequence incompatibility
    for e in instance.employees:
        for j in range(instance.h - 1):
            for p in instance.shifts:
                for q in instance.forbidden_followups[p]:
                    prob += (
                        x[(e, j, p)] + x[(e, j + 1, q)] <= 1,
                        f"C2_{e}_{j}_{p}_{q}"
                    )
    print(f"After C2: {n_constraints()} constraints total")

    # Constraint 3 — max times each employee works each shift
    for e in instance.employees:
        for p in instance.shifts:
            prob += (
                pulp.lpSum(x[(e, j, p)] for j in range(instance.h)) <= instance.max_shifts[(e, p)],
                f"C3_{e}_{p}"
            )
    print(f"After C3: {n_constraints()} constraints total")

    # Constraint 4 — bounded total working time
    for e in instance.employees:
        total_minutes = pulp.lpSum(
            instance.shift_duration[p] * x[(e, j, p)]
            for j in range(instance.h)
            for p in instance.shifts
        )
        prob += (total_minutes >= instance.min_total_min[e], f"C4_min_{e}")
        prob += (total_minutes <= instance.max_total_min[e], f"C4_max_{e}")
    print(f"After C4: {n_constraints()} constraints total")

    # Constraint 5 — max consecutive working days
    for e in instance.employees:
        c_max = instance.max_consec[e]
        for j in range(instance.h - c_max):
            prob += (
                pulp.lpSum(
                    x[(e, k, p)]
                    for k in range(j, j + c_max + 1)
                    for p in instance.shifts
                ) <= c_max,
                f"C5_{e}_{j}"
            )
    print(f"After C5: {n_constraints()} constraints total")

    # Constraint 6 — min consecutive working days
    for e in instance.employees:
        c_min = instance.min_consec[e]
        for s in range(1, c_min):
            for j in range(1, instance.h - s):
                works_before = pulp.lpSum(x[(e, j - 1, p)] for p in instance.shifts)
                works_after  = pulp.lpSum(x[(e, j + s, p)] for p in instance.shifts)
                works_inside = pulp.lpSum(
                    x[(e, k, p)]
                    for k in range(j, j + s)
                    for p in instance.shifts
                )
                prob += (
                    (1 - works_before) + works_inside + (1 - works_after) <= s + 1,
                    f"C6_{e}_{s}_{j}"
                )
    print(f"After C6: {n_constraints()} constraints total")

    # Constraint 7 — min consecutive days off
    for e in instance.employees:
        r_min = instance.min_off[e]
        for s in range(1, r_min):
            for j in range(1, instance.h - s):
                works_before = pulp.lpSum(x[(e, j - 1, p)] for p in instance.shifts)
                works_after  = pulp.lpSum(x[(e, j + s, p)] for p in instance.shifts)
                off_inside   = s - pulp.lpSum(
                    x[(e, k, p)]
                    for k in range(j, j + s)
                    for p in instance.shifts
                )
                prob += (
                    works_before + off_inside + works_after <= s + 1,
                    f"C7_{e}_{s}_{j}"
                )
    print(f"After C7: {n_constraints()} constraints total")

    # Constraint 8 — max weekends worked
    for e in instance.employees:
        for w in range(instance.num_weekends):
            saturday = 7 * w + 5
            sunday   = 7 * w + 6
            weekend_work = (
                pulp.lpSum(x[(e, saturday, p)] for p in instance.shifts)
                + pulp.lpSum(x[(e, sunday, p)] for p in instance.shifts)
            )
            prob += (weekend_work <= 2 * t[(e, w)], f"C8a_{e}_{w}")

    for e in instance.employees:
        prob += (
            pulp.lpSum(t[(e, w)] for w in range(instance.num_weekends)) <= instance.max_weekends[e],
            f"C8b_{e}"
        )
    print(f"After C8: {n_constraints()} constraints total")

    # Constraint 9 — requested days off (hard constraint)
    for e in instance.employees:
        for j in instance.days_off[e]:
            prob += (
                pulp.lpSum(x[(e, j, p)] for p in instance.shifts) == 0,
                f"C9_{e}_{j}"
            )
    print(f"After C9: {n_constraints()} constraints total")

    # Constraint 10 — shift coverage with shortage/surplus
    for j in range(instance.h):
        for p in instance.shifts:
            prob += (
                pulp.lpSum(x[(e, j, p)] for e in instance.employees)
                + y_under[(j, p)]
                - y_over[(j, p)]
                == instance.coverage[(j, p)],
                f"C10_{j}_{p}"
            )
    print(f"After C10: {n_constraints()} constraints total")

    # ── Objective: minimise total penalty ────────────────────────────────────

    # Term 1: unsatisfied positive requests (pay if NOT assigned)
    term1 = pulp.lpSum(
        weight * (1 - x[(e, j, p)])
        for (e, j, p), weight in instance.on_requests.items()
    )

    # Term 2: violated negative requests (pay if assigned)
    term2 = pulp.lpSum(
        weight * x[(e, j, p)]
        for (e, j, p), weight in instance.off_requests.items()
    )

    # Term 3: understaffing penalty
    term3 = pulp.lpSum(
        instance.under_penalty[(j, p)] * y_under[(j, p)]
        for j in range(instance.h)
        for p in instance.shifts
    )

    # Term 4: overstaffing penalty
    term4 = pulp.lpSum(
        instance.over_penalty[(j, p)] * y_over[(j, p)]
        for j in range(instance.h)
        for p in instance.shifts
    )

    prob += term1 + term2 + term3 + term4

    return prob, x, t, y_under, y_over


if __name__ == "__main__":
    import os
    from parser import parse_instance

    script_dir    = os.path.dirname(os.path.abspath(__file__))
    instance_path = os.path.join(script_dir, "..", "Data", "Instances", "Instance1.txt")

    instance = parse_instance(instance_path)
    instance.summary()

    prob, x, t, y_under, y_over = build_model(instance)

    print()
    print(f"Total variables in model  : {len(prob.variables())}")
    print(f"Total constraints in model: {len(prob.constraints)}")