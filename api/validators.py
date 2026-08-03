import os
from django.core.exceptions import ValidationError
from django.utils import timezone

def validate_positive_salary(value):
    """
    Validates that a financial/salary value is strictly greater than zero.
    """
    if value is not None and value <= 0:
        raise ValidationError("Salary/amount must be greater than zero.")

def validate_leave_dates(start_date, end_date):
    """
    Validates that the start date of a leave is strictly less than the end date.
    """
    if start_date and end_date and start_date >= end_date:
        raise ValidationError("Start date must be less than end date.")

def validate_file_upload(file):
    """
    Validates file extension and size for secure uploading (Module 13).
    """
    # 1. Check extension
    ext = os.path.splitext(file.name)[1].lower()
    valid_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx']
    if ext not in valid_extensions:
        raise ValidationError(f"Unsupported file extension. Allowed formats: {', '.join(valid_extensions)}")
        
    # 2. Limit size to 5MB
    limit = 5 * 1024 * 1024
    if file.size > limit:
        raise ValidationError("File size cannot exceed 5MB.")
