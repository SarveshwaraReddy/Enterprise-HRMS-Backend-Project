import datetime
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from enterprise_hrms.employees.models import Employee
from enterprise_hrms.departments.models import Department
from enterprise_hrms.api.permissions import IsOwnerOrAdminOrHR, IsAdminOrHR
from .models import LeaveType, LeaveBalance, LeaveRequest
from .serializers import (
    LeaveTypeSerializer,
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    ApplyLeaveSerializer,
    ApproveRejectSerializer,
    CancelLeaveSerializer
)
from .filters import LeaveRequestFilter
from .permissions import IsLeaveOwnerOrManagerOrHR, IsDepartmentManager, IsHROrAdmin
from .services import (
    apply_leave,
    approve_leave,
    reject_leave,
    final_approve_leave,
    cancel_leave,
    employee_leave_summary,
    get_or_create_leave_balance
)
from .reports import (
    generate_leave_history_pdf,
    generate_annual_leave_register_excel,
    generate_department_leave_summary_excel,
    generate_leave_transactions_csv
)


class LeaveTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Leave Types. CRUD operations restricted to HR/Admin.
    """
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdminOrHR()]
        return [permissions.IsAuthenticated()]


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing Leave Balances.
    """
    serializer_class = LeaveBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['employee', 'year', 'leave_type']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role in ['admin', 'hr']:
            return LeaveBalance.objects.all()
        try:
            employee = user.employee_profile
            return LeaveBalance.objects.filter(employee=employee)
        except Employee.DoesNotExist:
            return LeaveBalance.objects.none()


class LeaveRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Leave Requests, supporting employee submissions,
    multi-level manager & HR approval workflow, leave cancellation, calendar views,
    leave analytics, and report exporters.
    """
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsLeaveOwnerOrManagerOrHR]
    filterset_class = LeaveRequestFilter
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__employee_id', 'reason', 'status']
    ordering_fields = ['applied_at', 'start_date', 'end_date']
    ordering = ['-applied_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role in ['admin', 'hr']:
            return LeaveRequest.objects.all().select_related('employee', 'leave_type', 'employee__department')

        try:
            employee = user.employee_profile
            managed_depts = employee.managed_departments.all()
            if managed_depts.exists():
                return LeaveRequest.objects.filter(
                    Q(employee=employee) | Q(employee__department__in=managed_depts)
                ).select_related('employee', 'leave_type', 'employee__department')
            return LeaveRequest.objects.filter(employee=employee).select_related('employee', 'leave_type', 'employee__department')
        except Employee.DoesNotExist:
            return LeaveRequest.objects.none()

    # --- Employee Endpoints ---

    @action(detail=False, methods=['post'], url_path='apply')
    def apply(self, request):
        """
        POST /api/v1/leaves/apply/
        Employee endpoint to submit a leave request.
        """
        serializer = ApplyLeaveSerializer(data=request.data)
        serializer.is_validate_or_400 = True
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request.user
        try:
            employee = user.employee_profile
        except Employee.DoesNotExist:
            return Response(
                {"success": False, "message": "Employee profile not found for authenticated user."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Resolve LeaveType by ID or Code
        leave_type_val = data['leave_type']
        try:
            if str(leave_type_val).isdigit():
                leave_type = LeaveType.objects.get(id=int(leave_type_val))
            else:
                leave_type = LeaveType.objects.get(code__iexact=leave_type_val)
        except LeaveType.DoesNotExist:
            return Response(
                {"success": False, "message": f"Leave type '{leave_type_val}' not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        is_hr_override = data.get('is_hr_override', False) and (user.is_superuser or user.role in ['admin', 'hr'])

        try:
            leave_req = apply_leave(
                employee=employee,
                leave_type=leave_type,
                start_date=data['start_date'],
                end_date=data['end_date'],
                reason=data['reason'],
                is_hr_override=is_hr_override,
                request=request
            )
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "success": True,
            "message": "Leave request submitted successfully.",
            "data": LeaveRequestSerializer(leave_req).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='my-leaves')
    def my_leaves(self, request):
        """
        GET /api/v1/leaves/my-leaves/
        Retrieves leave history for the logged-in employee.
        """
        user = request.user
        try:
            employee = user.employee_profile
        except Employee.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)

        queryset = LeaveRequest.objects.filter(employee=employee).order_by('-applied_at')
        filtered_qs = self.filter_queryset(queryset)
        page = self.paginate_queryset(filtered_qs)
        if page is not None:
            serializer = LeaveRequestSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = LeaveRequestSerializer(filtered_qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='my-balance')
    def my_balance(self, request):
        """
        GET /api/v1/leaves/my-balance/
        Retrieves leave balance summary for the logged-in employee.
        """
        user = request.user
        try:
            employee = user.employee_profile
        except Employee.DoesNotExist:
            return Response(
                {"success": False, "message": "Employee profile not found."},
                status=status.HTTP_400_BAD_REQUEST
            )

        year_param = request.query_params.get('year')
        year = int(year_param) if year_param and year_param.isdigit() else datetime.date.today().year

        summary = employee_leave_summary(employee, year=year)
        return Response({"success": True, "data": summary})

    @action(detail=True, methods=['put', 'post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """
        PUT/POST /api/v1/leaves/{id}/cancel/
        Cancels a leave request and restores leave balance if previously approved.
        """
        leave_req = self.get_object()
        user = request.user
        try:
            employee = user.employee_profile
        except Employee.DoesNotExist:
            employee = None

        # Permission check: Owner or HR/Admin
        if not (user.is_superuser or user.role in ['admin', 'hr'] or leave_req.employee == employee):
            return Response(
                {"success": False, "message": "You do not have permission to cancel this leave request."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = CancelLeaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get('reason', '')

        try:
            updated_req = cancel_leave(leave_req, user=user, reason=reason, request=request)
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "success": True,
            "message": "Leave request cancelled successfully.",
            "data": LeaveRequestSerializer(updated_req).data
        })

    # --- Manager Endpoints ---

    @action(detail=False, methods=['get'], url_path='pending')
    def pending(self, request):
        """
        GET /api/v1/leaves/pending/
        Lists leave requests pending manager review for manager's department.
        """
        user = request.user
        if user.is_superuser or user.role in ['admin', 'hr']:
            qs = LeaveRequest.objects.filter(status__startswith='pending')
        else:
            try:
                employee = user.employee_profile
                managed_depts = employee.managed_departments.all()
                if not managed_depts.exists():
                    return Response([], status=status.HTTP_200_OK)
                qs = LeaveRequest.objects.filter(
                    employee__department__in=managed_depts,
                    status='pending_manager'
                )
            except Employee.DoesNotExist:
                return Response([], status=status.HTTP_200_OK)

        filtered_qs = self.filter_queryset(qs)
        page = self.paginate_queryset(filtered_qs)
        if page is not None:
            serializer = LeaveRequestSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = LeaveRequestSerializer(filtered_qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['put', 'post'], url_path='approve')
    def approve(self, request, pk=None):
        """
        PUT/POST /api/v1/leaves/{id}/approve/
        Manager approval step.
        """
        leave_req = self.get_object()
        user = request.user

        is_manager = False
        try:
            user_emp = user.employee_profile
            if leave_req.employee.department and leave_req.employee.department.manager == user_emp:
                is_manager = True
        except Employee.DoesNotExist:
            pass

        if not (user.is_superuser or user.role in ['admin', 'hr'] or is_manager):
            return Response(
                {"success": False, "message": "You do not have permission to perform manager approval on this leave request."},
                status=status.HTTP_403_FORBIDDEN
            )

        comments = request.data.get('comments', '')
        try:
            updated_req = approve_leave(leave_req, approver_user=user, comments=comments, request=request)
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "success": True,
            "message": "Leave request approved by manager, pending HR final approval.",
            "data": LeaveRequestSerializer(updated_req).data
        })

    @action(detail=True, methods=['put', 'post'], url_path='reject')
    def reject(self, request, pk=None):
        """
        PUT/POST /api/v1/leaves/{id}/reject/
        Rejects a leave request.
        """
        leave_req = self.get_object()
        user = request.user

        is_manager = False
        try:
            user_emp = user.employee_profile
            if leave_req.employee.department and leave_req.employee.department.manager == user_emp:
                is_manager = True
        except Employee.DoesNotExist:
            pass

        if not (user.is_superuser or user.role in ['admin', 'hr'] or is_manager):
            return Response(
                {"success": False, "message": "You do not have permission to reject this leave request."},
                status=status.HTTP_403_FORBIDDEN
            )

        comments = request.data.get('comments', '')
        try:
            updated_req = reject_leave(leave_req, reviewer_user=user, comments=comments, request=request)
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "success": True,
            "message": "Leave request rejected.",
            "data": LeaveRequestSerializer(updated_req).data
        })

    # --- HR/Admin Endpoints ---

    @action(detail=True, methods=['put', 'post'], url_path='final-approve')
    def final_approve(self, request, pk=None):
        """
        PUT/POST /api/v1/leaves/{id}/final-approve/
        HR final approval step.
        """
        leave_req = self.get_object()
        user = request.user

        if not (user.is_superuser or user.role in ['admin', 'hr']):
            return Response(
                {"success": False, "message": "Only Admin or HR can perform final HR approval."},
                status=status.HTTP_403_FORBIDDEN
            )

        comments = request.data.get('comments', '')
        try:
            updated_req = final_approve_leave(leave_req, hr_user=user, comments=comments, request=request)
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "success": True,
            "message": "Leave request fully approved by HR.",
            "data": LeaveRequestSerializer(updated_req).data
        })

    # --- Leave Calendar APIs ---

    @action(detail=False, methods=['get'], url_path='calendar/monthly')
    def monthly_calendar(self, request):
        """
        GET /api/v1/leaves/calendar/monthly/?month=7&year=2026
        Returns approved & pending leaves for the given month and year.
        """
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        today = datetime.date.today()
        m = int(month) if month and month.isdigit() else today.month
        y = int(year) if year and year.isdigit() else today.year

        queryset = self.get_queryset().filter(
            start_date__year=y,
            start_date__month=m,
            status__in=['approved', 'pending_manager', 'pending_hr']
        )
        serializer = LeaveRequestSerializer(queryset, many=True)
        return Response({
            "month": m,
            "year": y,
            "total_leaves": queryset.count(),
            "leaves": serializer.data
        })

    @action(detail=False, methods=['get'], url_path='calendar/team')
    def team_calendar(self, request):
        """
        GET /api/v1/leaves/calendar/team/?department_id=X
        Returns upcoming/active leaves for team members in the user's department.
        """
        user = request.user
        try:
            emp = user.employee_profile
            dept = emp.department
        except Employee.DoesNotExist:
            dept = None

        dept_id = request.query_params.get('department_id')
        if dept_id and dept_id.isdigit():
            try:
                dept = Department.objects.get(id=int(dept_id))
            except Department.DoesNotExist:
                return Response({"success": False, "message": "Department not found."}, status=status.HTTP_404_NOT_FOUND)

        if not dept:
            qs = LeaveRequest.objects.none()
        else:
            qs = LeaveRequest.objects.filter(
                employee__department=dept,
                status__in=['approved', 'pending_manager', 'pending_hr']
            )

        serializer = LeaveRequestSerializer(qs, many=True)
        return Response({
            "department": dept.name if dept else None,
            "leaves": serializer.data
        })

    @action(detail=False, methods=['get'], url_path='calendar/upcoming')
    def upcoming_leaves(self, request):
        """
        GET /api/v1/leaves/calendar/upcoming/
        Returns leaves starting today or in the future.
        """
        today = datetime.date.today()
        qs = self.get_queryset().filter(
            start_date__gte=today,
            status__in=['approved', 'pending_manager', 'pending_hr']
        ).order_by('start_date')[:20]

        serializer = LeaveRequestSerializer(qs, many=True)
        return Response({"count": len(qs), "upcoming_leaves": serializer.data})

    @action(detail=False, methods=['get'], url_path='calendar/currently-on-leave')
    def currently_on_leave(self, request):
        """
        GET /api/v1/leaves/calendar/currently-on-leave/
        Returns list of employees who are on approved leave today.
        """
        today = datetime.date.today()
        qs = self.get_queryset().filter(
            start_date__lte=today,
            end_date__gte=today,
            status='approved'
        )

        serializer = LeaveRequestSerializer(qs, many=True)
        return Response({"date": str(today), "count": len(qs), "on_leave": serializer.data})

    # --- Leave Analytics API ---

    @action(detail=False, methods=['get'], url_path='analytics')
    def analytics(self, request):
        """
        GET /api/v1/leaves/analytics/
        Returns leave statistics, most used leave types, monthly trends, and balance stats.
        Restricted to Admin/HR.
        """
        if not (request.user.is_superuser or request.user.role in ['admin', 'hr']):
            return Response(
                {"success": False, "message": "Only Admin or HR can view leave analytics."},
                status=status.HTTP_403_FORBIDDEN
            )

        year_param = request.query_params.get('year')
        year = int(year_param) if year_param and year_param.isdigit() else datetime.date.today().year

        # 1. Most Used Leave Type
        most_used = LeaveRequest.objects.filter(
            status='approved', start_date__year=year
        ).values(
            'leave_type__name', 'leave_type__code'
        ).annotate(
            total_requests=Count('id'),
            total_days=Sum('total_days')
        ).order_by('-total_days')

        # 2. Monthly Leave Trends
        monthly_trends = []
        for m in range(1, 13):
            approved_count = LeaveRequest.objects.filter(
                status='approved', start_date__year=year, start_date__month=m
            ).count()
            days_sum = LeaveRequest.objects.filter(
                status='approved', start_date__year=year, start_date__month=m
            ).aggregate(total=Sum('total_days'))['total'] or 0

            monthly_trends.append({
                "month": m,
                "month_name": datetime.date(year, m, 1).strftime('%B'),
                "approved_requests": approved_count,
                "total_days": days_sum
            })

        # 3. Average Leave Days per Employee
        active_emp_count = Employee.objects.filter(status='active').count() or 1
        total_approved_days = LeaveRequest.objects.filter(
            status='approved', start_date__year=year
        ).aggregate(total=Sum('total_days'))['total'] or 0

        avg_leave_per_employee = round(total_approved_days / active_emp_count, 2)

        # 4. Employees with Zero Remaining Leave Balance
        zero_balance_objs = LeaveBalance.objects.filter(year=year, remaining_days__lte=0).select_related('employee', 'leave_type')
        zero_balance_list = [
            {
                "employee_id": b.employee.employee_id,
                "employee_name": f"{b.employee.first_name} {b.employee.last_name}",
                "leave_type": b.leave_type.name,
                "allocated_days": b.allocated_days,
                "used_days": b.used_days,
                "remaining_days": b.remaining_days
            }
            for b in zero_balance_objs
        ]

        return Response({
            "year": year,
            "most_used_leave_types": list(most_used),
            "monthly_leave_trends": monthly_trends,
            "average_leave_per_employee": avg_leave_per_employee,
            "employees_with_zero_balance_count": len(zero_balance_list),
            "employees_with_zero_balance": zero_balance_list
        })

    # --- Leave Reports Export API ---

    @action(detail=False, methods=['get'], url_path='report')
    def export_report(self, request):
        """
        GET /api/v1/leaves/report/?report_format=pdf|excel|csv&report_type=history|annual_register|dept_summary|transactions
        Export leave reports in PDF, Excel, or CSV format.
        Restricted to Admin/HR.
        """
        if not (request.user.is_superuser or request.user.role in ['admin', 'hr']):
            return Response(
                {"success": False, "message": "Only Admin or HR can export leave reports."},
                status=status.HTTP_403_FORBIDDEN
            )

        fmt = request.query_params.get('report_format', 'pdf').lower()
        report_type = request.query_params.get('report_type', 'history').lower()
        qs = self.filter_queryset(self.get_queryset())

        if fmt == 'pdf':
            return generate_leave_history_pdf(qs)
        elif fmt in ['excel', 'xlsx']:
            if report_type == 'dept_summary':
                return generate_department_leave_summary_excel()
            return generate_annual_leave_register_excel()
        elif fmt == 'csv':
            return generate_leave_transactions_csv(qs)

        return Response({"success": False, "message": "Invalid report_format. Use 'pdf', 'excel', or 'csv'."}, status=status.HTTP_400_BAD_REQUEST)
