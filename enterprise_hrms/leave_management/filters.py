import django_filters
from .models import LeaveRequest


class LeaveRequestFilter(django_filters.FilterSet):
    employee = django_filters.CharFilter(method='filter_employee')
    department = django_filters.CharFilter(method='filter_department')
    leave_type = django_filters.CharFilter(method='filter_leave_type')
    status = django_filters.CharFilter(field_name='status', lookup_expr='exact')
    start_date = django_filters.DateFilter(field_name='start_date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='end_date', lookup_expr='lte')
    year = django_filters.NumberFilter(field_name='start_date__year')
    manager = django_filters.CharFilter(method='filter_manager')

    class Meta:
        model = LeaveRequest
        fields = ['status', 'start_date', 'end_date', 'year']

    def filter_employee(self, queryset, name, value):
        if value.isdigit():
            return queryset.filter(employee_id=int(value))
        return queryset.filter(employee__employee_id__iexact=value)

    def filter_department(self, queryset, name, value):
        if value.isdigit():
            return queryset.filter(employee__department_id=int(value))
        return queryset.filter(employee__department__code__iexact=value)

    def filter_leave_type(self, queryset, name, value):
        if value.isdigit():
            return queryset.filter(leave_type_id=int(value))
        return queryset.filter(leave_type__code__iexact=value)

    def filter_manager(self, queryset, name, value):
        if value.isdigit():
            return queryset.filter(employee__department__manager_id=int(value))
        return queryset.filter(employee__department__manager__employee_id__iexact=value)
