from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.utils import timezone
from django.db.models import Sum
import datetime

from enterprise_hrms.employees.models import Employee
from enterprise_hrms.departments.models import Department
from enterprise_hrms.attendance.models import Attendance
from enterprise_hrms.leave_management.models import LeaveRequest
from enterprise_hrms.payroll.models import Payroll
from enterprise_hrms.api.permissions import IsAdminOrHR

class DashboardView(APIView):
    """
    Dashboard API returning summary statistics for the system.
    Restricted to Admin and HR.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminOrHR]

    def get(self, request):
        today = timezone.localtime().date()
        current_month = today.month
        current_year = today.year
        
        # 1. Total Employees
        total_employees = Employee.objects.count()
        active_employees = Employee.objects.filter(status='active').count()
        
        # 2. Departments
        total_departments = Department.objects.count()
        
        # 3. Attendance Today
        attendance_today = Attendance.objects.filter(date=today, status='present').count()
        
        # 4. Pending Leaves (Pending Manager or Pending HR)
        pending_leaves = LeaveRequest.objects.filter(status__startswith='pending').count()
        
        # 5. Payroll This Month (Sum of Net Salaries generated/paid for current month/year)
        payroll_sum = Payroll.objects.filter(
            month=current_month, 
            year=current_year
        ).aggregate(total=Sum('net_salary'))['total'] or 0.00
        
        # 6. Recent Employees (Last 5 registered)
        recent_queryset = Employee.objects.all().order_by('-joining_date')[:5]
        recent_employees = [
            {
                "id": emp.id,
                "employee_id": emp.employee_id,
                "first_name": emp.first_name,
                "last_name": emp.last_name,
                "designation": emp.designation,
                "joining_date": emp.joining_date.strftime('%Y-%m-%d') if emp.joining_date else None,
                "status": emp.status
            }
            for emp in recent_queryset
        ]
        
        data = {
            "total_employees": total_employees,
            "active_employees": active_employees,
            "departments": total_departments,
            "attendance_today": attendance_today,
            "pending_leaves": pending_leaves,
            "payroll_this_month": round(float(payroll_sum), 2),
            "recent_employees": recent_employees
        }
        
        return Response({
            "success": True,
            "message": "Dashboard data retrieved successfully.",
            "data": data
        })
