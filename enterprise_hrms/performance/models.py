from django.db import models
from enterprise_hrms.employees.models import Employee

class PerformanceCycle(models.Model):
    STATUS_CHOICES = (
        ('Draft', 'Draft'),
        ('Active', 'Active'),
        ('Closed', 'Closed'),
    )

    cycle_name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.cycle_name

class Goal(models.Model):
    GOAL_TYPES = (
        ('KPI', 'KPI'),
        ('OKR', 'OKR'),
        ('Project Goal', 'Project Goal'),
        ('Learning Goal', 'Learning Goal'),
    )
    STATUS_CHOICES = (
        ('Not Started', 'Not Started'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='goals')
    performance_cycle = models.ForeignKey(PerformanceCycle, on_delete=models.CASCADE, related_name='goals')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    goal_type = models.CharField(max_length=50, choices=GOAL_TYPES)
    weightage = models.DecimalField(max_digits=5, decimal_places=2, help_text="Weightage in percentage")
    target_value = models.CharField(max_length=255, blank=True, null=True)
    achieved_value = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Not Started')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class PerformanceReview(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Self Submitted', 'Self Submitted'),
        ('Manager Reviewed', 'Manager Reviewed'),
        ('HR Approved', 'HR Approved'),
        ('Completed', 'Completed'),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='performance_reviews')
    performance_cycle = models.ForeignKey(PerformanceCycle, on_delete=models.CASCADE, related_name='reviews')
    self_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    manager_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    final_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    self_comments = models.TextField(blank=True, null=True)
    manager_comments = models.TextField(blank=True, null=True)
    hr_comments = models.TextField(blank=True, null=True)
    promotion_recommended = models.BooleanField(default=False)
    increment_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')
    review_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Review for {self.employee} - {self.performance_cycle}"
