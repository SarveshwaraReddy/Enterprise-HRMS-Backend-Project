from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import PerformanceCycle, Goal, PerformanceReview
from .serializers import PerformanceCycleSerializer, GoalSerializer, PerformanceReviewSerializer
from .services import (
    create_cycle, assign_goal, submit_self_review, manager_review, hr_review
)
from .permissions import IsHR, IsManager, IsOwnerOrHR

class PerformanceCycleViewSet(viewsets.ModelViewSet):
    queryset = PerformanceCycle.objects.all()
    serializer_class = PerformanceCycleSerializer
    # Only HR and Admins should manage cycles, but let's assume IsHR for creation
    
    def create(self, request, *args, **kwargs):
        # Using service
        cycle = create_cycle(
            cycle_name=request.data.get('cycle_name'),
            start_date=request.data.get('start_date'),
            end_date=request.data.get('end_date'),
            description=request.data.get('description'),
            status=request.data.get('status', 'Draft')
        )
        serializer = self.get_serializer(cycle)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class GoalViewSet(viewsets.ModelViewSet):
    queryset = Goal.objects.all()
    serializer_class = GoalSerializer
    
    def create(self, request, *args, **kwargs):
        # In real system, validate employee exists etc. Assuming IDs for now
        from enterprise_hrms.employees.models import Employee
        
        emp = Employee.objects.get(id=request.data.get('employee'))
        cycle = PerformanceCycle.objects.get(id=request.data.get('performance_cycle'))
        
        goal = assign_goal(
            employee=emp,
            performance_cycle=cycle,
            title=request.data.get('title'),
            goal_type=request.data.get('goal_type'),
            weightage=float(request.data.get('weightage')),
            description=request.data.get('description')
        )
        serializer = self.get_serializer(goal)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class PerformanceReviewViewSet(viewsets.ModelViewSet):
    queryset = PerformanceReview.objects.all()
    serializer_class = PerformanceReviewSerializer

    @action(detail=True, methods=['put'], url_path='self')
    def self_review_action(self, request, pk=None):
        review = self.get_object()
        updated_review = submit_self_review(
            review=review,
            self_rating=request.data.get('self_rating'),
            self_comments=request.data.get('self_comments')
        )
        serializer = self.get_serializer(updated_review)
        return Response(serializer.data)

    @action(detail=True, methods=['put'], url_path='manager')
    def manager_review_action(self, request, pk=None):
        review = self.get_object()
        updated_review = manager_review(
            review=review,
            manager_rating=request.data.get('manager_rating'),
            manager_comments=request.data.get('manager_comments')
        )
        serializer = self.get_serializer(updated_review)
        return Response(serializer.data)

    @action(detail=True, methods=['put'], url_path='hr')
    def hr_review_action(self, request, pk=None):
        review = self.get_object()
        updated_review = hr_review(
            review=review,
            hr_comments=request.data.get('hr_comments'),
            final_rating=request.data.get('final_rating'),
            goal_achievement_rating=request.data.get('goal_achievement_rating')
        )
        serializer = self.get_serializer(updated_review)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        active_cycles = PerformanceCycle.objects.filter(status='Active').count()
        pending_self = PerformanceReview.objects.filter(status='Pending').count()
        pending_manager = PerformanceReview.objects.filter(status='Self Submitted').count()
        pending_hr = PerformanceReview.objects.filter(status='Manager Reviewed').count()
        
        # Simple placeholders for top performers, etc.
        top_performers = PerformanceReview.objects.filter(status='Completed', final_rating__gte=4.5).count()
        
        data = {
            'active_cycles': active_cycles,
            'pending_self_reviews': pending_self,
            'pending_manager_reviews': pending_manager,
            'pending_hr_approvals': pending_hr,
            'top_performers_count': top_performers,
        }
        return Response(data)

from rest_framework.views import APIView
from .reports import generate_employee_performance_report, generate_department_performance_report
from .analytics import generate_company_analytics
from django.shortcuts import get_object_or_404
from enterprise_hrms.employees.models import Employee
# Assuming a Department model exists somewhere, e.g., enterprise_hrms.employees.models.Department
# We'll just pass department ID to a hypothetical Department model if needed, or query it.

class ReportsView(APIView):
    def get(self, request):
        cycle_id = request.query_params.get('cycle_id')
        employee_id = request.query_params.get('employee_id')
        department_id = request.query_params.get('department_id')
        
        cycle = get_object_or_404(PerformanceCycle, id=cycle_id)
        
        if employee_id:
            employee = get_object_or_404(Employee, id=employee_id)
            report = generate_employee_performance_report(employee, cycle)
            return Response(report)
        elif department_id:
            # Mock department for now or import it
            # from enterprise_hrms.employees.models import Department
            # department = get_object_or_404(Department, id=department_id)
            class MockDept:
                def __init__(self, id):
                    self.id = id
                    self.name = f"Dept {id}"
            report = generate_department_performance_report(MockDept(department_id), cycle)
            return Response(report)
        return Response({'error': 'Provide employee_id or department_id'}, status=400)

class AnalyticsView(APIView):
    def get(self, request):
        cycle_id = request.query_params.get('cycle_id')
        cycle = PerformanceCycle.objects.filter(id=cycle_id).first() if cycle_id else None
        
        analytics = generate_company_analytics(cycle)
        return Response(analytics)
