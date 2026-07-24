from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.utils import timezone
from decimal import Decimal

from .models import Payroll
from .serializers import PayrollSerializer
from .utils import calculate_unpaid_leave_days, generate_payslip_pdf
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.api.permissions import IsOwnerOrAdminOrHR, IsAdminOrHR
from enterprise_hrms.audit_logs.utils import log_action
from enterprise_hrms.notifications.utils import create_notification

class PayrollViewSet(viewsets.ModelViewSet):
    """
    ViewSet to manage Payroll records.
    Restricted to Admin/HR for write operations; Employees can view their own payroll.
    """
    serializer_class = PayrollSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdminOrHR]
    filterset_fields = ['employee', 'month', 'year', 'status']
    search_fields = ['employee__first_name', 'employee__last_name', 'status']
    ordering_fields = ['year', 'month']
    ordering = ['-year', '-month']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role in ['admin', 'hr']:
            return Payroll.objects.all()
        # Employee can only see their own payrolls
        try:
            employee = user.employee_profile
            return Payroll.objects.filter(employee=employee)
        except Employee.DoesNotExist:
            return Payroll.objects.none()

    def perform_create(self, serializer):
        # Override to calculate net_salary automatically on manual creation
        basic_salary = Decimal(str(serializer.validated_data['basic_salary']))
        allowances = Decimal(str(serializer.validated_data.get('allowances', 0.00)))
        deductions = Decimal(str(serializer.validated_data.get('deductions', 0.00)))
        net_salary = basic_salary + allowances - deductions
        
        payroll = serializer.save(net_salary=net_salary)
        
        log_action(
            user=self.request.user,
            action="Payroll Generated",
            description=f"Payroll manually created for {payroll.employee.first_name} {payroll.employee.last_name} for {payroll.month}/{payroll.year}",
            request=self.request
        )

    def perform_update(self, serializer):
        # Recalculate net salary on manual update
        basic_salary = Decimal(str(serializer.validated_data.get('basic_salary', self.get_object().basic_salary)))
        allowances = Decimal(str(serializer.validated_data.get('allowances', self.get_object().allowances)))
        deductions = Decimal(str(serializer.validated_data.get('deductions', self.get_object().deductions)))
        net_salary = basic_salary + allowances - deductions
        
        payroll = serializer.save(net_salary=net_salary)
        
        log_action(
            user=self.request.user,
            action="Payroll Updated",
            description=f"Payroll updated for {payroll.employee.first_name} {payroll.employee.last_name} for {payroll.month}/{payroll.year}",
            request=self.request
        )

    @action(detail=False, methods=['post'], url_path='generate', permission_classes=[IsAdminOrHR])
    def generate(self, request):
        """
        Bulk or single employee payroll generation for a given month and year.
        Deducts for unpaid leaves automatically. Allowances default to 10% of basic.
        """
        month = request.data.get('month')
        year = request.data.get('year')
        employee_id = request.data.get('employee_id')
        
        if not month or not year:
            return Response(
                {"success": False, "message": "Parameters 'month' and 'year' are required in the body."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            month = int(month)
            year = int(year)
        except ValueError:
            return Response(
                {"success": False, "message": "Invalid format for 'month' or 'year'."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if employee_id:
            employees = Employee.objects.filter(id=employee_id, status='active')
            if not employees.exists():
                return Response(
                    {"success": False, "message": "Active Employee not found."},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            employees = Employee.objects.filter(status='active')
            
        generated_count = 0
        payroll_records = []
        
        for emp in employees:
            basic_salary = emp.salary
            # Default allowances to 10% of basic
            allowances = round(basic_salary * Decimal('0.10'), 2)
            
            # Calculate unpaid leave deductions
            unpaid_days = calculate_unpaid_leave_days(emp, month, year)
            daily_rate = basic_salary / Decimal('30.00')
            deductions = round(unpaid_days * daily_rate, 2)
            
            net_salary = basic_salary + allowances - deductions
            if net_salary < 0:
                net_salary = Decimal('0.00')
                
            payroll, created = Payroll.objects.update_or_create(
                employee=emp,
                month=month,
                year=year,
                defaults={
                    'basic_salary': basic_salary,
                    'allowances': allowances,
                    'deductions': deductions,
                    'net_salary': net_salary,
                    'status': 'generated'
                }
            )
            
            generated_count += 1
            payroll_records.append(PayrollSerializer(payroll).data)
            
            # Log action
            log_action(
                user=request.user,
                action="Payroll Generated",
                description=f"Payroll generated for {emp.first_name} {emp.last_name} for {month}/{year}",
                request=request
            )
            
            # Create employee notification
            if emp.user:
                create_notification(
                    recipient=emp.user,
                    title="Payslip Generated",
                    message=f"Your payroll payslip for {month}/{year} has been generated. Net Salary: ${net_salary:,.2f}"
                )
                
        return Response({
            "success": True,
            "message": f"Successfully generated payroll for {generated_count} employee(s).",
            "data": payroll_records
        })

    @action(detail=True, methods=['get'], url_path='slip')
    def slip(self, request, pk=None):
        """
        Download a beautiful PDF copy of the pay slip.
        Restricted to owner employee, Admin, or HR.
        """
        payroll = self.get_object()
        
        # Enforce PDF document rendering
        pdf_data = generate_payslip_pdf(payroll)
        
        response = HttpResponse(pdf_data, content_type='application/pdf')
        filename = f"payslip_{payroll.employee.employee_id}_{payroll.month}_{payroll.year}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Log download action
        log_action(
            user=request.user,
            action="Payslip Downloaded",
            description=f"Downloaded payslip for {payroll.employee.first_name} {payroll.employee.last_name} ({payroll.month}/{payroll.year})",
            request=request
        )
        
        return response
