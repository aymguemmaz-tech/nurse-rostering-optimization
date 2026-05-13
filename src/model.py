from docplex.mp.model import Model
from parser import Instance


def build_model(instance: Instance) -> Model:
    
    
    m = Model(name="nurse_rostering")
    
    # --- Decision variables ---
    
    # x_{e,j,p} = 1 if employee e works shift p on day j
    x = {}
    for e in instance.employees:
        for j in range(instance.h):
            for p in instance.shifts:
                x[(e, j, p)] = m.binary_var(name=f"x_{e}_{j}_{p}")
    
    # t_{e,w} = 1 if employee e works at least one day of weekend w
    t = {}
    for e in instance.employees:
        for w in range(instance.num_weekends):
            t[(e, w)] = m.binary_var(name=f"t_{e}_{w}")
    
    # y_under_{j,p} = staff shortage on shift p on day j
    y_under = {}
    for j in range(instance.h):
        for p in instance.shifts:
            y_under[(j, p)] = m.integer_var(lb=0, name=f"y_under_{j}_{p}")
    
    # y_over_{j,p} = staff surplus on shift p on day j
    y_over = {}
    for j in range(instance.h):
        for p in instance.shifts:
            y_over[(j, p)] = m.integer_var(lb=0, name=f"y_over_{j}_{p}")
    
     # --- Constraints ---
    
    before = m.number_of_constraints
    
    # Constraint 1 — at most one shift per employee per day
    for e in instance.employees:
        for j in range(instance.h):
            m.add_constraint(
                m.sum(x[(e, j, p)] for p in instance.shifts) <= 1
            )
    print(f"After C1: +{m.number_of_constraints - before} constraints (total: {m.number_of_constraints})")
    before = m.number_of_constraints
    
    # Constraint 2 — shift sequence incompatibility
    for e in instance.employees:
        for j in range(instance.h - 1):
            for p in instance.shifts:
                for q in instance.forbidden_followups[p]:
                    m.add_constraint(
                        x[(e, j, p)] + x[(e, j+1, q)] <= 1
                    )
    print(f"After C2: +{m.number_of_constraints - before} constraints (total: {m.number_of_constraints})")
    before = m.number_of_constraints
    
    # Constraint 3 — max times each employee works each shift
    for e in instance.employees:
        for p in instance.shifts:
            m.add_constraint(
                m.sum(x[(e, j, p)] for j in range(instance.h)) <= instance.max_shifts[(e, p)]
            )
    print(f"After C3: +{m.number_of_constraints - before} constraints (total: {m.number_of_constraints})")
    before = m.number_of_constraints
    
    # Constraint 4 — bounded total working time
    for e in instance.employees:
        total_minutes = m.sum(
            instance.shift_duration[p] * x[(e, j, p)]
            for j in range(instance.h)
            for p in instance.shifts
        )
        m.add_constraint(total_minutes >= instance.min_total_min[e])
        m.add_constraint(total_minutes <= instance.max_total_min[e])
    print(f"After C4: +{m.number_of_constraints - before} constraints (total: {m.number_of_constraints})")
    before = m.number_of_constraints
    
    # Constraint 5 — max consecutive working days
    for e in instance.employees:
        c_max = instance.max_consec[e]
        for j in range(instance.h - c_max):
            m.add_constraint(
                m.sum(
                    x[(e, k, p)]
                    for k in range(j, j + c_max + 1)
                    for p in instance.shifts
                ) <= c_max
            )
    print(f"After C5: +{m.number_of_constraints - before} constraints (total: {m.number_of_constraints})")
    before = m.number_of_constraints
    
    # Constraint 6 — min consecutive working days
    for e in instance.employees:
        c_min = instance.min_consec[e]
        for s in range(1, c_min):
            for j in range(1, instance.h - s):
                works_before = m.sum(x[(e, j - 1, p)] for p in instance.shifts)
                works_after = m.sum(x[(e, j + s, p)] for p in instance.shifts)
                works_inside = m.sum(
                    x[(e, k, p)]
                    for k in range(j, j + s)
                    for p in instance.shifts
                )
                m.add_constraint(
                    (1 - works_before) + works_inside + (1 - works_after) <= s + 1
                )
    print(f"After C6: +{m.number_of_constraints - before} constraints (total: {m.number_of_constraints})")
    
    # Constraint 7 — min consecutive days off
    for e in instance.employees:
        r_min = instance.min_off[e]                # field name from parser
        for s in range(1, r_min):
            for j in range(1, instance.h - s):
                works_before = m.sum(x[(e, j - 1, p)] for p in instance.shifts)
                works_after = m.sum(x[(e, j + s, p)] for p in instance.shifts)
                off_inside = s - m.sum(
                    x[(e, k, p)]
                    for k in range(j, j + s)
                    for p in instance.shifts
                )
                m.add_constraint(
                    works_before + off_inside + works_after <= s + 1
                )
    print(f"After C7: +{m.number_of_constraints - before} constraints (total: {m.number_of_constraints})")
    before = m.number_of_constraints        
    
    # Constraint 8 — max weekends worked
    
    # Part A: link t_{e,w} to assignment variables
    # If employee works at least one of Sat/Sun of weekend w, then t_{e,w} must be 1.
    # The factor of 2 lets t_{e,w} absorb both days into a single weekend flag.
    for e in instance.employees:
        for w in range(instance.num_weekends):
            saturday = 7 * w + 5
            sunday = 7 * w + 6
            weekend_work = (
                m.sum(x[(e, saturday, p)] for p in instance.shifts)
                + m.sum(x[(e, sunday, p)] for p in instance.shifts)
            )
            m.add_constraint(weekend_work <= 2 * t[(e, w)])
    
    # Part B: limit total weekends worked per employee
    for e in instance.employees:
        m.add_constraint(
            m.sum(t[(e, w)] for w in range(instance.num_weekends))
            <= instance.max_weekends[e]
        )
    print(f"After C8: +{m.number_of_constraints - before} constraints (total: {m.number_of_constraints})")
    before = m.number_of_constraints
            
    # Constraint 9 — requested days off (hard constraint)
    for e in instance.employees:
        for j in instance.days_off[e]:
            m.add_constraint(
                m.sum(x[(e, j, p)] for p in instance.shifts) == 0
            )
    print(f"After C9: +{m.number_of_constraints - before} constraints (total: {m.number_of_constraints})")
    before = m.number_of_constraints
    
    # Constraint 10 — shift coverage with shortage/surplus
    for j in range(instance.h):
        for p in instance.shifts:
            m.add_constraint(
                m.sum(x[(e, j, p)] for e in instance.employees)
                + y_under[(j, p)]
                - y_over[(j, p)]
                == instance.coverage[(j, p)]
            )
    print(f"After C10: +{m.number_of_constraints - before} constraints (total: {m.number_of_constraints})")
            

    return m


if __name__ == "__main__":
    import os
    from parser import parse_instance
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    instance_path = os.path.join(
        script_dir, "..", "Data", "Instances", "Instance1.txt"
    )
    
    instance = parse_instance(instance_path)
    instance.summary()
    
    m = build_model(instance)
    
    print()
    print(f"Total variables in model: {m.number_of_variables}")
    print(f"Total constraints in model: {m.number_of_constraints}")