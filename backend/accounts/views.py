from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User
from .serializers import UserSerializer, UserCreateSerializer, PasswordChangeSerializer
from agencies.models import Agency
from system_config.models import AgencyBranding
from system_config.serializers import AgencyBrandingSerializer, AgencyBrandingCreateSerializer
from utils.permissions import IsDeveloper, IsMember, IsAgent
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_user(request):
    """
    Get current authenticated user profile
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer to include user role and agency info"""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['role'] = user.role
        token['agency_id'] = user.agency.id if user.agency else None
        token['agency_name'] = user.agency.name if user.agency else None
        token['full_name'] = user.full_name
        
        return token


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token view using our serializer"""
    serializer_class = CustomTokenObtainPairSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users.
    Developers can manage all users, members can manage their agency users.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['role', 'is_active', 'agency']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering_fields = ['username', 'first_name', 'last_name', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'developer':
            return User.objects.select_related('agency')
        elif user.role == 'member':
            return User.objects.filter(agency=user.agency).select_related('agency')
        else:
            return User.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer
    
    def perform_create(self, serializer):
        """Create user with proper agency context"""
        if self.request.user.role not in ['developer', 'member']:
            raise permissions.PermissionDenied("Only developers and members can create users.")
        
        # Set agency if not provided and user is member/agent
        if not serializer.validated_data.get('agency') and self.request.user.role in ['member', 'agent']:
            serializer.validated_data['agency'] = self.request.user.agency
        
        serializer.save()

    def perform_update(self, serializer):
        """Update user with permission checks"""
        if self.request.user.role not in ['developer', 'member']:
            raise permissions.PermissionDenied("Only developers and members can update users.")
        
        serializer.save()

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['patch'])
    def update_me(self, request):
        """Update current user profile"""
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user password"""
        serializer = PasswordChangeSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if user.check_password(serializer.validated_data['old_password']):
                user.set_password(serializer.validated_data['new_password'])
                user.save()
                return Response({'detail': 'Password changed successfully'})
            else:
                return Response(
                    {'old_password': ['Wrong password.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def request_password_reset(request):
    """
    Request password reset email
    """
    email = request.data.get('email')
    if not email:
        return Response(
            {'email': ['This field is required.']},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Don't reveal if email exists or not
        return Response({'detail': 'Password reset email sent'})
    
    # Generate reset token
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # Create reset URL
    reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"
    
    # Send email
    try:
        send_mail(
            'Password Reset Request',
            f'Click the link to reset your password: {reset_url}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return Response({'detail': 'Password reset email sent'})
    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}")
        return Response(
            {'detail': 'Failed to send password reset email'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def reset_password(request):
    """
    Reset password with token
    """
    uid = request.data.get('uid')
    token = request.data.get('token')
    new_password = request.data.get('new_password')
    
    if not all([uid, token, new_password]):
        return Response(
            {'detail': 'Missing required fields'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        uid = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response(
            {'detail': 'Invalid reset link'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not default_token_generator.check_token(user, token):
        return Response(
            {'detail': 'Invalid or expired reset link'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user.set_password(new_password)
    user.save()
    
    return Response({'detail': 'Password reset successfully'})


class MemberProfileView(APIView):
    """
    Member profile management using AgencyBranding model
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get member profile (agency branding)"""
        try:
            user = request.user
            
            if user.role not in ['member', 'agent']:
                return Response(
                    {'detail': 'Only members and agents can access profile'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if not user.agency:
                return Response(
                    {'detail': 'User is not associated with any agency'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get or create agency branding
            branding, created = AgencyBranding.objects.get_or_create(
                agency=user.agency,
                defaults={
                    'company_name': user.agency.name,
                    'phone': user.agency.phone,
                    'email': user.agency.email,
                    'address': user.agency.address,
                }
            )
            
            serializer = AgencyBrandingSerializer(branding, context={'request': request})
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error getting member profile: {e}")
            return Response(
                {'detail': 'Failed to get profile'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        """Create or update member profile (agency branding)"""
        try:
            user = request.user
            if user.role not in ['member', 'agent']:
                return Response(
                    {'detail': 'Only members and agents can update profile'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if not user.agency:
                return Response(
                    {'detail': 'User is not associated with any agency'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get or create agency branding
            branding, created = AgencyBranding.objects.get_or_create(
                agency=user.agency,
                defaults={
                    'company_name': user.agency.name,
                    'phone': user.agency.phone,
                    'email': user.agency.email,
                    'address': user.agency.address,
                }
            )
            
            # Update branding with provided data
            serializer = AgencyBrandingCreateSerializer(
                branding, 
                data=request.data, 
                partial=True,
                context={'request': request}
            )
            
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Error updating member profile: {e}")
            return Response(
                {'detail': 'Failed to update profile'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def generate_voucher_number(request):
    """Generate next voucher number for the agency"""
    try:
        user = request.user
        if user.role not in ['member', 'agent']:
            return Response(
                {'detail': 'Only members and agents can generate voucher numbers'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not user.agency:
            return Response(
                {'detail': 'User is not associated with any agency'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Import here to avoid circular imports
        from bookings.models import VoucherSequence
        
        # Get or create voucher sequence for this agency
        sequence, created = VoucherSequence.objects.get_or_create(
            agency=user.agency,
            defaults={'current_sequence': 0}
        )
        
        # Generate next voucher number
        voucher_number = sequence.get_next_voucher_number()
        
        return Response({
            'voucher_number': voucher_number,
            'manual_number': voucher_number,  # Same as voucher number
            'sequence': sequence.current_sequence
        })
        
    except Exception as e:
        logger.error(f"Error generating voucher number: {e}")
        return Response(
            {'detail': 'Failed to generate voucher number'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_logo(request):
    """Upload agency logo"""
    try:
        user = request.user
        if user.role not in ['member', 'agent']:
            return Response(
                {'detail': 'Only members and agents can upload logos'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not user.agency:
            return Response(
                {'detail': 'User is not associated with any agency'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get or create agency branding
        branding, created = AgencyBranding.objects.get_or_create(
            agency=user.agency,
            defaults={
                'company_name': user.agency.name,
                'phone': user.agency.phone,
                'email': user.agency.email,
                'address': user.agency.address,
            }
        )
        
        logo = request.FILES.get('logo')
        if not logo:
            return Response(
                {'detail': 'No logo file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/svg+xml']
        if logo.content_type not in allowed_types:
            return Response(
                {'detail': 'Invalid file type. Only JPEG, PNG, GIF, and SVG are allowed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate file size (max 5MB)
        if logo.size > 5 * 1024 * 1024:
            return Response(
                {'detail': 'File size too large. Maximum 5MB allowed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        branding.logo = logo
        branding.save()
        
        serializer = AgencyBrandingSerializer(branding, context={'request': request})
        return Response({
            'detail': 'Logo uploaded successfully',
            'logo_url': branding.logo.url if branding.logo else None,
            'branding': serializer.data
        })
        
    except Exception as e:
        logger.error(f"Error uploading logo: {e}")
        return Response(
            {'detail': 'Failed to upload logo'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
