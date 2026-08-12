from django.utils import timezone
from .models import PerformanceCycle, Goal, PerformanceReview
from .validators import validate_active_performance_cycle, validate_goal_weightage
from .notifications import log_and_notify

def create_cycle(cycle_name, start_date, end_date, description=None, status='Draft'):
    cycle = PerformanceCycle.objects.create(
        cycle_name=cycle_name,
        start_date=start_date,
        end_date=end_date,
        description=description,
        status=status
    )
    if status == 'Active':
        log_and_notify("Performance Cycle Created", f"Cycle {cycle_name} is now active.", recipients=['HR', 'Manager', 'Employee'])
    return cycle

def assign_goal(employee, performance_cycle, title, goal_type, weightage, description=None):
    validate_active_performance_cycle(performance_cycle)
    validate_goal_weightage(employee, performance_cycle, weightage)
    
    goal = Goal.objects.create(
        employee=employee,
        performance_cycle=performance_cycle,
        title=title,
        goal_type=goal_type,
        weightage=weightage,
        description=description,
        status='Not Started'
    )
    log_and_notify("Goal Assigned", f"Goal '{title}' assigned.", recipients=[employee.user])
    return goal

def submit_self_review(review, self_rating, self_comments):
    validate_active_performance_cycle(review.performance_cycle)
    
    review.self_rating = self_rating
    review.self_comments = self_comments
    review.status = 'Self Submitted'
    review.review_date = timezone.now().date()
    review.save()
    
    log_and_notify("Self Review Submitted", f"{review.employee} submitted their review.", recipients=[review.employee.manager.user if hasattr(review.employee, 'manager') and review.employee.manager else 'HR'])
    return review

def manager_review(review, manager_rating, manager_comments):
    validate_active_performance_cycle(review.performance_cycle)
    
    review.manager_rating = manager_rating
    review.manager_comments = manager_comments
    review.status = 'Manager Reviewed'
    review.save()
    
    log_and_notify("Manager Review Completed", f"Manager reviewed {review.employee}.", recipients=['HR'])
    return review

def hr_review(review, hr_comments, final_rating=None, goal_achievement_rating=None):
    validate_active_performance_cycle(review.performance_cycle)
    
    review.hr_comments = hr_comments
    
    # Calculate final rating if not provided
    if final_rating is None:
        if goal_achievement_rating is None:
            # Simple assumption: goal achievement rating out of 5 based on completed goals weightage
            completed_weightage = sum(g.weightage for g in review.employee.goals.filter(performance_cycle=review.performance_cycle, status='Completed'))
            goal_achievement_rating = float(completed_weightage) / 20.0 # 100% -> 5.0

        calculated_rating = calculate_final_rating(
            float(review.self_rating or 0), 
            float(review.manager_rating or 0), 
            float(goal_achievement_rating)
        )
        review.final_rating = calculated_rating
    else:
        review.final_rating = final_rating

    review.increment_percentage = recommend_increment(review.final_rating)
    review.promotion_recommended = recommend_promotion(review.final_rating)
    
    review.status = 'Completed'
    review.save()
    
    log_and_notify("HR Approval Completed", f"HR completed review for {review.employee}. Final Rating: {review.final_rating}", recipients=[review.employee.user])
    return review

def calculate_final_rating(self_rating, manager_rating, goal_achievement_rating):
    """
    (Self Rating × 20%) + (Manager Rating × 60%) + (Goal Achievement × 20%)
    Assumes all ratings are on a 1-5 scale.
    """
    final = (self_rating * 0.20) + (manager_rating * 0.60) + (goal_achievement_rating * 0.20)
    return round(final, 1)

def recommend_increment(final_rating):
    """
    Increment percentage must be between 0–30%.
    Grades mapped to increments (approximate logic based on typical rules):
    < 2.0 -> 0%
    2.0 - 3.0 -> 5%
    3.0 - 4.0 -> 10%
    4.0 - 4.5 -> 20%
    >= 4.5 -> 30%
    """
    if final_rating < 2.0: return 0.0
    if final_rating < 3.0: return 5.0
    if final_rating < 4.0: return 10.0
    if final_rating < 4.5: return 20.0
    return 30.0

def recommend_promotion(final_rating):
    """
    Promotion recommendation requires a minimum final rating of 4.5/5.
    """
    return final_rating >= 4.5
