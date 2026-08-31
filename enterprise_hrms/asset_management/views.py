import datetime
from django.utils import timezone
from django.db.models import Count, Q, Avg, F, ExpressionWrapper, DurationField
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from enterprise_hrms.employees.models import Employee
from .models import (
    AssetCategory, Asset, AssetAssignment,
    AssetMaintenance, SupportTicket, SoftwareLicense,
)
from .serializers import (
    AssetCategorySerializer,
    AssetSerializer,
    AssetAssignmentSerializer,
    AssetAssignRequestSerializer,
    AssetReturnSerializer,
    AssetMaintenanceSerializer,
    SupportTicketSerializer,
    SupportTicketCloseSerializer,
    SoftwareLicenseSerializer,
    LicenseAssignSerializer,
)
from .permissions import (
    IsITTeamOrAdmin,
    IsITOrHROrAdmin,
    IsTicketOwnerOrITOrAdmin,
    IsAssetAssigneeOrITOrAdmin,
)
from .services import (
    create_asset,
    assign_asset,
    return_asset,
    schedule_maintenance,
    create_ticket,
    assign_ticket,
    close_ticket,
    asset_summary,
)
from .maintenance import complete_maintenance, cancel_maintenance
from .reports import (
    generate_asset_report_pdf, generate_asset_report_excel, generate_asset_report_csv,
    generate_support_report_pdf, generate_support_report_excel, generate_support_report_csv,
    generate_license_report_pdf, generate_license_report_excel, generate_license_report_csv,
)
from .notifications import notify_license_expiry, notify_warranty_expiry


# ─────────────────────────────────────────────
# Asset Category
# ─────────────────────────────────────────────

class AssetCategoryViewSet(viewsets.ModelViewSet):
    """
    CRUD for asset categories. Only IT team / Admin can create/update/delete.
    """
    queryset = AssetCategory.objects.all()
    serializer_class = AssetCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsITTeamOrAdmin()]
        return [permissions.IsAuthenticated()]


# ─────────────────────────────────────────────
# Asset
# ─────────────────────────────────────────────

class AssetViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for Assets + custom actions: assign, return_asset, my_assets, summary.

    POST   /api/v1/assets/
    GET    /api/v1/assets/
    GET    /api/v1/assets/{id}/
    PUT    /api/v1/assets/{id}/
    DELETE /api/v1/assets/{id}/
    POST   /api/v1/assets/assign/
    PUT    /api/v1/assets/return/
    GET    /api/v1/assets/my-assets/
    GET    /api/v1/assets/summary/
    """
    queryset = Asset.objects.select_related('category').all()
    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['asset_code', 'name', 'serial_number', 'vendor', 'location']
    filterset_fields = ['status', 'category']
    ordering_fields = ['asset_code', 'name', 'purchase_date', 'created_at']
    ordering = ['asset_code']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy',
                           'assign', 'return_asset', 'schedule_maintenance_action',
                           'complete_maintenance_action', 'cancel_maintenance_action']:
            return [permissions.IsAuthenticated(), IsITTeamOrAdmin()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        asset = create_asset(serializer.validated_data, user=request.user, request=request)
        return Response(AssetSerializer(asset).data, status=status.HTTP_201_CREATED)

    # POST /api/v1/assets/assign/
    @action(detail=False, methods=['post'], url_path='assign')
    def assign(self, request):
        """Assign an asset to an employee."""
        asset_id = request.data.get('asset')
        try:
            asset = Asset.objects.get(pk=asset_id)
        except Asset.DoesNotExist:
            return Response({'detail': 'Asset not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AssetAssignRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Resolve assigner
        assigned_by = None
        try:
            assigned_by = request.user.employee_profile
        except Employee.DoesNotExist:
            pass

        assignment = assign_asset(
            asset=asset,
            employee=data['employee'],
            assigned_by=assigned_by,
            assigned_date=data.get('assigned_date'),
            expected_return_date=data.get('expected_return_date'),
            notes=data.get('notes', ''),
            user=request.user,
            request=request,
        )
        return Response(AssetAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)

    # PUT /api/v1/assets/return/
    @action(detail=False, methods=['put'], url_path='return')
    def return_asset(self, request):
        """Return an assigned asset."""
        serializer = AssetReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            assignment = AssetAssignment.objects.select_related('asset', 'employee').get(
                pk=serializer.validated_data['assignment_id']
            )
        except AssetAssignment.DoesNotExist:
            return Response({'detail': 'Assignment not found.'}, status=status.HTTP_404_NOT_FOUND)

        assignment = return_asset(assignment, user=request.user, request=request)
        return Response(AssetAssignmentSerializer(assignment).data)

    # GET /api/v1/assets/my-assets/
    @action(detail=False, methods=['get'], url_path='my-assets',
            permission_classes=[permissions.IsAuthenticated])
    def my_assets(self, request):
        """List assets currently assigned to the authenticated employee."""
        try:
            employee = request.user.employee_profile
        except Employee.DoesNotExist:
            return Response({'detail': 'Employee profile not found.'}, status=status.HTTP_404_NOT_FOUND)

        assignments = AssetAssignment.objects.filter(
            employee=employee, status='active'
        ).select_related('asset', 'asset__category')
        serializer = AssetAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)

    # GET /api/v1/assets/summary/
    @action(detail=False, methods=['get'], url_path='summary',
            permission_classes=[permissions.IsAuthenticated, IsITOrHROrAdmin])
    def summary(self, request):
        """Return a high-level asset summary by status."""
        return Response(asset_summary())

    # POST /api/v1/assets/{id}/schedule-maintenance/
    @action(detail=True, methods=['post'], url_path='schedule-maintenance')
    def schedule_maintenance_action(self, request, pk=None):
        """Schedule maintenance for a specific asset."""
        asset = self.get_object()
        scheduled_date = request.data.get('scheduled_date')
        description = request.data.get('description', '')
        cost = request.data.get('cost')

        scheduled_by = None
        try:
            scheduled_by = request.user.employee_profile
        except Employee.DoesNotExist:
            pass

        maintenance = schedule_maintenance(
            asset=asset,
            scheduled_date=scheduled_date,
            scheduled_by=scheduled_by,
            description=description,
            cost=cost,
            user=request.user,
            request=request,
        )
        return Response(AssetMaintenanceSerializer(maintenance).data, status=status.HTTP_201_CREATED)

    # POST /api/v1/assets/maintenance/{id}/complete/
    @action(detail=True, methods=['post'], url_path='maintenance/complete')
    def complete_maintenance_action(self, request, pk=None):
        """Mark a maintenance record as completed."""
        try:
            maintenance = AssetMaintenance.objects.select_related('asset').get(pk=pk)
        except AssetMaintenance.DoesNotExist:
            return Response({'detail': 'Maintenance record not found.'}, status=status.HTTP_404_NOT_FOUND)
        completed_date = request.data.get('completed_date')
        maintenance = complete_maintenance(maintenance, completed_date=completed_date,
                                          user=request.user, request=request)
        return Response(AssetMaintenanceSerializer(maintenance).data)


# ─────────────────────────────────────────────
# Asset Assignment
# ─────────────────────────────────────────────

class AssetAssignmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for asset assignments.
    IT team / Admin see all; employees see only their own.
    """
    serializer_class = AssetAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsAssetAssigneeOrITOrAdmin]
    filterset_fields = ['status', 'asset', 'employee']
    ordering_fields = ['assigned_date', 'created_at']
    ordering = ['-assigned_date']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or getattr(user, 'role', '') in ['admin', 'it']:
            return AssetAssignment.objects.select_related(
                'asset', 'asset__category', 'employee', 'assigned_by'
            ).all()
        try:
            employee = user.employee_profile
            return AssetAssignment.objects.filter(employee=employee).select_related(
                'asset', 'asset__category', 'employee', 'assigned_by'
            )
        except Employee.DoesNotExist:
            return AssetAssignment.objects.none()


# ─────────────────────────────────────────────
# Asset Maintenance
# ─────────────────────────────────────────────

class AssetMaintenanceViewSet(viewsets.ModelViewSet):
    """
    CRUD for asset maintenance records. Restricted to IT team / Admin.
    """
    queryset = AssetMaintenance.objects.select_related('asset', 'scheduled_by').all()
    serializer_class = AssetMaintenanceSerializer
    permission_classes = [permissions.IsAuthenticated, IsITTeamOrAdmin]
    filterset_fields = ['status', 'asset']
    ordering_fields = ['scheduled_date', 'created_at']
    ordering = ['-scheduled_date']

    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        """Mark a maintenance record as completed."""
        maintenance = self.get_object()
        completed_date = request.data.get('completed_date')
        maintenance = complete_maintenance(
            maintenance, completed_date=completed_date,
            user=request.user, request=request
        )
        return Response(self.get_serializer(maintenance).data)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """Cancel a maintenance record."""
        maintenance = self.get_object()
        maintenance = cancel_maintenance(maintenance, user=request.user, request=request)
        return Response(self.get_serializer(maintenance).data)


# ─────────────────────────────────────────────
# IT Support Tickets
# ─────────────────────────────────────────────

class SupportTicketViewSet(viewsets.ModelViewSet):
    """
    Support ticket lifecycle management.

    POST /api/v1/support/tickets/
    GET  /api/v1/support/tickets/
    PUT  /api/v1/support/tickets/{id}/
    PUT  /api/v1/support/tickets/{id}/close/
    PUT  /api/v1/support/tickets/{id}/assign/
    """
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated, IsTicketOwnerOrITOrAdmin]
    filterset_fields = ['status', 'priority', 'category', 'assigned_engineer']
    search_fields = ['ticket_number', 'subject', 'description']
    ordering_fields = ['created_at', 'priority']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or getattr(user, 'role', '') in ['admin', 'it']:
            return SupportTicket.objects.select_related(
                'employee', 'asset', 'assigned_engineer'
            ).all()
        try:
            employee = user.employee_profile
            return SupportTicket.objects.filter(employee=employee).select_related(
                'employee', 'asset', 'assigned_engineer'
            )
        except Employee.DoesNotExist:
            return SupportTicket.objects.none()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Resolve employee
        employee = data.get('employee')
        if not employee:
            try:
                employee = request.user.employee_profile
            except Employee.DoesNotExist:
                return Response(
                    {'detail': 'Employee profile not found.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        ticket = create_ticket(
            employee=employee,
            subject=data['subject'],
            description=data['description'],
            category=data.get('category', 'other'),
            priority=data.get('priority', 'medium'),
            asset=data.get('asset'),
            assigned_engineer=data.get('assigned_engineer'),
            user=request.user,
            request=request,
        )
        return Response(SupportTicketSerializer(ticket).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        # Closed ticket guard
        if instance.status == 'closed':
            return Response(
                {'detail': f"Ticket '{instance.ticket_number}' is closed and cannot be edited."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    # PUT /api/v1/support/tickets/{id}/close/
    @action(detail=True, methods=['put'], url_path='close',
            permission_classes=[permissions.IsAuthenticated, IsITTeamOrAdmin])
    def close(self, request, pk=None):
        """Close a support ticket."""
        ticket = self.get_object()
        serializer = SupportTicketCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = close_ticket(
            ticket,
            resolution_notes=serializer.validated_data.get('resolution_notes', ''),
            user=request.user,
            request=request,
        )
        return Response(SupportTicketSerializer(ticket).data)

    # PUT /api/v1/support/tickets/{id}/assign/
    @action(detail=True, methods=['put'], url_path='assign',
            permission_classes=[permissions.IsAuthenticated, IsITTeamOrAdmin])
    def assign(self, request, pk=None):
        """Assign an engineer to a ticket."""
        ticket = self.get_object()
        engineer_id = request.data.get('engineer')
        if not engineer_id:
            return Response({'detail': 'engineer field is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            engineer = Employee.objects.get(pk=engineer_id)
        except Employee.DoesNotExist:
            return Response({'detail': 'Engineer not found.'}, status=status.HTTP_404_NOT_FOUND)
        ticket = assign_ticket(ticket, engineer, user=request.user, request=request)
        return Response(SupportTicketSerializer(ticket).data)


# ─────────────────────────────────────────────
# Software License
# ─────────────────────────────────────────────

class SoftwareLicenseViewSet(viewsets.ModelViewSet):
    """
    CRUD for software licenses. IT/Admin manage; all authenticated can view.
    """
    queryset = SoftwareLicense.objects.select_related('assigned_employee').all()
    serializer_class = SoftwareLicenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['software_name', 'vendor', 'license_key']
    filterset_fields = ['status', 'license_type', 'assigned_employee']
    ordering_fields = ['software_name', 'expiry_date', 'created_at']
    ordering = ['software_name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy',
                           'assign_license', 'revoke_license']:
            return [permissions.IsAuthenticated(), IsITTeamOrAdmin()]
        return [permissions.IsAuthenticated()]

    @action(detail=True, methods=['put'], url_path='assign')
    def assign_license(self, request, pk=None):
        """Assign a software license to an employee."""
        license_obj = self.get_object()
        serializer = LicenseAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        license_obj.assigned_employee = serializer.validated_data['employee']
        license_obj.status = 'active'
        license_obj.save(update_fields=['assigned_employee', 'status'])
        return Response(SoftwareLicenseSerializer(license_obj).data)

    @action(detail=True, methods=['put'], url_path='revoke')
    def revoke_license(self, request, pk=None):
        """Revoke a software license."""
        license_obj = self.get_object()
        license_obj.assigned_employee = None
        license_obj.status = 'revoked'
        license_obj.save(update_fields=['assigned_employee', 'status'])
        return Response(SoftwareLicenseSerializer(license_obj).data)

    @action(detail=False, methods=['get'], url_path='expiring-soon',
            permission_classes=[permissions.IsAuthenticated, IsITOrHROrAdmin])
    def expiring_soon(self, request):
        """List licenses expiring within the next 30 days."""
        today = datetime.date.today()
        threshold = today + datetime.timedelta(days=30)
        qs = SoftwareLicense.objects.filter(
            expiry_date__lte=threshold,
            expiry_date__gte=today,
            status='active',
        ).select_related('assigned_employee')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


# ─────────────────────────────────────────────
# Dashboard API
# ─────────────────────────────────────────────

class AssetDashboardView(APIView):
    """
    GET /api/v1/assets/dashboard/
    Returns high-level asset management KPIs.
    """
    permission_classes = [permissions.IsAuthenticated, IsITOrHROrAdmin]

    def get(self, request):
        today = datetime.date.today()
        expiry_threshold = today + datetime.timedelta(days=30)

        # Assets by status
        asset_counts = Asset.objects.values('status').annotate(count=Count('id'))
        by_status = {row['status']: row['count'] for row in asset_counts}

        # Assets by category
        by_category = list(
            Asset.objects.values('category__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # Support tickets
        ticket_stats = SupportTicket.objects.aggregate(
            open=Count('id', filter=Q(status='open')),
            in_progress=Count('id', filter=Q(status='in_progress')),
            resolved=Count('id', filter=Q(status='resolved')),
            closed=Count('id', filter=Q(status='closed')),
        )

        # Tickets by priority
        by_priority = list(
            SupportTicket.objects.values('priority')
            .annotate(count=Count('id'))
        )

        # Expiring licenses
        expiring_licenses = SoftwareLicense.objects.filter(
            expiry_date__lte=expiry_threshold,
            expiry_date__gte=today,
            status='active',
        ).count()

        # Maintenance requests
        maintenance_count = AssetMaintenance.objects.filter(
            status__in=['scheduled', 'in_progress']
        ).count()

        return Response({
            'assets': {
                'total': Asset.objects.count(),
                'available': by_status.get('available', 0),
                'assigned': by_status.get('assigned', 0),
                'under_maintenance': by_status.get('under_maintenance', 0),
                'retired': by_status.get('retired', 0),
                'by_category': by_category,
            },
            'support_tickets': {
                **ticket_stats,
                'by_priority': by_priority,
            },
            'maintenance_requests': maintenance_count,
            'expiring_licenses_next_30_days': expiring_licenses,
        })


# ─────────────────────────────────────────────
# Reports
# ─────────────────────────────────────────────

class AssetReportView(APIView):
    """
    GET /api/v1/assets/reports/assets/?format=pdf|excel|csv
    GET /api/v1/assets/reports/support/?format=pdf|excel|csv
    GET /api/v1/assets/reports/licenses/?format=pdf|excel|csv
    """
    permission_classes = [permissions.IsAuthenticated, IsITOrHROrAdmin]

    def get(self, request, report_type='assets'):
        fmt = request.query_params.get('format', 'pdf').lower()

        if report_type == 'assets':
            qs = Asset.objects.select_related('category').all()
            generators = {
                'pdf': generate_asset_report_pdf,
                'excel': generate_asset_report_excel,
                'csv': generate_asset_report_csv,
            }
        elif report_type == 'support':
            qs = SupportTicket.objects.select_related('employee', 'assigned_engineer').all()
            generators = {
                'pdf': generate_support_report_pdf,
                'excel': generate_support_report_excel,
                'csv': generate_support_report_csv,
            }
        elif report_type == 'licenses':
            qs = SoftwareLicense.objects.select_related('assigned_employee').all()
            generators = {
                'pdf': generate_license_report_pdf,
                'excel': generate_license_report_excel,
                'csv': generate_license_report_csv,
            }
        else:
            return Response({'detail': 'Unknown report type.'}, status=status.HTTP_400_BAD_REQUEST)

        if fmt not in generators:
            return Response(
                {'detail': f"Unsupported format '{fmt}'. Use pdf, excel, or csv."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return generators[fmt](qs)
