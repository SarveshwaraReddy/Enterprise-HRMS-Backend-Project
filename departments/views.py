from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, Sum, Count
from .models import Department
from .serializers import DepartmentSerializer

from enterprise_hrms.api.permissions import IsAdminOrHR

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrHR()]
        return [permissions.IsAuthenticated()]

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        department = self.get_object()
        employees = department.employees.all()
        
        total_employees = employees.count()
        avg_salary = employees.aggregate(Avg('salary'))['salary__avg'] or 0
        total_salary_budget = employees.aggregate(Sum('salary'))['salary__sum'] or 0
        
        status_breakdown = employees.values('status').annotate(count=Count('status'))
        gender_breakdown = employees.values('gender').annotate(count=Count('gender'))
        
        stats = {
            "department_id": department.id,
            "department_name": department.name,
            "department_code": department.code,
            "total_employees": total_employees,
            "average_salary": round(float(avg_salary), 2),
            "total_salary_budget": round(float(total_salary_budget), 2),
            "status_breakdown": {item['status']: item['count'] for item in status_breakdown},
            "gender_breakdown": {item['gender']: item['count'] for item in gender_breakdown}
        }
        return Response(stats)

    @action(detail=False, methods=['get'])
    def all_statistics(self, request):
        departments = Department.objects.all()
        stats_list = []
        
        for dept in departments:
            employees = dept.employees.all()
            total_employees = employees.count()
            avg_salary = employees.aggregate(Avg('salary'))['salary__avg'] or 0
            total_salary_budget = employees.aggregate(Sum('salary'))['salary__sum'] or 0
            status_breakdown = employees.values('status').annotate(count=Count('status'))
            
            stats_list.append({
                "department_id": dept.id,
                "department_name": dept.name,
                "department_code": dept.code,
                "total_employees": total_employees,
                "average_salary": round(float(avg_salary), 2),
                "total_salary_budget": round(float(total_salary_budget), 2),
                "status_breakdown": {item['status']: item['count'] for item in status_breakdown}
            })
            
        return Response(stats_list)
