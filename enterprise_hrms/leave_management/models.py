from django.db import models
from enterprise_hrms.employees.models import Employee

class LeaveRequest(models.Model):
    LEAVE_TYPE_CHOICES = [
        ('sick', 'Sick Leave'),
        ('casual', 'Casual Leave'),
        ('annual', 'Annual Leave'),
        ('maternity', 'Maternity Leave'),
        ('paternity', 'Paternity Leave'),
        ('unpaid', 'Unpaid Leave'),
    ]

    STATUS_CHOICES = [
        ('pending_manager', 'Pending Manager Approval'),
        ('pending_hr', 'Pending HR Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES)
    reason = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_manager')
    
    manager_comments = models.TextField(blank=True, null=True)
    hr_comments = models.TextField(blank=True, null=True)
    
    manager_approved_by = models.ForeignKey(
        Employee, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='manager_approved_leaves'
    )
    hr_approved_by = models.ForeignKey(
        Employee, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='hr_approved_leaves'
    )
    
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-applied_at']
        indexes = [
            models.Index(fields=['employee', 'status'], name='leave_emp_status_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__gte=models.F('start_date')),
                name='leave_end_date_gte_start_date'
            )
        ]

    def __str__(self):
        return f"{self.employee} - {self.leave_type} ({self.status})"
