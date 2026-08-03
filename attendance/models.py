from django.db import models
from django.utils import timezone
from enterprise_hrms.employees.models import Employee

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('half_day', 'Half Day'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField(default=timezone.now)
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')

    class Meta:
        unique_together = ('employee', 'date')
        ordering = ['-date', 'employee']

    def __str__(self):
        return f"{self.employee} - {self.date} ({self.status})"
