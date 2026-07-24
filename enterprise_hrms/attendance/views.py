from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Count
import datetime

from .models import Attendance
from .serializers import AttendanceSerializer
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.api.permissions import IsOwnerOrAdminOrHR, IsAdminOrHR

class AttendanceViewSet(viewsets.ModelViewSet):
    """
    ViewSet to manage Employee Attendance.
    """
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdminOrHR]
    filterset_fields = ['employee', 'date', 'status']
    search_fields = ['employee__first_name', 'employee__last_name', 'status']
    ordering_fields = ['date']
    ordering = ['-date']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role in ['admin', 'hr']:
            return Attendance.objects.all()
        # Employee can only see their own attendance
        try:
            employee = user.employee_profile
            return Attendance.objects.filter(employee=employee)
        except Employee.DoesNotExist:
            return Attendance.objects.none()

    @action(detail=False, methods=['post'], url_path='mark')
    def mark(self, request):
        """
        Mark attendance for the logged-in employee:
        - If first call today: Create check_in.
        - If second call today: Update check_out.
        """
        user = request.user
        try:
            employee = user.employee_profile
        except Employee.DoesNotExist:
            return Response(
                {"success": False, "message": "Only users linked to an Employee profile can mark attendance."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        today = timezone.localtime().date()
        now_time = timezone.localtime().time()
        
        attendance, created = Attendance.objects.get_or_create(
            employee=employee,
            date=today,
            defaults={
                'check_in': now_time,
                'status': 'present'
            }
        )
        
        if not created:
            attendance.check_out = now_time
            attendance.save()
            return Response({
                "success": True,
                "message": "Checked out successfully.",
                "data": AttendanceSerializer(attendance).data
            })
            
        return Response({
            "success": True,
            "message": "Checked in successfully.",
            "data": AttendanceSerializer(attendance).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='monthly')
    def monthly(self, request):
        """
        Get monthly attendance summary.
        Params: month (1-12), year, and employee_id (optional, restricted to Admin/HR).
        """
        user = request.user
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        employee_id = request.query_params.get('employee_id')
        
        if not month or not year:
            return Response(
                {"success": False, "message": "Parameters 'month' and 'year' are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            month = int(month)
            year = int(year)
        except ValueError:
            return Response(
                {"success": False, "message": "Invalid format for 'month' or 'year'."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Determine target employee
        if user.role in ['admin', 'hr'] or user.is_superuser:
            if employee_id:
                try:
                    employee = Employee.objects.get(id=employee_id)
                except Employee.DoesNotExist:
                    return Response(
                        {"success": False, "message": "Employee not found."},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                return Response(
                    {"success": False, "message": "Parameter 'employee_id' is required for Admin/HR."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            try:
                employee = user.employee_profile
            except Employee.DoesNotExist:
                return Response(
                    {"success": False, "message": "Employee profile not found."},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        records = Attendance.objects.filter(
            employee=employee,
            date__month=month,
            date__year=year
        )
        
        counts = records.values('status').annotate(count=Count('status'))
        breakdown = {choice[0]: 0 for choice in Attendance.STATUS_CHOICES}
        for item in counts:
            breakdown[item['status']] = item['count']
            
        data = {
            "employee_id": employee.id,
            "employee_name": f"{employee.first_name} {employee.last_name}",
            "month": month,
            "year": year,
            "total_days_logged": records.count(),
            "breakdown": breakdown
        }
        
        return Response({"success": True, "data": data})
