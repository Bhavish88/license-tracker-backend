from rest_framework import viewsets, decorators, response, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.utils import timezone
from .models import Category, Certificate, License, Notification, ActivityLog, Setting, Profile
from .serializers import CategorySerializer, CertificateSerializer, LicenseSerializer, NotificationSerializer, ActivityLogSerializer
from .serializers import DashboardSummarySerializer , RegisterSerializer, ProfileSerializer, SettingSerializer
from .serializers import PasswordResetSerializer, PasswordResetConfirmSerializer, ChangePasswordSerializer
from rest_framework.pagination import PageNumberPagination
from .permissions import IsOwner
from django.core.exceptions import FieldError
from .throttling import BurstRateThrottle, SustainedRateThrottle, APIKeyRateThrottle
import os
from django.conf import settings
from django.http import FileResponse, Http404
from drf_spectacular.utils import extend_schema
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.core.mail import send_mail
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer

User = get_user_model()


@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_dashboard_summary(request):
    return Response({
        "total_users": User.objects.count(),
        "total_certificates": Certificate.objects.count(),
        "total_licenses": License.objects.count(),
        "total_categories": Category.objects.count(),
    })


@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_recent_activity(request):
    logs = ActivityLog.objects.select_related("user").order_by("-created_at")[:5]
    serializer = ActivityLogSerializer(logs, many=True)
    return Response(serializer.data)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data["current_password"]):
            return Response(
                {"detail": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(serializer.validated_data["new_password"])
        user.save()

        return Response(
            {"message": "Password updated successfully."},
            status=status.HTTP_200_OK
        )


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    serializer = RegisterSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)


token_generator = PasswordResetTokenGenerator()


class PasswordResetView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        user = User.objects.filter(email=email).first()

        if user:
            token = token_generator.make_token(user)
            uid = user.pk

            reset_link = f"http://localhost:5500/reset-password.html?uid={uid}&token={token}"

            send_mail(
                subject="Reset your DocuVault password",
                message=f"Click the link to reset your password:\n\n{reset_link}",
                from_email=None,
                recipient_list=[email],
                fail_silently=True,
            )

        return Response(
            {"message": "If this email exists, a password reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uid = serializer.validated_data["uid"]
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        user = User.objects.filter(pk=uid).first()

        if not user or not token_generator.check_token(user, token):
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        return Response(
            {"message": "Password has been reset successfully."},
            status=status.HTTP_200_OK
        )


class IsOwnerPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        try:
            return obj.owner == request.user
        except AttributeError:
            return False


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        if self.request.user and (self.request.user.is_staff or self.request.user.is_superuser):
            return self.queryset
        model = self.queryset.model
        field_names = [f.name for f in model._meta.get_fields()]
        q = self.queryset
        if 'owner' in field_names:
            return q.filter(owner=self.request.user)
        if 'user' in field_names:
            return q.filter(user=self.request.user)
        if 'created_by' in field_names:
            return q.filter(created_by=self.request.user)
        return q.none()

    def perform_create(self, serializer):
        try:
            serializer.save(owner=self.request.user)
        except TypeError:
            try:
                serializer.save(user=self.request.user)
            except TypeError:
                try:
                    serializer.save(created_by=self.request.user)
                except TypeError:
                    serializer.save()


class CertificateViewSet(viewsets.ModelViewSet):
    queryset = Certificate.objects.all()
    serializer_class = CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    throttle_classes = [BurstRateThrottle, SustainedRateThrottle, APIKeyRateThrottle]

    def get_queryset(self):
        if self.request.user and (self.request.user.is_staff or self.request.user.is_superuser):
            return self.queryset
        model = self.queryset.model
        field_names = [f.name for f in model._meta.get_fields()]
        q = self.queryset
        if 'owner' in field_names:
            return q.filter(owner=self.request.user)
        if 'user' in field_names:
            return q.filter(user=self.request.user)
        if 'created_by' in field_names:
            return q.filter(created_by=self.request.user)
        return q.none()

    def perform_create(self, serializer):
        try:
            serializer.save(owner=self.request.user)
        except TypeError:
            try:
                serializer.save(user=self.request.user)
            except TypeError:
                try:
                    serializer.save(created_by=self.request.user)
                except TypeError:
                    serializer.save()

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        cert = self.get_object()
        cert.is_active = not cert.is_active
        cert.save()
        return Response({'id': cert.id, 'is_active': cert.is_active})

    @action(
        detail=True,
        methods=['get'],
        url_path='download',
        permission_classes=[permissions.IsAuthenticated, IsOwner]
    )
    def download(self, request, pk=None):
        cert = self.get_object()

        file_field = getattr(cert, "file", None)
        if not file_field:
            raise Http404("No file attached to this certificate.")

        try:
            file_path = file_field.path
        except (ValueError, NotImplementedError, AttributeError):
            return Response(
                {"detail": "File is not stored locally; download not supported for this storage."},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )

        if not os.path.exists(file_path):
            raise Http404("File not found on server.")

        resp = FileResponse(open(file_path, "rb"))
        resp["Content-Length"] = os.path.getsize(file_path)
        resp["Content-Disposition"] = f'attachment; filename="{os.path.basename(file_path)}"'
        return resp


class LicenseViewSet(viewsets.ModelViewSet):
    queryset = License.objects.all()
    serializer_class = LicenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    throttle_classes = [BurstRateThrottle, SustainedRateThrottle, APIKeyRateThrottle]

    def get_queryset(self):
        if self.request.user and (self.request.user.is_staff or self.request.user.is_superuser):
            return self.queryset
        model = self.queryset.model
        field_names = [f.name for f in model._meta.get_fields()]
        q = self.queryset
        if 'owner' in field_names:
            return q.filter(owner=self.request.user)
        if 'user' in field_names:
            return q.filter(user=self.request.user)
        if 'created_by' in field_names:
            return q.filter(created_by=self.request.user)
        return q.none()

    def perform_create(self, serializer):
        try:
            serializer.save(owner=self.request.user)
        except TypeError:
            try:
                serializer.save(user=self.request.user)
            except TypeError:
                try:
                    serializer.save(created_by=self.request.user)
                except TypeError:
                    serializer.save()

    @action(
        detail=True,
        methods=['get'],
        url_path='download',
        permission_classes=[permissions.IsAuthenticated, IsOwner]
    )
    def download(self, request, pk=None):
        lic = self.get_object()

        file_field = getattr(lic, "file", None)
        if not file_field:
            raise Http404("No file attached to this license.")

        try:
            file_path = file_field.path
        except (ValueError, NotImplementedError, AttributeError):
            return Response(
                {"detail": "File is not stored locally; download not supported for this storage."},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )

        if not os.path.exists(file_path):
            raise Http404("File not found on server.")

        resp = FileResponse(open(file_path, "rb"))
        resp["Content-Length"] = os.path.getsize(file_path)
        resp["Content-Disposition"] = f'attachment; filename="{os.path.basename(file_path)}"'
        return resp


def get_expiry_data_for_user(user):
    expired = []
    expiring_soon = []
    valid = []

    setting, _ = Setting.objects.get_or_create(user=user)
    default_days = setting.default_notify_days

    certs = Certificate.objects.filter(owner=user, expiry_date__isnull=False)
    for c in certs:
        days = c.days_until_expiry()
        notify_days = c.notify_before_days or default_days

        if days < 0:
            expired.append(c)
        elif days <= notify_days:
            expiring_soon.append(c)
        else:
            valid.append(c)

    licenses = License.objects.filter(owner=user, expiry_date__isnull=False)
    for l in licenses:
        days = l.days_until_expiry()
        notify_days = l.notify_before_days or default_days

        if days < 0:
            expired.append(l)
        elif days <= notify_days:
            expiring_soon.append(l)
        else:
            valid.append(l)

    return {
        "expired": expired,
        "expiring_soon": expiring_soon,
        "valid": valid,
    }


@extend_schema(
    responses=DashboardSummarySerializer,
    summary="Dashboard summary for the logged-in user",
    description="Returns totals, expired, expiring soon certificates and category breakdown."
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_summary(request):
    user = request.user

    expiry = get_expiry_data_for_user(user)

    total = (
        Certificate.objects.filter(owner=user).count() +
        License.objects.filter(owner=user).count()
    )

    by_category = {}
    for c in Certificate.objects.filter(owner=user):
        key = c.category.name if c.category else "Uncategorized"
        by_category[key] = by_category.get(key, 0) + 1

    return Response({
        "total": total,
        "expired": len(expiry["expired"]),
        "expiring_soon": len(expiry["expiring_soon"]),
        "by_category": by_category
    })


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Notification.objects.all().order_by('-sent_at')
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        if user and (user.is_staff or user.is_superuser):
            return self.queryset
        return self.queryset.filter(user=user)

    @decorators.action(detail=True, methods=['patch'], url_path='read')
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        if not notif.is_read:
            notif.is_read = True
            notif.save(update_fields=['is_read'])
        return response.Response(self.get_serializer(notif).data, status=status.HTTP_200_OK)

    @decorators.action(detail=True, methods=['patch'], url_path='unread')
    def mark_unread(self, request, pk=None):
        notif = self.get_object()
        if notif.is_read:
            notif.is_read = False
            notif.save(update_fields=['is_read'])
        return response.Response(self.get_serializer(notif).data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def expiry_tracker(request):
    user = request.user

    expired = []
    expiring_soon = []
    valid = []

    certs = Certificate.objects.filter(owner=user, expiry_date__isnull=False)
    for c in certs:
        days = c.days_until_expiry()
        item = {
            "type": "certificate",
            "id": c.id,
            "title": c.title,
            "expiry_date": c.expiry_date,
            "days_left": days,
        }

        if days < 0:
            expired.append(item)
        elif c.should_notify():
            expiring_soon.append(item)
        else:
            valid.append(item)

    licenses = License.objects.filter(owner=user, expiry_date__isnull=False)
    for l in licenses:
        days = l.days_until_expiry()
        item = {
            "type": "license",
            "id": l.id,
            "name": l.name,
            "expiry_date": l.expiry_date,
            "days_left": days,
        }

        if days < 0:
            expired.append(item)
        elif l.should_notify():
            expiring_soon.append(item)
        else:
            valid.append(item)

    return Response({
        "expired": expired,
        "expiring_soon": expiring_soon,
        "valid": valid,
    })


class SettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        setting, _ = Setting.objects.get_or_create(user=request.user)
        serializer = SettingSerializer(setting)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        setting, _ = Setting.objects.get_or_create(user=request.user)
        serializer = SettingSerializer(setting, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

from datetime import date
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse


@api_view(["GET"])
@permission_classes([AllowAny])
def send_reminders(request):
    return JsonResponse({"message": "Reminders sent"})