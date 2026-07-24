import os
import django
import random
import datetime
from decimal import Decimal

# Configure Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'enterprise_hrms.settings')
django.setup()

from enterprise_hrms.accounts.models import User
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.departments.models import Department
from enterprise_hrms.attendance.models import Attendance
from enterprise_hrms.leave_management.models import LeaveRequest
from enterprise_hrms.payroll.models import Payroll
from enterprise_hrms.audit_logs.models import AuditLog

def seed():
    print("Clearing old records...")
    Payroll.objects.all().delete()
    LeaveRequest.objects.all().delete()
    Attendance.objects.all().delete()
    Employee.objects.all().delete()
    Department.objects.all().delete()
    User.objects.exclude(is_superuser=True).delete()

    print("Creating core users...")
    # Admin User
    admin_user, _ = User.objects.get_or_create(
        email="admin@hrms.com",
        defaults={
            "username": "admin",
            "role": "admin",
            "phone": "5550101"
        }
    )
    admin_user.set_password("Password123!")
    admin_user.save()

    # HR User
    hr_user, _ = User.objects.get_or_create(
        email="hr@hrms.com",
        defaults={
            "username": "hr_manager",
            "role": "hr",
            "phone": "5550202"
        }
    )
    hr_user.set_password("Password123!")
    hr_user.save()

    print("Creating departments...")
    depts = [
        {"name": "Engineering", "code": "ENG", "desc": "Software engineering and development"},
        {"name": "Human Resources", "code": "HR", "desc": "HR administration and recruitment"},
        {"name": "Sales & Business", "code": "SAL", "desc": "Client relations and revenue generation"},
        {"name": "Marketing", "code": "MKT", "desc": "Product marketing and advertising"},
    ]
    dept_objs = []
    for d in depts:
        obj, _ = Department.objects.get_or_create(
            code=d["code"],
            defaults={"name": d["name"], "description": d["desc"]}
        )
        dept_objs.append(obj)

    first_names = [
        "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
        "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
        "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
        "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
        "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle"
    ]
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
        "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
        "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young",
        "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores"
    ]
    designations = {
        "ENG": ["Software Engineer", "Senior Dev", "QA Engineer", "DevOps Engineer", "Frontend Developer"],
        "HR": ["HR Generalist", "Recruiter", "HR Analyst", "Compensation Specialist"],
        "SAL": ["Sales Specialist", "Account Executive", "Business Analyst", "Sales Manager"],
        "MKT": ["Marketing Lead", "Content Creator", "SEO Specialist", "Social Media Coordinator"]
    }

    print("Generating 40 employee records...")
    employees = []
    for i in range(40):
        fn = first_names[i]
        ln = last_names[i]
        emp_id = f"EMP{100 + i}"
        email = f"{fn.lower()}.{ln.lower()}@hrms.com"
        phone = f"9876543{i:03d}"
        
        # Determine department & designation
        dept = random.choice(dept_objs)
        desig = random.choice(designations[dept.code])
        
        # Base Salary
        salary = Decimal(random.randint(3000, 11000))
        
        # User Account
        user = User.objects.create(
            username=f"{fn.lower()}_{ln.lower()}",
            email=email,
            phone=phone,
            role="employee"
        )
        user.set_password("Password123!")
        user.save()

        # Employee Profile
        emp = Employee.objects.create(
            employee_id=emp_id,
            first_name=fn,
            last_name=ln,
            email=email,
            phone=phone,
            dob=datetime.date(random.randint(1980, 2002), random.randint(1, 12), random.randint(1, 28)),
            gender=random.choice(["male", "female"]),
            department=dept,
            designation=desig,
            salary=salary,
            joining_date=datetime.date(random.randint(2020, 2025), random.randint(1, 12), random.randint(1, 28)),
            status="active",
            user=user
        )
        employees.append(emp)

    # Set department managers
    print("Setting department managers...")
    for idx, dept in enumerate(dept_objs):
        # Pick one employee from that department to be manager
        candidates = [e for e in employees if e.department == dept]
        if candidates:
            dept.manager = candidates[0]
            dept.save()

    print("Generating check-in logs (Attendance)...")
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    
    for emp in employees:
        # Today
        Attendance.objects.create(
            employee=emp,
            date=today,
            check_in=datetime.time(9, random.randint(0, 15), 0),
            check_out=datetime.time(17, random.randint(0, 30), 0) if random.random() > 0.1 else None,
            status="present" if random.random() > 0.05 else "late"
        )
        # Yesterday
        Attendance.objects.create(
            employee=emp,
            date=yesterday,
            check_in=datetime.time(8, random.randint(45, 59), 0),
            check_out=datetime.time(17, random.randint(0, 15), 0),
            status="present"
        )

    print("Generating leave requests...")
    leave_types = ['sick', 'casual', 'annual', 'unpaid']
    statuses = ['approved', 'rejected', 'pending_manager']
    
    for emp in random.sample(employees, 15):
        start = datetime.date(2026, 7, random.randint(10, 20))
        end = start + datetime.timedelta(days=random.randint(1, 5))
        
        LeaveRequest.objects.create(
            employee=emp,
            leave_type=random.choice(leave_types),
            reason="Family matter / health checkup",
            start_date=start,
            end_date=end,
            status=random.choice(statuses)
        )

    print("Generating payroll summaries...")
    for emp in random.sample(employees, 20):
        basic = emp.salary
        allowances = basic * Decimal("0.10")
        deductions = Decimal("0.00")
        net = basic + allowances - deductions
        
        Payroll.objects.create(
            employee=emp,
            month=6,
            year=2026,
            basic_salary=basic,
            allowances=allowances,
            deductions=deductions,
            net_salary=net,
            status="paid"
        )

    print("Creating audit logs...")
    AuditLog.objects.create(
        user=admin_user,
        action="Database Seeded",
        description="Seeding system populated 40 initial employee records.",
        ip_address="127.0.0.1"
    )

    print("--------------------------------------------------")
    print("Database seeding completed successfully!")
    print(f"Created Admin Account: admin@hrms.com  / Password123!")
    print(f"Created HR Account:    hr@hrms.com     / Password123!")
    print(f"Created 40 Employees (emails: first.last@hrms.com / Password123!)")
    print("--------------------------------------------------")

if __name__ == "__main__":
    seed()
