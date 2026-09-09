from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Exists, OuterRef, Subquery, Count, Q, F, FloatField, ExpressionWrapper, Prefetch
from django.utils import timezone
from .models import Employee, Task, PerformanceRating, Project
from enterprise_hrms.payroll.models import Payroll
from enterprise_hrms.leave_management.models import LeaveRequest
from .serializers import EmployeeSerializer
from enterprise_hrms.api.permissions import IsOwnerOrAdminOrHR, IsAdminOrHR
from .services import EmployeeService

class EmployeeViewSet(viewsets.ModelViewSet):
    """
    ViewSet to manage employee profiles.
    Admin/HR have full access. Employees can only view/retrieve their own profile.
    """
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdminOrHR]
    filterset_fields = ['department', 'gender', 'status']
    search_fields = ['first_name', 'last_name', 'email', 'employee_id']
    ordering_fields = ['joining_date', 'employee_id']
    ordering = ['employee_id']

    def get_queryset(self):
        user = self.request.user
        queryset = Employee.objects.select_related('department', 'user')
        if user.is_superuser or user.role in ['admin', 'hr']:
            return queryset.all()
        # Employees can only access their own profile
        try:
            return queryset.filter(user=user)
        except Exception:
            return Employee.objects.none()

    def create(self, request, *args, **kwargs):
        # Only Admin or HR can create employees
        if not (request.user.is_superuser or request.user.role in ['admin', 'hr']):
            return Response(
                {"success": False, "message": "Only Admin or HR can register new employees."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Only Admin or HR can delete employees
        if not (request.user.is_superuser or request.user.role in ['admin', 'hr']):
            return Response(
                {"success": False, "message": "Only Admin or HR can delete employees."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        EmployeeService.create_employee(serializer, self.request)

    def perform_update(self, serializer):
        EmployeeService.update_employee(serializer, self.request)

    def perform_destroy(self, instance):
        EmployeeService.delete_employee(instance, self.request)

    @action(detail=False, methods=['get'])
    def no_attendance(self, request):
        employees = Employee.objects.filter(attendances__isnull=True).values('id', 'first_name', 'last_name', 'employee_id')
        return Response(list(employees))

    @action(detail=False, methods=['get'])
    def pending_leave(self, request):
        pending_leaves = LeaveRequest.objects.filter(employee=OuterRef('pk'), status__in=['pending_manager', 'pending_hr'])
        employees = Employee.objects.annotate(has_pending_leave=Exists(pending_leaves)).filter(has_pending_leave=True).values('id', 'first_name', 'last_name')
        return Response(list(employees))

    @action(detail=False, methods=['get'])
    def latest_salary(self, request):
        latest_payroll = Payroll.objects.filter(employee=OuterRef('pk')).order_by('-year', '-month')
        employees = Employee.objects.annotate(latest_salary=Subquery(latest_payroll.values('net_salary')[:1])).values('id', 'first_name', 'last_name', 'latest_salary')
        return Response(list(employees))

    @action(detail=False, methods=['get'])
    def latest_performance(self, request):
        latest_rating = PerformanceRating.objects.filter(employee=OuterRef('pk')).order_by('-review_date')
        employees = Employee.objects.annotate(latest_rating=Subquery(latest_rating.values('rating')[:1])).values('id', 'first_name', 'last_name', 'latest_rating')
        return Response(list(employees))

    @action(detail=False, methods=['get'])
    def overdue_tasks(self, request):
        overdue = Task.objects.filter(employee=OuterRef('pk'), is_completed=False, due_date__lt=timezone.now().date())
        employees = Employee.objects.annotate(has_overdue=Exists(overdue)).filter(has_overdue=True).values('id', 'first_name', 'last_name')
        return Response(list(employees))

    @action(detail=False, methods=['get'])
    def complex_analytics(self, request):
        # Optimized API returning: Employee, Department, Current Salary, Attendance %, Leave Count, Performance Rating, Active Projects
        latest_payroll = Payroll.objects.filter(employee=OuterRef('pk')).order_by('-year', '-month')
        latest_rating = PerformanceRating.objects.filter(employee=OuterRef('pk')).order_by('-review_date')
        active_projects_prefetch = Prefetch('projects', queryset=Project.objects.filter(is_active=True), to_attr='active_projects_list')

        employees = Employee.objects.select_related('department').prefetch_related(active_projects_prefetch).annotate(
            latest_salary=Subquery(latest_payroll.values('net_salary')[:1]),
            latest_rating=Subquery(latest_rating.values('rating')[:1]),
            leave_count=Count('leave_requests', distinct=True),
            total_attendances=Count('attendances', distinct=True),
            present_attendances=Count('attendances', filter=Q(attendances__status='present'), distinct=True),
        ).annotate(
            attendance_pct=ExpressionWrapper(F('present_attendances') * 100.0 / F('total_attendances'), output_field=FloatField())
        )

        data = []
        for emp in employees:
            data.append({
                'employee_id': emp.employee_id,
                'name': f"{emp.first_name} {emp.last_name}",
                'department': emp.department.name if emp.department else None,
                'current_salary': emp.latest_salary,
                'attendance_percent': round(emp.attendance_pct, 2) if emp.attendance_pct is not None else 0.0,
                'leave_count': emp.leave_count,
                'performance_rating': emp.latest_rating,
                'active_projects': [p.name for p in emp.active_projects_list]
            })

        return Response(data)