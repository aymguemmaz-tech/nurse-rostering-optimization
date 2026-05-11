

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple


@dataclass
class Instance:
    
    
    # From SECTION_HORIZON
    h: int = 0                                    # number of days
    
    # From SECTION_SHIFTS
    shifts: List[str] = field(default_factory=list)        # P
    shift_duration: Dict[str, int] = field(default_factory=dict)   # d_p
    forbidden_followups: Dict[str, Set[str]] = field(default_factory=dict)  # I_p
    
    # From SECTION_STAFF
    employees: List[str] = field(default_factory=list)     # E
    max_shifts: Dict[Tuple[str, str], int] = field(default_factory=dict)   # m_{e,p}^max
    max_total_min: Dict[str, int] = field(default_factory=dict)   # t_e^max
    min_total_min: Dict[str, int] = field(default_factory=dict)   # t_e^min
    max_consec: Dict[str, int] = field(default_factory=dict)      # c_e^max
    min_consec: Dict[str, int] = field(default_factory=dict)      # c_e^min
    min_off: Dict[str, int] = field(default_factory=dict)         # r_e^min
    max_weekends: Dict[str, int] = field(default_factory=dict)    # w_e^max
    
    # From SECTION_DAYS_OFF
    days_off: Dict[str, Set[int]] = field(default_factory=dict)   # R_e
    
    # From SECTION_SHIFT_ON_REQUESTS  (positive requests)
    on_requests: Dict[Tuple[str, int, str], int] = field(default_factory=dict)   # q_{e,j,p}
    
    # From SECTION_SHIFT_OFF_REQUESTS  (negative requests)
    off_requests: Dict[Tuple[str, int, str], int] = field(default_factory=dict)  # p_{e,j,p}
    
    # From SECTION_COVER
    coverage: Dict[Tuple[int, str], int] = field(default_factory=dict)       # u_{j,p}
    under_penalty: Dict[Tuple[int, str], int] = field(default_factory=dict)  # v_{j,p}^min
    over_penalty: Dict[Tuple[int, str], int] = field(default_factory=dict)   # v_{j,p}^max
    
    @property
    def num_weekends(self) -> int:
        
        return self.h // 7
    
    def summary(self) -> None:
        
        print("=" * 50)
        print(f"Instance summary")
        print("=" * 50)
        print(f"Horizon h         = {self.h} days  ({self.num_weekends} weekends)")
        print(f"Shift types |P|   = {len(self.shifts)}  ->  {self.shifts}")
        print(f"Employees |E|     = {len(self.employees)}")
        print(f"Days off          = {sum(len(s) for s in self.days_off.values())} entries")
        print(f"Positive requests = {len(self.on_requests)}")
        print(f"Negative requests = {len(self.off_requests)}")
        print(f"Coverage entries  = {len(self.coverage)}")
        print("=" * 50)


def parse_instance(path: str) -> Instance:
    
    
    instance = Instance()
    
    # Step 1 — Read the file
    with open(path, "r") as f:
        lines = f.readlines()
    
    # Step 2 — Clean lines: strip whitespace, remove comments and empty lines
    cleaned = []
    for line in lines:
        line = line.strip()
        if line == "" or line.startswith("#"):
            continue
        cleaned.append(line)
    
    # Step 3 — Split into sections
    sections = {}
    current_section = None
    for line in cleaned:
        if line.startswith("SECTION_"):
            current_section = line
            sections[current_section] = []
        else:
            if current_section is None:
                raise ValueError(f"Found data line before any SECTION_ header: {line}")
            sections[current_section].append(line)
    
    # Step 4 — Parse each section into the Instance object
    
    # SECTION_HORIZON
    instance.h = int(sections["SECTION_HORIZON"][0])
    
    # SECTION_SHIFTS
    for line in sections["SECTION_SHIFTS"]:
        parts = line.split(",")
        shift_id = parts[0]
        duration = int(parts[1])
        forbidden_str = parts[2]
        instance.shifts.append(shift_id)
        instance.shift_duration[shift_id] = duration
        if forbidden_str == "":
            instance.forbidden_followups[shift_id] = set()
        else:
            instance.forbidden_followups[shift_id] = set(forbidden_str.split("|"))
    
    # SECTION_STAFF
    for line in sections["SECTION_STAFF"]:
        parts = line.split(",")
        emp_id = parts[0]
        instance.employees.append(emp_id)
        instance.max_total_min[emp_id] = int(parts[2])
        instance.min_total_min[emp_id] = int(parts[3])
        instance.max_consec[emp_id]    = int(parts[4])
        instance.min_consec[emp_id]    = int(parts[5])
        instance.min_off[emp_id]       = int(parts[6])
        instance.max_weekends[emp_id]  = int(parts[7])
        for piece in parts[1].split("|"):
            shift_id, max_value = piece.split("=")
            instance.max_shifts[(emp_id, shift_id)] = int(max_value)
    
    # SECTION_DAYS_OFF
    for line in sections["SECTION_DAYS_OFF"]:
        parts = line.split(",")
        emp_id = parts[0]
        instance.days_off[emp_id] = {int(d) for d in parts[1:]}
    
    # SECTION_SHIFT_ON_REQUESTS
    for line in sections["SECTION_SHIFT_ON_REQUESTS"]:
        parts = line.split(",")
        instance.on_requests[(parts[0], int(parts[1]), parts[2])] = int(parts[3])
    
    # SECTION_SHIFT_OFF_REQUESTS
    for line in sections["SECTION_SHIFT_OFF_REQUESTS"]:
        parts = line.split(",")
        instance.off_requests[(parts[0], int(parts[1]), parts[2])] = int(parts[3])
    
    # SECTION_COVER
    for line in sections["SECTION_COVER"]:
        parts = line.split(",")
        day = int(parts[0])
        shift_id = parts[1]
        instance.coverage[(day, shift_id)]      = int(parts[2])
        instance.under_penalty[(day, shift_id)] = int(parts[3])
        instance.over_penalty[(day, shift_id)]  = int(parts[4])
    
    return instance


if __name__ == "__main__":
    import os
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    instance_path = os.path.join(
        script_dir, "..", "Data", "Instances", "Instance1.txt")
    inst = parse_instance(instance_path)
    inst.summary()
    