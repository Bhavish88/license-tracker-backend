import mimetypes
import re
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Category, Certificate, License, Notification, ActivityLog, Setting, Profile
)
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

# ==============================
# JWT
# ==============================
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["is_staff"] = user.is_staff
        token["is_superuser"] = user.is_superuser
        token["username"] = user.username
        return token


# ==============================
# REGISTER
# ==============================
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def validate_username(self, value):
        if " " in value:
            raise serializers.ValidationError("Username cannot contain spaces.")
        return value

    def create(self, validated_data):
        user = User(
            username=validated_data["username"],
            email=validated_data["email"]
        )
        user.set_password(validated_data["password"])
        user.save()
        return user


# ==============================
# PASSWORD RESET
# ==============================
class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.IntegerField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


# ==============================
# SIMPLE USER
# ==============================
class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email")


# ==============================
# CATEGORY
# ==============================
class CategorySerializer(serializers.ModelSerializer):
    owner = SimpleUserSerializer(read_only=True)

    class Meta:
        model = Category
        fields = ("id", "owner", "name", "description", "created_at")
        read_only_fields = ("id", "owner", "created_at")


# ==============================
# FILE VALIDATOR
# ==============================
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {"application/pdf", "image/png", "image/jpeg"}

def validate_certificate_file(file):
    if file.size > MAX_FILE_SIZE:
        raise serializers.ValidationError("File size must be 10 MB or less.")

    content_type = getattr(file, "content_type", None)
    if not content_type:
        content_type, _ = mimetypes.guess_type(file.name)

    if content_type not in ALLOWED_CONTENT_TYPES:
        raise serializers.ValidationError(
            "Unsupported file type. Allowed types: PDF, PNG, JPG/JPEG."
        )

    return file


# ==============================
# CERTIFICATE
# ==============================
class CertificateSerializer(serializers.ModelSerializer):
    owner = SimpleUserSerializer(read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    file = serializers.FileField(validators=[validate_certificate_file])

    class Meta:
        model = Certificate
        fields = (
            "id", "owner", "title", "category", "category_name", "file",
            "issued_date", "expiry_date", "notify_before_days",
            "is_active", "created_at", "updated_at"
        )
        read_only_fields = ("id", "owner", "created_at", "updated_at", "category_name")

    def validate(self, data):
        issued = data.get("issued_date", getattr(self.instance, "issued_date", None))
        expiry = data.get("expiry_date", getattr(self.instance, "expiry_date", None))
        notify_days = data.get("notify_before_days", getattr(self.instance, "notify_before_days", None))

        request = self.context.get("request")
        owner = request.user if request else None

        file = data.get("file")
        if owner and file:
            existing_files = Certificate.objects.filter(owner=owner).values_list("file", flat=True)
            existing_names = [f.split("/")[-1] for f in existing_files if f]

        if file.name in existing_names:
             raise serializers.ValidationError("You have already uploaded a certificate with this file name.")

        if issued and expiry and expiry < issued:
            raise serializers.ValidationError("expiry_date cannot be before issued_date.")

        if notify_days is not None and notify_days < 0:
            raise serializers.ValidationError("notify_before_days must be zero or positive.")

        title = data.get("title", getattr(self.instance, "title", None))
        if owner and issued and title:
            qs = Certificate.objects.filter(owner=owner, title=title, issued_date=issued)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("Certificate already exists.")

        return data


# ==============================
# LICENSE
# ==============================
class LicenseSerializer(serializers.ModelSerializer):
    owner = SimpleUserSerializer(read_only=True)
    file = serializers.FileField(required=False, allow_null=True, validators=[validate_certificate_file])

    class Meta:
        model = License
        fields = (
            "id", "owner", "name", "number", "issued_by",
            "issue_date", "expiry_date", "file", "created_at",
        )
        read_only_fields = ("id", "owner", "created_at")

    def validate(self, data):
        issue = data.get("issue_date", getattr(self.instance, "issue_date", None))
        expiry = data.get("expiry_date", getattr(self.instance, "expiry_date", None))

        request = self.context.get("request")
        owner = request.user if request else None

        name = data.get("name", getattr(self.instance, "name", None))
        file = data.get("file")
        if owner and file:
         existing_files = License.objects.filter(owner=owner).values_list("file", flat=True)
         existing_names = [f.split("/")[-1] for f in existing_files if f]

        if file.name in existing_names:
            raise serializers.ValidationError("You have already uploaded a license with this file name.")
        
        if not name:
            raise serializers.ValidationError("License name is required.")

        if issue and expiry and expiry <= issue:
            raise serializers.ValidationError("expiry_date must be after issue_date.")

        # 🔧 ENFORCED: Duplicate license prevention (same user + name + issue_date)
        if owner and issue and name:
            qs = License.objects.filter(owner=owner, name=name, issue_date=issue)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("License already exists.")

        return data


# ==============================
# NOTIFICATION
# ==============================
class NotificationSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(read_only=True)
    certificate = serializers.PrimaryKeyRelatedField(read_only=True)
    certificate_id = serializers.IntegerField(source="certificate.pk", read_only=True)
    certificate_title = serializers.CharField(source="certificate.title", read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id", "user", "certificate", "certificate_id",
            "certificate_title", "message", "sent_at",
            "is_read", "tag",
        )
        read_only_fields = (
            "id", "user", "sent_at",
            "certificate", "certificate_id",
            "certificate_title", "tag",
        )


# ==============================
# ACTIVITY LOG
# ==============================
class ActivityLogSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(read_only=True)

    class Meta:
        model = ActivityLog
        fields = ("id", "user", "action", "created_at", "meta")
        read_only_fields = ("id", "user", "created_at")


# ==============================
# SETTINGS
# ==============================
class SettingSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(read_only=True)

    class Meta:
        model = Setting
        fields = (
            "id", "user", "notify_via_email",
            "notify_via_sms", "dark_mode",
            "default_notify_days",
        )
        read_only_fields = ("id", "user")

    def validate_default_notify_days(self, value):
        allowed = [7, 15, 30]
        if value not in allowed:
            raise serializers.ValidationError(
                "default_notify_days must be one of 7, 15, or 30."
            )
        return value


# ==============================
# DASHBOARD
# ==============================
class DashboardSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    expired = serializers.IntegerField()
    expiring_soon = serializers.IntegerField()
    by_category = serializers.DictField(
        child=serializers.IntegerField(),
        help_text="Mapping of category name → number of certificates"
    )


# ==============================
# PROFILE
# ==============================
class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username")
    email = serializers.EmailField(source="user.email")

    class Meta:
        model = Profile
        fields = ["username", "email", "full_name", "phone_number"]

    def validate_phone_number(self, value):
        if value and not re.fullmatch(r"\d{10}", value):
            raise serializers.ValidationError("Phone number must be exactly 10 digits.")
        return value

    def validate_full_name(self, value):
        if value and not re.fullmatch(r"[A-Za-z\s]+", value):
            raise serializers.ValidationError("Full name must contain only alphabets.")
        return value

    def validate(self, data):
        user_data = data.get("user", {})
        username = user_data.get("username")
        if username and " " in username:
            raise serializers.ValidationError("Username cannot contain spaces.")
        return data

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})

        if "username" in user_data:
            instance.user.username = user_data["username"]
        if "email" in user_data:
            instance.user.email = user_data["email"]
        instance.user.save()

        return super().update(instance, validated_data)


# ==============================
# CHANGE PASSWORD
# ==============================
class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match.")
        return data
