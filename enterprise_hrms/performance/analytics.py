from django.db.models import Count, Avg, Sum
from .models import PerformanceReview

def generate_company_analytics(performance_cycle=None):
    queryset = PerformanceReview.objects.filter(status='Completed')
    if performance_cycle:
        queryset = queryset.filter(performance_cycle=performance_cycle)
        
    total_reviews = queryset.count()
    if total_reviews == 0:
        return {'message': 'No completed reviews available.'}
        
    rating_distribution = queryset.values('final_rating').annotate(count=Count('id')).order_by('final_rating')
    promotion_recommendations = queryset.filter(promotion_recommended=True).count()
    
    # Assuming employee has a base salary, we would join to calculate exact budget. 
    # For now, just aggregate the percentage points.
    increment_budget_percent = queryset.aggregate(Sum('increment_percentage'))['increment_percentage__sum'] or 0
    
    performance_by_department = queryset.values('employee__department__name').annotate(
        avg_rating=Avg('final_rating')
    ).order_by('-avg_rating')
    
    return {
        'total_reviews': total_reviews,
        'rating_distribution': list(rating_distribution),
        'promotion_recommendations': promotion_recommendations,
        'total_increment_percentage_points': increment_budget_percent,
        'performance_by_department': list(performance_by_department)
    }
