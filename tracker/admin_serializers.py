from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import License, Certificate, Notification, AdminSetting

User = get_user_model()


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
        )


class AdminLicenseSerializer(serializers.ModelSerializer):
    owner = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = License
        fields = (
            "id",
            "name",        # title
            "owner",
            "issued_by",
            "issue_date",
            "expiry_date",
        )


class AdminCertificateSerializer(serializers.ModelSerializer):
    owner = serializers.CharField(source="owner.username", read_only=True)
    category = serializers.CharField(
        source="category.name",
        default="-",
        read_only=True
    )

    class Meta:
        model = Certificate
        fields = (
            "id",
            "title",
            "owner",
            "category",
            "issued_date",
            "expiry_date",
        )

class AdminNotificationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    document_type = serializers.SerializerMethodField()
    document_title = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            "id",
            "username",
            "email",
            "message",
            "document_type",
            "document_title",
            "is_read",
            "sent_at",
            "tag",
        )

    def get_document_type(self, obj):
        return "Certificate" if obj.certificate else None

    def get_document_title(self, obj):
        return obj.certificate.title if obj.certificate else None

class AdminSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminSetting
        fields = (
            "default_notify_days",
            "email_notifications_enabled",
            "sms_notifications_enabled",
            "updated_at",
        )