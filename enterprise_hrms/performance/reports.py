from django.db.models import Avg, Count, Q
from .models import PerformanceReview, Goal

def generate_employee_performance_report(employee, performance_cycle):
    goals = Goal.objects.filter(employee=employee, performance_cycle=performance_cycle)
    review = PerformanceReview.objects.filter(employee=employee, performance_cycle=performance_cycle).first()
    
    report = {
        'employee_id': employee.id,
        'employee_name': f"{employee.user.first_name} {employee.user.last_name}" if hasattr(employee, 'user') else str(employee),
        'goals': list(goals.values('title', 'goal_type', 'weightage', 'status', 'achieved_value')),
        'ratings': {
            'self_rating': review.self_rating if review else None,
            'manager_rating': review.manager_rating if review else None,
        },
        'final_grade': review.final_rating if review else None,
        'promotion_recommendation': review.promotion_recommended if review else False
    }
    return report

def generate_department_performance_report(department, performance_cycle):
    reviews = PerformanceReview.objects.filter(
        employee__department=department, 
        performance_cycle=performance_cycle,
        status='Completed'
    )
    
    average_rating = reviews.aggregate(Avg('final_rating'))['final_rating__avg'] or 0
    top_performers = reviews.filter(final_rating__gte=4.5).values('employee__user__first_name', 'employee__user__last_name', 'final_rating')
    low_performers = reviews.filter(final_rating__lt=2.5).values('employee__user__first_name', 'employee__user__last_name', 'final_rating')
    
    return {
        'department': getattr(department, 'name', str(department)),
        'average_rating': round(average_rating, 2),
        'top_performers': list(top_performers),
        'low_performers': list(low_performers)
    }
