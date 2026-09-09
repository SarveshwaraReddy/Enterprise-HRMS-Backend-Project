from django.contrib import admin
from .models import Document

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'document_type', 'uploaded_at')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_id')
    list_filter = ('document_type', 'uploaded_at')
