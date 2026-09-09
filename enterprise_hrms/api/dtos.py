from dataclasses import dataclass
from typing import Optional

@dataclass
class LeaveApprovalDTO:
    """DTO for handling leave approval logic."""
    leave_id: int
    decision: str
    comments: str
    approver_profile: object  # Should be Employee profile
    request_obj: object
    
@dataclass
class AttendanceSummaryDTO:
    """DTO for formatting attendance summary."""
    employee_id: int
    employee_name: str
    month: int
    year: int
    total_days_logged: int
    breakdown: dict
