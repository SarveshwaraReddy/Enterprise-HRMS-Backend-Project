from rest_framework.exceptions import ValidationError
from django.db.models import Sum

def validate_active_performance_cycle(cycle):
    if cycle.status != 'Active':
        raise ValidationError("This action can only be performed on an active performance cycle.")

def validate_goal_weightage(employee, performance_cycle, new_weightage, exclude_goal_id=None):
    from .models import Goal
    
    goals = Goal.objects.filter(employee=employee, performance_cycle=performance_cycle)
    if exclude_goal_id:
        goals = goals.exclude(id=exclude_goal_id)
        
    current_weightage = goals.aggregate(Sum('weightage'))['weightage__sum'] or 0
    total_weightage = current_weightage + new_weightage
    
    if total_weightage > 100:
        raise ValidationError(f"Total goal weightage cannot exceed 100%. Current weightage is {current_weightage}%.")
