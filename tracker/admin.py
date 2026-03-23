# tracker/admin.py
from django.contrib import admin
from .models import Category, Certificate, License, Notification, ActivityLog, Setting

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    list_filter = ()
    readonly_fields = ('created_at',)

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'category', 'issued_date', 'expiry_date', 'is_active','reminders_sent')
    search_fields = ('title', 'owner__username', 'category__name')
    list_filter = ('is_active', 'category', 'expiry_date')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'expiry_date'
    fieldsets = (
        (None, {'fields': ('title', 'owner', 'category', 'file')}),
        ('Dates & Reminders', {'fields': ('issued_date', 'expiry_date', 'notify_before_days', 'is_active')}),
        ('Meta', {'fields': ('created_at', 'updated_at')}),
    )

@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ('name', 'number', 'owner', 'issued_by', 'issue_date', 'expiry_date','reminders_sent')
    search_fields = ('name', 'number', 'owner__username')
    list_filter = ('issued_by', 'expiry_date')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'expiry_date'
    fieldsets = (
        (None, {'fields': ('name', 'number', 'owner', 'issued_by', 'file')}),
        ('Dates & Validity', {'fields': ('issue_date', 'expiry_date', 'notify_before_days', 'is_active')}),
        ('Meta', {'fields': ('created_at', 'updated_at')}),
    )

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'certificate', 'sent_at', 'is_read', 'tag')
    search_fields = ('user__username', 'message', 'tag')
    list_filter = ('is_read', 'tag')
    readonly_fields = ('sent_at',)

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'created_at')
    search_fields = ('user__username', 'action')
    readonly_fields = ('created_at', 'meta')

@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ('user', 'notify_via_email', 'notify_via_sms', 'dark_mode', 'default_notify_days')
    search_fields = ('user__username',)
