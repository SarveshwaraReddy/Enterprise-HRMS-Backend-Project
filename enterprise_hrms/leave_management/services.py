from django.db import transaction
from .models import LeaveRequest
from enterprise_hrms.audit_logs.utils import log_action
from enterprise_hrms.notifications.utils import create_notification

class LeaveService:
    @staticmethod
    @transaction.atomic
    def process_manager_approval(leave_id, decision, comments, approver_profile, request_obj):
        # select_for_update locks the row until the transaction is complete to prevent race conditions
        leave_req = LeaveRequest.objects.select_for_update().get(id=leave_id)
        
        if leave_req.status != 'pending_manager':
            raise ValueError("Leave request is not in a valid state for manager approval.")

        leave_req.manager_comments = comments
        leave_req.manager_approved_by = approver_profile
        
        if decision == 'approve':
            leave_req.status = 'pending_hr'
            msg = "Leave request approved by manager, pending HR final approval."
        else:
            leave_req.status = 'rejected'
            msg = "Leave request rejected by manager."
            
        leave_req.save()
        
        log_action(
            user=request_obj.user,
            action="Leave Approval",
            description=f"Manager review completed for Leave ID {leave_req.id}: {msg}",
            request=request_obj
        )
        
        create_notification(
            recipient=leave_req.employee.user,
            title="Leave Request Updated (Manager Review)",
            message=msg
        )
        
        return leave_req, msg

    @staticmethod
    @transaction.atomic
    def process_hr_approval(leave_id, decision, comments, approver_profile, request_obj):
        # select_for_update prevents concurrent HR approvals
        leave_req = LeaveRequest.objects.select_for_update().get(id=leave_id)
        
        if leave_req.status != 'pending_hr':
            raise ValueError("Leave request is not in a valid state for HR approval.")

        leave_req.hr_comments = comments
        leave_req.hr_approved_by = approver_profile
        
        if decision == 'approve':
            leave_req.status = 'approved'
            msg = "Leave request fully approved by HR."
        else:
            leave_req.status = 'rejected'
            msg = "Leave request rejected by HR."
            
        leave_req.save()
        
        log_action(
            user=request_obj.user,
            action="Leave Approval",
            description=f"HR final review completed for Leave ID {leave_req.id}: {msg}",
            request=request_obj
        )
        
        create_notification(
            recipient=leave_req.employee.user,
            title="Leave Request Finalized",
            message=msg
        )
        
        return leave_req, msg
