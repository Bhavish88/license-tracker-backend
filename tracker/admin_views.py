from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model

from .models import License, Certificate, Notification, AdminSetting
from .admin_serializers import (
    AdminUserSerializer,
    AdminLicenseSerializer,
    AdminCertificateSerializer,
    AdminNotificationSerializer,
    AdminSettingSerializer
)

User = get_user_model()


# ------------------------
# USERS
# ------------------------

@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_users_list(request):
    users = User.objects.all().order_by("-date_joined")
    serializer = AdminUserSerializer(users, many=True)
    return Response(serializer.data)


@api_view(["DELETE"])
@permission_classes([IsAdminUser])
def admin_delete_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {"detail": "User not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    user.delete()
    return Response(
        {"message": "User deleted successfully"},
        status=status.HTTP_204_NO_CONTENT
    )


# ------------------------
# LICENSES
# ------------------------

@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_licenses_list(request):
    licenses = License.objects.select_related("owner").all()
    serializer = AdminLicenseSerializer(licenses, many=True)
    return Response(serializer.data)


# ------------------------
# CERTIFICATES
# ------------------------

@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_certificates_list(request):
    certificates = Certificate.objects.select_related(
        "owner", "category"
    ).all()
    serializer = AdminCertificateSerializer(certificates, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def admin_notifications_list(request):
    """
    Admin-only, read-only endpoint to view all notifications system-wide.
    Supports filtering, search, and sorting.
    """

    qs = Notification.objects.select_related("user", "certificate").all()

    # --- filters ---
    user_id = request.query_params.get("user")
    status = request.query_params.get("status")  # read | unread
    notif_type = request.query_params.get("type")
    search = request.query_params.get("search")

    if user_id:
        qs = qs.filter(user__id=user_id)

    if status == "read":
        qs = qs.filter(is_read=True)
    elif status == "unread":
        qs = qs.filter(is_read=False)

    if notif_type:
        qs = qs.filter(tag__icontains=notif_type)

    if search:
        qs = qs.filter(
            user__username__icontains=search
        ) | qs.filter(
            message__icontains=search
        )

    qs = qs.order_by("-sent_at")

    serializer = AdminNotificationSerializer(qs, many=True)
    return Response(serializer.data)

@api_view(["GET", "PUT"])
@permission_classes([IsAdminUser])
def admin_settings(request):
    """
    Admin Settings:
    - System configuration (editable)
    - Admin profile info (read-only)
    """

    settings_obj, _ = AdminSetting.objects.get_or_create(id=1)

    admin_user = request.user

    if request.method == "GET":
        settings_data = AdminSettingSerializer(settings_obj).data

        profile_data = {
            "username": admin_user.username,
            "email": admin_user.email,
            "role": "Superuser" if admin_user.is_superuser else "Staff",
            "last_login": admin_user.last_login,
        }

        return Response({
            "system_settings": settings_data,
            "admin_profile": profile_data,
        })

    # PUT → update system settings only
    serializer = AdminSettingSerializer(
        settings_obj, data=request.data, partial=True
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(serializer.data)