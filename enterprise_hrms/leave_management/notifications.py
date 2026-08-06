from enterprise_hrms.notifications.utils import create_notification
from enterprise_hrms.accounts.models import User


def notify_leave_applied(leave_request):
    """
    Notifies employee and manager/HR upon leave application.
    """
    # Employee notification
    if leave_request.employee and leave_request.employee.user:
        create_notification(
            recipient=leave_request.employee.user,
            title="Leave Request Applied",
            message=f"Your request for {leave_request.leave_type.name} from {leave_request.start_date} to {leave_request.end_date} ({leave_request.total_days} day(s)) has been submitted."
        )

    # Manager notification
    if leave_request.employee and leave_request.employee.department and leave_request.employee.department.manager:
        manager_user = leave_request.employee.department.manager.user
        if manager_user:
            create_notification(
                recipient=manager_user,
                title="New Leave Request Pending Approval",
                message=f"Leave request from {leave_request.employee.first_name} {leave_request.employee.last_name} for {leave_request.leave_type.name} ({leave_request.start_date} to {leave_request.end_date}) requires your review."
            )


def notify_manager_approved(leave_request):
    """
    Notifies employee and HR upon manager approval.
    """
    if leave_request.employee and leave_request.employee.user:
        create_notification(
            recipient=leave_request.employee.user,
            title="Leave Request Manager Approved",
            message=f"Your leave request for {leave_request.leave_type.name} from {leave_request.start_date} to {leave_request.end_date} was approved by your manager and is pending HR final approval."
        )

    # Notify HR admins
    hr_users = User.objects.filter(role__in=['hr', 'admin'])
    for hr in hr_users:
        create_notification(
            recipient=hr,
            title="Leave Request Pending HR Approval",
            message=f"Leave request for {leave_request.employee.first_name} {leave_request.employee.last_name} was approved by department manager and awaits final HR approval."
        )


def notify_hr_approved(leave_request):
    """
    Notifies employee upon final HR approval.
    """
    if leave_request.employee and leave_request.employee.user:
        create_notification(
            recipient=leave_request.employee.user,
            title="Leave Request Fully Approved",
            message=f"Your leave request for {leave_request.leave_type.name} from {leave_request.start_date} to {leave_request.end_date} has been fully approved by HR."
        )


def notify_leave_rejected(leave_request, reviewer_role="Manager", comments=""):
    """
    Notifies employee when leave is rejected.
    """
    msg = f"Your leave request for {leave_request.leave_type.name} from {leave_request.start_date} to {leave_request.end_date} was rejected by {reviewer_role}."
    if comments:
        msg += f" Comments: {comments}"

    if leave_request.employee and leave_request.employee.user:
        create_notification(
            recipient=leave_request.employee.user,
            title="Leave Request Rejected",
            message=msg
        )


def notify_leave_cancelled(leave_request):
    """
    Notifies employee upon leave cancellation.
    """
    if leave_request.employee and leave_request.employee.user:
        create_notification(
            recipient=leave_request.employee.user,
            title="Leave Request Cancelled",
            message=f"Your leave request for {leave_request.leave_type.name} from {leave_request.start_date} to {leave_request.end_date} has been cancelled."
        )
