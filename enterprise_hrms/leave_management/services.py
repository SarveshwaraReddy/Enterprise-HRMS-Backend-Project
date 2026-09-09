from django.db import transaction
from .models import LeaveRequest
from enterprise_hrms.audit_logs.utils import log_action
from enterprise_hrms.notifications.utils import create_notification
from enterprise_hrms.api.exceptions import InvalidWorkflowStateError
from enterprise_hrms.api.decorators import audit_action, execution_timing, business_validation
from enterprise_hrms.api.context_managers import BusinessTransaction
from enterprise_hrms.api.dtos import LeaveApprovalDTO
from typing import Tuple

def validate_manager_approval(dto: LeaveApprovalDTO) -> None:
    leave_req = LeaveRequest.objects.get(id=dto.leave_id)
    if leave_req.status != 'pending_manager':
        raise InvalidWorkflowStateError(leave_req.status, 'pending_manager')

def validate_hr_approval(dto: LeaveApprovalDTO) -> None:
    leave_req = LeaveRequest.objects.get(id=dto.leave_id)
    if leave_req.status != 'pending_hr':
        raise InvalidWorkflowStateError(leave_req.status, 'pending_hr')

class LeaveService:
    @staticmethod
    @execution_timing
    @audit_action("Manager Leave Approval")
    @business_validation(validate_manager_approval)
    def process_manager_approval(dto: LeaveApprovalDTO) -> Tuple[LeaveRequest, str]:
        with BusinessTransaction(f"Manager approval for leave {dto.leave_id}"):
            leave_req = LeaveRequest.objects.select_for_update().get(id=dto.leave_id)
            
            leave_req.manager_comments = dto.comments
            leave_req.manager_approved_by = dto.approver_profile
            
            if dto.decision == 'approve':
                leave_req.status = 'pending_hr'
                msg = "Leave request approved by manager, pending HR final approval."
            else:
                leave_req.status = 'rejected'
                msg = "Leave request rejected by manager."
                
            leave_req.save()
            
            create_notification(
                recipient=leave_req.employee.user,
                title="Leave Request Updated (Manager Review)",
                message=msg
            )
            
            return leave_req, msg

    @staticmethod
    @execution_timing
    @audit_action("HR Leave Approval")
    @business_validation(validate_hr_approval)
    def process_hr_approval(dto: LeaveApprovalDTO) -> Tuple[LeaveRequest, str]:
        with BusinessTransaction(f"HR approval for leave {dto.leave_id}"):
            leave_req = LeaveRequest.objects.select_for_update().get(id=dto.leave_id)
            
            leave_req.hr_comments = dto.comments
            leave_req.hr_approved_by = dto.approver_profile
            
            if dto.decision == 'approve':
                leave_req.status = 'approved'
                msg = "Leave request fully approved by HR."
            else:
                leave_req.status = 'rejected'
                msg = "Leave request rejected by HR."
                
            leave_req.save()
            
            create_notification(
                recipient=leave_req.employee.user,
                title="Leave Request Finalized",
                message=msg
            )
            
            return leave_req, msg
