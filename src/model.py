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
    
    # Constraint 1 — at most one shift per employee per day
    for e in instance.employees:
        for j in range(instance.h):
            m.add_constraint(
                m.sum(x[(e, j, p)] for p in instance.shifts) <= 1
            )
    
               
    # Constraint 2 — shift sequence incompatibility
   
    for e in instance.employees:
        for j in range(instance.h - 1):
            for p in instance.shifts:
                for q in instance.forbidden_followups[p]:
                    m.add_constraint(
                        x[(e, j, p)] + x[(e, j+1, q)] <= 1
                    )        
    
    # Constraint 3 — max times each employee works each shift
    
    for e in instance.employees:
        for p in instance.shifts:
            m.add_constraint(
                m.sum(x[(e, j, p)] for j in range(instance.h)) <= instance.max_shifts[(e, p)]
            )           
    
                    
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