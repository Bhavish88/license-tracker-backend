from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import Certificate, License, ActivityLog

User = get_user_model()

@receiver(post_save, sender=Certificate)
def log_certificate_upload(sender, instance, created, **kwargs):
    if created:
        ActivityLog.objects.create(
            user=instance.owner,
            action="Uploaded certificate",
            meta={
                "certificate_id": instance.id,
                "title": instance.title
            }
        )


@receiver(post_save, sender=License)
def log_license_upload(sender, instance, created, **kwargs):
    if created:
        ActivityLog.objects.create(
            user=instance.owner,
            action="Uploaded license",
            meta={
                "license_id": instance.id,
                "name": instance.name
            }
        )


@receiver(post_save, sender=User)
def log_user_registration(sender, instance, created, **kwargs):
    if created:
        ActivityLog.objects.create(
            user=instance,
            action="User registered",
            meta={
                "username": instance.username,
                "email": instance.email
            }
        )


@receiver(post_delete, sender=User)
def log_user_deletion(sender, instance, **kwargs):
    ActivityLog.objects.create(
        user=None,  # user no longer exists
        action="User account deleted",
        meta={
            "username": instance.username,
            "email": instance.email
        }
    )
