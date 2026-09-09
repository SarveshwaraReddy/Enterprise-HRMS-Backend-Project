from django.contrib import admin
from .models import Department

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'manager')
    search_fields = ('name', 'code', 'manager__first_name', 'manager__last_name')
    list_filter = ('manager',)
