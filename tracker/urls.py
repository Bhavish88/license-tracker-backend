from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import CertificateViewSet, CategoryViewSet, LicenseViewSet, StandardResultsSetPagination, NotificationViewSet , register_user, PasswordResetView, PasswordResetConfirmView
from . import views, admin_views

router = DefaultRouter()
router.register(r'certificates', CertificateViewSet, basename='certificate')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'licenses', LicenseViewSet, basename='license')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/dashboard/', views.dashboard_summary, name='dashboard-summary'),
    path("api/register/", views.register_user, name="register"),
    path("api/password-reset/", PasswordResetView.as_view(), name="password-reset"),
    path("api/password-reset-confirm/", PasswordResetConfirmView.as_view()),
    path("api/expiry/", views.expiry_tracker, name="expiry-tracker"),
    path("api/profile/", views.ProfileView.as_view(), name="profile"),
    path("api/profile/change-password/", views.ChangePasswordView.as_view(), name="change-password"),
    path("api/settings/", views.SettingsView.as_view(), name="settings"),
    path("api/admin/dashboard/", views.admin_dashboard_summary, name="admin-dashboard-summary"),
    path("api/admin/recent-activity/", views.admin_recent_activity, name="admin-recent-activity"),
    path("api/admin/users/", admin_views.admin_users_list),
    path("api/admin/users/<int:user_id>/", admin_views.admin_delete_user),
    path("api/admin/licenses/", admin_views.admin_licenses_list),
    path("api/admin/certificates/", admin_views.admin_certificates_list),
    path("api/admin/notifications/", admin_views.admin_notifications_list),
    path("api/admin/settings/", admin_views.admin_settings),
]