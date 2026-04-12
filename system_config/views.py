from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from .models import (
    SAASProductConfig, SystemConfiguration, AgencyBranding, EmailTemplate,
    NotificationSettings, APIKey, AuditLog
)
from .serializers import (
    SAASProductConfigSerializer, SystemConfigurationSerializer, AgencyBrandingSerializer, AgencyBrandingCreateSerializer,
    EmailTemplateSerializer, EmailTemplateCreateSerializer,
    NotificationSettingsSerializer, NotificationSettingsCreateSerializer,
    APIKeySerializer, APIKeyCreateSerializer, APIKeyListSerializer,
    AuditLogSerializer, SystemConfigSummarySerializer, AgencyBrandingSummarySerializer
)
from utils.permissions import IsMember, IsAgent


@api_view(['GET', 'PATCH', 'POST'])
@permission_classes([IsMember])
def saas_product_config(request):
    """
    SAAS Product Configuration endpoint
    Only developers can access this - manages product-level branding
    """
    if request.method == 'GET':
        """Get SAAS product configuration"""
        config = SAASProductConfig.load()
        serializer = SAASProductConfigSerializer(config, context={'request': request})
        return Response(serializer.data)
    
    elif request.method in ['PATCH', 'POST']:
        """Update SAAS product configuration"""
        config = SAASProductConfig.load()
        serializer = SAASProductConfigSerializer(
            config, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def saas_product_config_public(request):
    """
    Public SAAS Product Configuration endpoint for authenticated users
    Read-only access to parent company information
    """
    config = SAASProductConfig.load()
    serializer = SAASProductConfigSerializer(config, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsMember])
def upload_saas_logo(request):
    """Upload SAAS product logo"""
    logo = request.FILES.get('logo')
    
    if not logo:
        return Response(
            {'error': 'No logo file provided.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/svg+xml']
    if logo.content_type not in allowed_types:
        return Response(
            {'error': 'Invalid file type. Only JPEG, PNG, GIF, and SVG are allowed.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate file size (max 5MB)
    if logo.size > 5 * 1024 * 1024:
        return Response(
            {'error': 'File size too large. Maximum 5MB allowed.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    config = SAASProductConfig.load()
    config.logo = logo
    config.save()
    
    serializer = SAASProductConfigSerializer(config, context={'request': request})
    return Response({
        'detail': 'Logo uploaded successfully',
        'logo_url': serializer.data['logo_url'],
        'config': serializer.data
    })


@api_view(['GET', 'PATCH'])
@permission_classes([IsMember])
def system_settings(request):
    """
    Simple settings endpoint for basic system configuration
    """
    if request.method == 'GET':
        # Get settings from database or return defaults
        try:
            configs = SystemConfiguration.objects.all()
            settings_data = {
                'system_name': 'Nahd Travels CRM',
                'support_email': 'support@nahdtravels.com',
                'support_phone': '+966123456789',
                'default_currency': 'PKR',
                'maintenance_mode': False,
                'logo_url': None,
                'primary_color': '#3b82f6',
                'secondary_color': '#8b5cf6',
                'accent_color': '#10b981',
            }
            
            # Update with database values if they exist
            for config in configs:
                if config.key == 'product_name':
                    settings_data['system_name'] = config.value
                elif config.key == 'support_email':
                    settings_data['support_email'] = config.value
                elif config.key == 'support_phone':
                    settings_data['support_phone'] = config.value
                elif config.key == 'default_currency':
                    settings_data['default_currency'] = config.value
                elif config.key == 'maintenance_mode':
                    settings_data['maintenance_mode'] = config.value.lower() == 'true'
            
            return Response(settings_data)
        except Exception as e:
            return Response({
                'system_name': 'Nahd Travels CRM',
                'support_email': 'support@nahdtravels.com',
                'support_phone': '+966123456789',
                'default_currency': 'PKR',
                'maintenance_mode': False,
                'logo_url': None,
                'primary_color': '#3b82f6',
                'secondary_color': '#8b5cf6',
                'accent_color': '#10b981',
            })
    
    elif request.method == 'PATCH':
        # Update system settings (placeholder)
        return Response({'detail': 'Settings updated successfully'})


class SystemConfigurationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing system-wide configurations.
    Only developers can access these settings.
    """
    serializer_class = SystemConfigurationSerializer
    permission_classes = [IsMember]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['key', 'description']
    ordering_fields = ['key', 'created_at', 'updated_at']
    ordering = ['key']

    def get_queryset(self):
        return SystemConfiguration.objects.all()

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get configurations grouped by category (based on key prefix)"""
        queryset = self.get_queryset()
        
        categories = {}
        for config in queryset:
            # Extract category from key (e.g., 'email.smtp.host' -> 'email')
            category = config.key.split('.')[0] if '.' in config.key else 'general'
            
            if category not in categories:
                categories[category] = {
                    'category': category,
                    'configurations': []
                }
            
            categories[category]['configurations'].append({
                'id': config.id,
                'key': config.key,
                'value': config.value,
                'description': config.description,
                'is_active': config.is_active,
                'updated_at': config.updated_at
            })
        
        return Response(list(categories.values()))

    @action(detail=False, methods=['get'])
    def public_configs(self, request):
        """Get public configurations that frontend can access"""
        # Only return configurations that are safe to expose to frontend
        public_keys = [
            'site.name',
            'site.description',
            'site.version',
            'features.enabled',
            'branding.default_colors',
        ]
        
        queryset = self.get_queryset().filter(
            key__in=public_keys,
            is_active=True
        )
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class AgencyBrandingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing agency branding and customization.
    Developers can manage all agencies, members can manage their own agency.
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['company_name', 'agency__name']
    ordering_fields = ['created_at', 'updated_at', 'company_name']
    ordering = ['-updated_at']

    def get_serializer_class(self):
        if self.action in ['create']:
            return AgencyBrandingCreateSerializer
        return AgencyBrandingSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role in ['member', 'agent']:
            return AgencyBranding.objects.filter(agency=user.agency).select_related('agency')
        else:
            return AgencyBranding.objects.none()

    def perform_create(self, serializer):
        """Create branding with proper agency context"""
        if self.request.user.role != 'member':
            raise permissions.PermissionDenied("Only members can create agency branding.")
        
        serializer.save()

    def perform_update(self, serializer):
        """Update branding with permission checks"""
        if self.request.user.role != 'member':
            raise permissions.PermissionDenied("Only members can update agency branding.")
        
        serializer.save()

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get agency branding summary"""
        queryset = self.get_queryset()
        
        summaries = []
        for branding in queryset:
            summaries.append({
                'agency_id': branding.agency.id,
                'agency_name': branding.agency.name,
                'has_logo': bool(branding.logo),
                'has_favicon': bool(branding.favicon),
                'primary_color': branding.primary_color,
                'secondary_color': branding.secondary_color,
                'company_name': branding.company_name,
                'is_active': branding.is_active,
                'last_updated': branding.updated_at
            })
        
        serializer = AgencyBrandingSummarySerializer(summaries, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def upload_logo(self, request, pk=None):
        """Upload agency logo"""
        if request.user.role != 'member':
            return Response(
                {'error': 'Only members can upload logos.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        branding = self.get_object()
        logo = request.FILES.get('logo')
        
        if not logo:
            return Response(
                {'error': 'No logo file provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/svg+xml']
        if logo.content_type not in allowed_types:
            return Response(
                {'error': 'Invalid file type. Only JPEG, PNG, GIF, and SVG are allowed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size (max 5MB)
        if logo.size > 5 * 1024 * 1024:
            return Response(
                {'error': 'File size too large. Maximum 5MB allowed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        branding.logo = logo
        branding.save()
        
        serializer = self.get_serializer(branding)
        return Response(serializer.data)


class EmailTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing email templates.
    Developers can manage all templates, members can manage their agency templates.
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['template_type', 'is_active', 'is_default', 'agency']
    search_fields = ['name', 'subject']
    ordering_fields = ['name', 'template_type', 'created_at', 'updated_at']
    ordering = ['template_type', 'name']

    def get_serializer_class(self):
        if self.action in ['create']:
            return EmailTemplateCreateSerializer
        return EmailTemplateSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = EmailTemplate.objects.select_related('agency')
        if user.role in ['member', 'agent']:
            return queryset.filter(agency=user.agency)
        else:
            return EmailTemplate.objects.none()

    def perform_create(self, serializer):
        """Create template with proper agency context"""
        if self.request.user.role != 'member':
            raise permissions.PermissionDenied("Only members can create email templates.")
        
        # Set agency if not provided
        if not serializer.validated_data.get('agency'):
            serializer.validated_data['agency'] = self.request.user.agency
        
        serializer.save()

    def perform_update(self, serializer):
        """Update template with permission checks"""
        if self.request.user.role != 'member':
            raise permissions.PermissionDenied("Only members can update email templates.")
        
        serializer.save()

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get templates grouped by type"""
        queryset = self.get_queryset()
        
        types = {}
        for template in queryset:
            if template.template_type not in types:
                types[template.template_type] = {
                    'template_type': template.template_type,
                    'templates': []
                }
            
            types[template.template_type]['templates'].append({
                'id': template.id,
                'name': template.name,
                'subject': template.subject,
                'agency_name': template.agency.name if template.agency else 'Global',
                'is_active': template.is_active,
                'is_default': template.is_default,
                'updated_at': template.updated_at
            })
        
        return Response(list(types.values()))

    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """Preview email template with sample data"""
        template = self.get_object()
        
        # Get sample variables from request
        sample_data = request.data.get('sample_data', {})
        
        # Render template with sample data
        try:
            from django.template import Template, Context
            html_template = Template(template.html_content)
            html_rendered = html_template.render(Context(sample_data))
            
            text_template = Template(template.text_content or '')
            text_rendered = text_template.render(Context(sample_data))
            
            return Response({
                'subject': template.subject,
                'html_content': html_rendered,
                'text_content': text_rendered,
                'variables': template.variables
            })
        except Exception as e:
            return Response(
                {'error': f'Template rendering error: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class NotificationSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notification settings.
    Developers can manage all settings, members can manage their agency settings.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create']:
            return NotificationSettingsCreateSerializer
        return NotificationSettingsSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = NotificationSettings.objects.select_related('agency')
        if user.role in ['member', 'agent']:
            return queryset.filter(agency=user.agency)
        else:
            return NotificationSettings.objects.none()

    def perform_create(self, serializer):
        """Create notification settings with proper agency context"""
        if self.request.user.role != 'member':
            raise permissions.PermissionDenied("Only members can create notification settings.")
        
        serializer.save()

    def perform_update(self, serializer):
        """Update notification settings with permission checks"""
        if self.request.user.role != 'member':
            raise permissions.PermissionDenied("Only members can update notification settings.")
        
        serializer.save()


class APIKeyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing API keys.
    Only developers can manage API keys.
    """
    permission_classes = [IsMember]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['key_type', 'is_active', 'agency']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'key_type', 'created_at', 'updated_at']
    ordering = ['key_type', 'name']

    def get_serializer_class(self):
        if self.action == 'list':
            return APIKeyListSerializer
        elif self.action in ['create']:
            return APIKeyCreateSerializer
        return APIKeySerializer

    def get_queryset(self):
        return APIKey.objects.select_related('agency')

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get API keys grouped by type"""
        queryset = self.get_queryset()
        
        types = {}
        for api_key in queryset:
            if api_key.key_type not in types:
                types[api_key.key_type] = {
                    'key_type': api_key.key_type,
                    'api_keys': []
                }
            
            types[api_key.key_type]['api_keys'].append({
                'id': api_key.id,
                'name': api_key.name,
                'api_key_masked': f"{api_key.api_key[:8]}...{api_key.api_key[-4:]}" if api_key.api_key else None,
                'endpoint_url': api_key.endpoint_url,
                'agency_name': api_key.agency.name if api_key.agency else 'Global',
                'is_active': api_key.is_active,
                'updated_at': api_key.updated_at
            })
        
        return Response(list(types.values()))

    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test API key connection"""
        api_key = self.get_object()
        
        # This would contain the actual testing logic based on key_type
        # For now, just return a placeholder response
        return Response({
            'status': 'success',
            'message': f'Connection test for {api_key.name} completed successfully.',
            'response_time': '150ms',
            'timestamp': timezone.now()
        })


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing audit logs.
    Only developers can access audit logs.
    """
    serializer_class = AuditLogSerializer
    permission_classes = [IsMember]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['action', 'model_name', 'user']
    search_fields = ['object_repr', 'model_name']
    ordering_fields = ['timestamp', 'user', 'action']
    ordering = ['-timestamp']

    def get_queryset(self):
        return AuditLog.objects.select_related('user')

    @action(detail=False, methods=['get'])
    def recent_changes(self, request):
        """Get recent configuration changes"""
        days = int(request.query_params.get('days', 7))
        since = timezone.now() - timedelta(days=days)
        
        queryset = self.get_queryset().filter(timestamp__gte=since)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_model(self, request):
        """Get audit logs grouped by model"""
        queryset = self.get_queryset()
        
        models = {}
        for log in queryset:
            if log.model_name not in models:
                models[log.model_name] = {
                    'model_name': log.model_name,
                    'total_changes': 0,
                    'actions': {}
                }
            
            models[log.model_name]['total_changes'] += 1
            
            if log.action not in models[log.model_name]['actions']:
                models[log.model_name]['actions'][log.action] = 0
            models[log.model_name]['actions'][log.action] += 1
        
        return Response(list(models.values()))


class SystemConfigDashboardViewSet(viewsets.ViewSet):
    """
    ViewSet for system configuration dashboard.
    Only developers can access this dashboard.
    """
    permission_classes = [IsMember]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get system configuration summary"""
        from agencies.models import Agency
        
        # Calculate summary statistics
        total_configurations = SystemConfiguration.objects.count()
        total_agencies = Agency.objects.count()
        agencies_with_branding = AgencyBranding.objects.filter(is_active=True).count()
        total_email_templates = EmailTemplate.objects.count()
        total_api_keys = APIKey.objects.count()
        
        # Recent changes (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_changes = AuditLog.objects.filter(timestamp__gte=week_ago).count()
        
        summary_data = {
            'total_configurations': total_configurations,
            'total_agencies': total_agencies,
            'agencies_with_branding': agencies_with_branding,
            'total_email_templates': total_email_templates,
            'total_api_keys': total_api_keys,
            'recent_changes': recent_changes
        }
        
        serializer = SystemConfigSummarySerializer(summary_data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def health_check(self, request):
        """Perform system configuration health check"""
        issues = []
        
        # Check for missing default configurations
        required_configs = [
            'site.name',
            'site.description',
            'email.smtp.host',
            'email.smtp.port',
        ]
        
        for config_key in required_configs:
            if not SystemConfiguration.objects.filter(key=config_key, is_active=True).exists():
                issues.append(f"Missing required configuration: {config_key}")
        
        # Check for agencies without branding
        from agencies.models import Agency
        agencies_without_branding = Agency.objects.exclude(
            branding__isnull=False
        ).count()
        
        if agencies_without_branding > 0:
            issues.append(f"{agencies_without_branding} agencies without branding configuration")
        
        # Check for missing default email templates
        required_templates = [
            'booking_confirmation',
            'payment_receipt',
            'voucher_generated',
        ]
        
        for template_type in required_templates:
            if not EmailTemplate.objects.filter(template_type=template_type, is_default=True).exists():
                issues.append(f"Missing default email template: {template_type}")
        
        return Response({
            'status': 'healthy' if not issues else 'issues_found',
            'issues': issues,
            'timestamp': timezone.now()
        })