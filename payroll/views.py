import os
from decimal import Decimal
from rest_framework import viewsets, permissions, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.conf import settings

from .models import SalaryStructure, PayrollRun, Payslip, Payroll
from .serializers import (
    SalaryStructureSerializer,
    PayrollRunSerializer,
    PayslipSerializer,
    CreatePayrollRunSerializer,
    PayrollSerializer
)
from .services import PayrollService
from .permissions import IsPayrollAdmin, IsPayslipOwnerOrAdmin, IsHR
from .reports import (
    export_payroll_report_pdf,
    export_payroll_register_excel,
    export_payroll_transactions_csv,
    get_employee_salary_history,
    get_department_payroll_report,
)
from .pdf_generator import generate_payslip_pdf
from .utils import calculate_unpaid_leave_days
from enterprise_hrms.audit_logs.utils import log_action
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.api.permissions import IsOwnerOrAdminOrHR, IsAdminOrHR


class SalaryStructureViewSet(viewsets.ModelViewSet):
    serializer_class = SalaryStructureSerializer
    permission_classes = [permissions.IsAuthenticated, IsPayrollAdmin]
    filterset_fields = ['employee', 'status']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__employee_id']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role in ['admin', 'hr']:
            return SalaryStructure.objects.all()
        try:
            employee = user.employee_profile
            return SalaryStructure.objects.filter(employee=employee)
        except Employee.DoesNotExist:
            return SalaryStructure.objects.none()

    def create(self, request, *args, **kwargs):
        employee_id = request.data.get('employee')
        if not employee_id:
            return Response(
                {"success": False, "message": "Employee ID is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        salary_structure = PayrollService.create_salary_structure(employee_id, request.data)
        log_action(user=request.user, action="Salary Structure Created", description=f"Created salary structure for employee {employee_id}", request=request)
        serializer = self.get_serializer(salary_structure)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        updated_structure = PayrollService.update_salary_structure(instance.id, request.data)
        log_action(user=request.user, action="Salary Structure Updated", description=f"Updated salary structure ID {instance.id}", request=request)
        serializer = self.get_serializer(updated_structure)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        PayrollService.delete_salary_structure(instance.id)
        log_action(user=request.user, action="Salary Structure Deleted", description=f"Deleted salary structure ID {instance.id}", request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PayrollRunViewSet(viewsets.ModelViewSet):
    queryset = PayrollRun.objects.all()
    serializer_class = PayrollRunSerializer
    permission_classes = [permissions.IsAuthenticated, IsPayrollAdmin]
    filterset_fields = ['payroll_month', 'payroll_year', 'status']
    ordering_fields = ['payroll_year', 'payroll_month']

    def create(self, request, *args, **kwargs):
        serializer = CreatePayrollRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        month = serializer.validated_data['payroll_month']
        year = serializer.validated_data['payroll_year']
        remarks = serializer.validated_data.get('remarks', '')

        payroll_run = PayrollService.create_payroll_run(
            payroll_month=month,
            payroll_year=year,
            processed_by=request.user,
            remarks=remarks
        )

        log_action(user=request.user, action="Payroll Run Created", description=f"Created payroll run for {month}/{year}", request=request)
        return Response(PayrollRunSerializer(payroll_run).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['put', 'post'], url_path='approve')
    def approve(self, request, pk=None):
        payroll_run = PayrollService.approve_payroll(pk, approved_by=request.user)
        log_action(user=request.user, action="Payroll Approved", description=f"Approved payroll run ID {pk}", request=request)
        return Response(PayrollRunSerializer(payroll_run).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['put', 'post'], url_path='release')
    def release(self, request, pk=None):
        payroll_run = PayrollService.release_payroll(pk)
        log_action(user=request.user, action="Payroll Released", description=f"Released payroll run ID {pk}", request=request)
        return Response(PayrollRunSerializer(payroll_run).data, status=status.HTTP_200_OK)


class PayslipViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PayslipSerializer
    permission_classes = [permissions.IsAuthenticated, IsPayslipOwnerOrAdmin]
    filterset_fields = ['employee', 'payroll_run', 'payroll_run__payroll_month', 'payroll_run__payroll_year']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__employee_id']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role in ['admin', 'hr']:
            return Payslip.objects.all()
        try:
            employee = user.employee_profile
            return Payslip.objects.filter(employee=employee)
        except Employee.DoesNotExist:
            return Payslip.objects.none()

    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, pk=None):
        payslip = self.get_object()

        file_path = os.path.join(settings.MEDIA_ROOT, str(payslip.pdf_path)) if payslip.pdf_path else None
        if not file_path or not os.path.exists(file_path):
            pdf_bytes = PayrollService.generate_payslip(payslip.employee, payslip.payroll_run)
            file_path = os.path.join(settings.MEDIA_ROOT, str(payslip.pdf_path))

        with open(file_path, 'rb') as f:
            pdf_bytes = f.read()

        filename = f"payslip_{payslip.employee.employee_id}_{payslip.payroll_run.payroll_month}_{payslip.payroll_run.payroll_year}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        log_action(user=request.user, action="Payslip Downloaded", description=f"Downloaded payslip ID {payslip.id}", request=request)
        return response


class LegacyPayrollViewSet(viewsets.ModelViewSet):
    """Legacy ViewSet maintaining full backward compatibility with older endpoints/tests."""
    serializer_class = PayrollSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdminOrHR]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role in ['admin', 'hr']:
            return Payroll.objects.all()
        try:
            return Payroll.objects.filter(employee=user.employee_profile)
        except Employee.DoesNotExist:
            return Payroll.objects.none()

    @action(detail=False, methods=['post'], url_path='generate', permission_classes=[IsAdminOrHR])
    def generate(self, request):
        month = request.data.get('month')
        year = request.data.get('year')
        employee_id = request.data.get('employee_id')

        if not month or not year:
            return Response({"success": False, "message": "Parameters 'month' and 'year' are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            month = int(month)
            year = int(year)
        except ValueError:
            return Response({"success": False, "message": "Invalid format for 'month' or 'year'."}, status=status.HTTP_400_BAD_REQUEST)

        employees = Employee.objects.filter(id=employee_id, status='active') if employee_id else Employee.objects.filter(status='active')
        records = []
        for emp in employees:
            basic = emp.salary
            allowances = round(basic * Decimal('0.10'), 2)
            unpaid_days = calculate_unpaid_leave_days(emp, month, year)
            deductions = round(unpaid_days * (basic / Decimal('30.00')), 2)
            net_salary = max(Decimal('0.00'), basic + allowances - deductions)

            p, _ = Payroll.objects.update_or_create(
                employee=emp, month=month, year=year,
                defaults={'basic_salary': basic, 'allowances': allowances, 'deductions': deductions, 'net_salary': net_salary, 'status': 'generated'}
            )
            records.append(PayrollSerializer(p).data)

        return Response({"success": True, "message": f"Successfully generated payroll for {len(records)} employee(s).", "data": records}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='slip')
    def slip(self, request, pk=None):
        payroll = self.get_object()
        pdf_data = generate_payslip_pdf(payroll)
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="payslip_{payroll.id}.pdf"'
        return response


class PayrollDashboardView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsPayrollAdmin]

    def get(self, request):
        analytics = PayrollService.get_dashboard_analytics()
        return Response({"success": True, "data": analytics}, status=status.HTTP_200_OK)


class PayrollReportsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, report_type=None):
        user = request.user
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        employee_id = request.query_params.get('employee_id')

        try:
            month = int(month) if month else None
            year = int(year) if year else None
        except ValueError:
            return Response({"success": False, "message": "Invalid month or year format."}, status=status.HTTP_400_BAD_REQUEST)

        if report_type == 'summary':
            if not (user.is_superuser or user.role in ['admin', 'hr']):
                return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
            summary = PayrollService.payroll_summary(month=month, year=year)
            return Response({"success": True, "data": summary})

        elif report_type == 'department':
            if not (user.is_superuser or user.role in ['admin', 'hr']):
                return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
            dept_report = get_department_payroll_report(month=month, year=year)
            return Response({"success": True, "data": dept_report})

        elif report_type == 'history':
            if not employee_id:
                if hasattr(user, 'employee_profile') and user.employee_profile:
                    employee_id = user.employee_profile.id
                else:
                    return Response({"success": False, "message": "Employee ID required."}, status=status.HTTP_400_BAD_REQUEST)

            if not (user.is_superuser or user.role in ['admin', 'hr']):
                if not hasattr(user, 'employee_profile') or str(user.employee_profile.id) != str(employee_id):
                    return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

            history = get_employee_salary_history(employee_id)
            return Response({"success": True, "data": history})

        elif report_type == 'export':
            if not (user.is_superuser or user.role in ['admin', 'hr']):
                return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

            fmt = request.query_params.get('format', 'csv').lower()
            if not month or not year:
                latest_run = PayrollRun.objects.order_by('-payroll_year', '-payroll_month').first()
                if latest_run:
                    month = latest_run.payroll_month
                    year = latest_run.payroll_year
                else:
                    month, year = 1, 2026

            if fmt == 'pdf':
                pdf_bytes = export_payroll_report_pdf(month, year)
                response = HttpResponse(pdf_bytes, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="payroll_report_{month}_{year}.pdf"'
                return response
            elif fmt in ['excel', 'xlsx']:
                excel_bytes = export_payroll_register_excel(month, year)
                response = HttpResponse(excel_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = f'attachment; filename="payroll_register_{month}_{year}.xlsx"'
                return response
            elif fmt == 'csv':
                csv_bytes = export_payroll_transactions_csv(month, year)
                response = HttpResponse(csv_bytes, content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="payroll_transactions_{month}_{year}.csv"'
                return response
            else:
                return Response({"success": False, "message": "Unsupported format. Use pdf, excel, or csv."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"success": False, "message": "Invalid report type specified."}, status=status.HTTP_400_BAD_REQUEST)
