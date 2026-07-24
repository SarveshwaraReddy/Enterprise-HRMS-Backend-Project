from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import LeaveRequest
from .serializers import LeaveRequestSerializer
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.api.permissions import IsOwnerOrAdminOrHR, IsAdminOrHR
from enterprise_hrms.audit_logs.utils import log_action
from enterprise_hrms.notifications.utils import create_notification

class LeaveRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet to manage Leave Requests.
    Supports standard CRUD and workflow transitions for Manager and HR approvals.
    """
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdminOrHR]
    filterset_fields = ['employee', 'leave_type', 'status']
    search_fields = ['employee__first_name', 'employee__last_name', 'status', 'reason']
    ordering_fields = ['applied_at', 'start_date']
    ordering = ['-applied_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role in ['admin', 'hr']:
            return LeaveRequest.objects.all()
        # Employee can see their own requests, and if they manage a department, their department's requests.
        try:
            employee = user.employee_profile
            managed_depts = employee.managed_departments.all()
            if managed_depts.exists():
                from django.db.models import Q
                return LeaveRequest.objects.filter(
                    Q(employee=employee) | Q(employee__department__in=managed_depts)
                )
            return LeaveRequest.objects.filter(employee=employee)
        except Employee.DoesNotExist:
            return LeaveRequest.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == 'employee' and not user.is_superuser:
            # Force employee field to logged-in user's profile
            try:
                employee = user.employee_profile
                leave_req = serializer.save(employee=employee, status='pending_manager')
            except Employee.DoesNotExist:
                raise ValueError("Employee profile not found for this user.")
        else:
            leave_req = serializer.save()
            
        # Log and notify
        log_action(
            user=user,
            action="Leave Created",
            description=f"Leave request created for employee: {leave_req.employee.first_name} {leave_req.employee.last_name} ({leave_req.start_date} to {leave_req.end_date})",
            request=self.request
        )
        
        # Notify employee
        create_notification(
            recipient=leave_req.employee.user,
            title="Leave Request Applied",
            message=f"Your request for {leave_req.get_leave_type_display()} from {leave_req.start_date} to {leave_req.end_date} has been submitted."
        )

    @action(detail=True, methods=['post'], url_path='manager-approve')
    def manager_approve(self, request, pk=None):
        """
        Manager approval step:
        - Transition status to pending_hr or rejected.
        - Restricted to Admin, HR, or the department manager of the employee.
        """
        leave_req = self.get_object()
        user = request.user
        
        # Check permissions: user is admin, hr, or manager of this employee's department
        is_manager = False
        try:
            user_employee = user.employee_profile
            # Check if user_employee is the manager of the department
            if leave_req.employee.department and leave_req.employee.department.manager == user_employee:
                is_manager = True
        except Employee.DoesNotExist:
            pass
            
        if not (user.is_superuser or user.role in ['admin', 'hr'] or is_manager):
            return Response(
                {"success": False, "message": "You do not have permission to perform manager approval for this leave request."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        decision = request.data.get('status') # 'approve' or 'reject'
        comments = request.data.get('comments', '')
        
        if decision not in ['approve', 'reject']:
            return Response(
                {"success": False, "message": "Valid 'status' parameter ('approve' or 'reject') is required in body."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            approver = user.employee_profile
        except Employee.DoesNotExist:
            approver = None
            
        leave_req.manager_comments = comments
        leave_req.manager_approved_by = approver
        
        if decision == 'approve':
            leave_req.status = 'pending_hr'
            msg = "Leave request approved by manager, pending HR final approval."
        else:
            leave_req.status = 'rejected'
            msg = "Leave request rejected by manager."
            
        leave_req.save()
        
        # Log & Notify
        log_action(
            user=user,
            action="Leave Approval",
            description=f"Manager review completed for Leave ID {leave_req.id}: {msg}",
            request=request
        )
        
        create_notification(
            recipient=leave_req.employee.user,
            title="Leave Request Updated (Manager Review)",
            message=msg
        )
        
        return Response({
            "success": True,
            "message": msg,
            "data": LeaveRequestSerializer(leave_req).data
        })

    @action(detail=True, methods=['post'], url_path='hr-approve')
    def hr_approve(self, request, pk=None):
        """
        HR approval step (final):
        - Transition status to approved or rejected.
        - Restricted to Admin and HR.
        """
        leave_req = self.get_object()
        user = request.user
        
        if not (user.is_superuser or user.role in ['admin', 'hr']):
            return Response(
                {"success": False, "message": "Only Admin or HR can perform final HR approval."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        decision = request.data.get('status') # 'approve' or 'reject'
        comments = request.data.get('comments', '')
        
        if decision not in ['approve', 'reject']:
            return Response(
                {"success": False, "message": "Valid 'status' parameter ('approve' or 'reject') is required in body."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            approver = user.employee_profile
        except Employee.DoesNotExist:
            approver = None
            
        leave_req.hr_comments = comments
        leave_req.hr_approved_by = approver
        
        if decision == 'approve':
            leave_req.status = 'approved'
            msg = "Leave request fully approved by HR."
        else:
            leave_req.status = 'rejected'
            msg = "Leave request rejected by HR."
            
        leave_req.save()
        
        # Log & Notify
        log_action(
            user=user,
            action="Leave Approval",
            description=f"HR final review completed for Leave ID {leave_req.id}: {msg}",
            request=request
        )
        
        create_notification(
            recipient=leave_req.employee.user,
            title="Leave Request Finalized",
            message=msg
        )
        
        return Response({
            "success": True,
            "message": msg,
            "data": LeaveRequestSerializer(leave_req).data
        })
