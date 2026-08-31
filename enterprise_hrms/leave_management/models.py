from django.db import models
from enterprise_hrms.employees.models import Employee


class LeaveType(models.Model):
    """
    Model representing different types of leave (e.g. Casual Leave, Sick Leave, Earned Leave).
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    annual_quota = models.PositiveIntegerField(default=0)
    is_paid = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Leave Type'
        verbose_name_plural = 'Leave Types'

    def __str__(self):
        return f"{self.name} ({self.code})"


class LeaveBalance(models.Model):
    """
    Model tracking an employee's allocated, used, and remaining leave days for a specific leave type and year.
    """
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_balances')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name='balances')
    allocated_days = models.PositiveIntegerField(default=0)
    used_days = models.PositiveIntegerField(default=0)
    remaining_days = models.IntegerField(default=0)
    year = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('employee', 'leave_type', 'year')
        ordering = ['-year', 'leave_type']
        verbose_name = 'Leave Balance'
        verbose_name_plural = 'Leave Balances'

    def save(self, *args, **kwargs):
        self.remaining_days = self.allocated_days - self.used_days
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee} - {self.leave_type.code} ({self.year}): {self.remaining_days}/{self.allocated_days} remaining"


class LeaveRequest(models.Model):
    """
    Model representing an employee's leave request submission and multi-level approval state.
    """
    STATUS_CHOICES = [
        ('pending_manager', 'Pending Manager Approval'),
        ('pending_hr', 'Pending HR Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name='leave_requests')
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.PositiveIntegerField(default=1)
    reason = models.TextField()
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
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-applied_at']
        verbose_name = 'Leave Request'
        verbose_name_plural = 'Leave Requests'

    def __str__(self):
        return f"{self.employee} - {self.leave_type.code} ({self.status})"
