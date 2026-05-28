import xml.etree.ElementTree as ET
from datetime import datetime, timedelta


def write_ros(schedule, instance, filename):
    """
    Export solved schedule to .ros XML format
    compatible with RosterViewer.
    """

    # =========================================================
    # CREATE ROOT
    # =========================================================

    root = ET.Element("SchedulingPeriod")
    
    # =========================================================
    # DATES
    # =========================================================

    start_date = datetime(2099, 1, 1)
    end_date = start_date + timedelta(days=instance.h - 1)

    start_xml = ET.SubElement(root, "StartDate")
    start_xml.text = start_date.strftime("%Y-%m-%d")

    end_xml = ET.SubElement(root, "EndDate")
    end_xml.text = end_date.strftime("%Y-%m-%d")

    # =========================================================
    # SHIFT TYPES
    # =========================================================

    shift_types = ET.SubElement(root, "ShiftTypes")

    # Example colors
    shift_colors = {
        "D": "Chartreuse",
        "E": "Yellow",
        "L": "Orange"
    }

    shift_times = {
        "D": "6:0",
        "E": "14:0",
        "L": "22:0"
    }

    for shift in instance.shifts:

        shift_xml = ET.SubElement(
            shift_types,
            "Shift",
            ID=shift
        )

        color = ET.SubElement(shift_xml, "Color")
        color.text = shift_colors.get(shift, "Gray")

        start = ET.SubElement(shift_xml, "StartTime")
        start.text = shift_times.get(shift, "6:0")

        duration = ET.SubElement(shift_xml, "Duration")
        duration.text = "480"

    # =========================================================
    # CONTRACTS
    # =========================================================

    contracts_xml = ET.SubElement(root, "Contracts")

    # Global contract
    all_contract = ET.SubElement(
        contracts_xml,
        "Contract",
        ID="All"
    )

    min_rest = ET.SubElement(
        all_contract,
        "MinRestTime",
        label="At least 840 minutes rest after a shift"
    )

    min_rest.text = "840"

    # Individual contracts
    for employee in instance.employees:

        contract = ET.SubElement(
            contracts_xml,
            "Contract",
            ID=employee
        )

        max_seq = ET.SubElement(
            contract,
            "MaxSeq",
            label="Max 5 consecutive shifts",
            value="5",
            shift="$"
        )

        min_seq = ET.SubElement(
            contract,
            "MinSeq",
            label="Min 2 consecutive shifts",
            value="2",
            shift="$"
        )

        valid = ET.SubElement(
            contract,
            "ValidShifts"
        )

        valid.set(
            "shift",
            ",".join(instance.shifts)
        )

    # =========================================================
    # EMPLOYEES
    # =========================================================

    employees_xml = ET.SubElement(root, "Employees")

    for employee in instance.employees:

        emp_xml = ET.SubElement(
            employees_xml,
            "Employee",
            ID=employee
        )

        contract1 = ET.SubElement(emp_xml, "ContractID")
        contract1.text = "All"

        contract2 = ET.SubElement(emp_xml, "ContractID")
        contract2.text = employee

    # =========================================================
    # FIXED ASSIGNMENTS
    # =========================================================

    fixed_xml = ET.SubElement(root, "FixedAssignments")

    for employee in instance.employees:

        for day in range(instance.h):

            shift = schedule[employee][day]

            # skip OFF days
            if shift == "OFF":
                continue

            employee_xml = ET.SubElement(
                fixed_xml,
                "Employee"
            )

            emp_id = ET.SubElement(
                employee_xml,
                "EmployeeID"
            )

            emp_id.text = employee

            assign = ET.SubElement(
                employee_xml,
                "Assign"
            )

            shift_xml = ET.SubElement(
                assign,
                "Shift"
            )

            shift_xml.text = shift

            day_xml = ET.SubElement(
                assign,
                "Day"
            )

            day_xml.text = str(day)

    # =========================================================
    # EMPTY REQUEST SECTIONS
    # =========================================================

    ET.SubElement(root, "ShiftOffRequests")
    ET.SubElement(root, "ShiftOnRequests")
    ET.SubElement(root, "CoverRequirements")

    # =========================================================
    # SAVE FILE
    # =========================================================

    tree = ET.ElementTree(root)

    tree.write(
    filename,
    encoding="utf-8",
    xml_declaration=True
    )

    print("solution.ros created!")
