# tracker/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.conf import settings
from django.db import models

REMINDER_STAGE_CHOICES = (
    ("NONE", "None"),
    ("PRE", "Pre-expiry"),
    ("ON", "On expiry"),
    ("POST", "Post expiry"),
)

User = settings.AUTH_USER_MODEL

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


User = get_user_model()

def certificate_upload_to(instance, filename):
    owner = getattr(instance, "owner", None)
    owner_id = getattr(owner, "id", "unknown")
    owner_part = f"user_{owner_id}"
    return f"certificates/{owner_part}/{timezone.now().year}/{timezone.now().month}/{filename}"


def license_upload_to(instance, filename):
    owner = getattr(instance, "owner", None)
    owner_id = getattr(owner, "id", "unknown")
    owner_part = f"user_{owner_id}"
    return f"licenses/{owner_part}/{timezone.now().year}/{timezone.now().month}/{filename}"


class Category(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('owner', 'name')
        ordering = ['name']

    def __str__(self):
        return self.name


class Certificate(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    title = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='certificates')
    file = models.FileField(upload_to=certificate_upload_to)
    issued_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    notify_before_days = models.PositiveIntegerField(default=7, help_text="Send reminder this many days before expiry")
    is_active = models.BooleanField(default=True)
    reminders_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reminder_stage = models.CharField(max_length=10, choices=REMINDER_STAGE_CHOICES, default="NONE")

    class Meta:
        ordering = ['-expiry_date', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "title", "issued_date"],
                name="unique_certificate_per_user"
            )
        ]

    def __str__(self):
        return f"{self.title}"

    def days_until_expiry(self):
        if not self.expiry_date:
            return None
        return (self.expiry_date - timezone.now().date()).days

    def should_notify(self):
        days = self.days_until_expiry()
        if days is None:
            return False
        return 0 <= days <= self.notify_before_days


class License(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='licenses')
    name = models.CharField(max_length=200)
    number = models.CharField(max_length=100, blank=True, null=True)
    issued_by = models.CharField(max_length=200, blank=True, null=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    file = models.FileField(upload_to=license_upload_to, null=True, blank=True)
    notify_before_days = models.PositiveIntegerField(default=7, help_text="Send reminder this many days before expiry")
    is_active = models.BooleanField(default=True)    
    reminders_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reminder_stage = models.CharField(max_length=10, choices=REMINDER_STAGE_CHOICES, default="NONE")

    class Meta:
        ordering = ['-issue_date']
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name", "issue_date"],
                name="unique_license_per_user"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.number})" if self.number else self.name

    def days_until_expiry(self):
        if not self.expiry_date:
            return None
        return (self.expiry_date - timezone.now().date()).days

    def should_notify(self):
        days = self.days_until_expiry()
        if days is None:
            return False
        return 0 <= days <= self.notify_before_days


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    certificate = models.ForeignKey(Certificate, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    tag = models.CharField(max_length=120, null=True, blank=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"Notif to {self.user} - {self.sent_at:%Y-%m-%d %H:%M}"


class ActivityLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs")
    action = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    meta = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        user_display = self.user.username if self.user else "System"
        return f"{user_display} — {self.action} @ {self.created_at:%Y-%m-%d %H:%M}"


class Setting(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='setting')
    notify_via_email = models.BooleanField(default=True)
    notify_via_sms = models.BooleanField(default=False)
    dark_mode = models.BooleanField(default=False)
    default_notify_days = models.PositiveIntegerField(default=30)

    def __str__(self):
        return f"Settings for {self.user.username}"


class AdminSetting(models.Model):
    default_notify_days = models.PositiveIntegerField(default=30)
    email_notifications_enabled = models.BooleanField(default=True)
    sms_notifications_enabled = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "System Admin Settings"
