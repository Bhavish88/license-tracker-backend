# tracker/management/commands/generate_notifications.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

from tracker.models import Certificate, License, Notification
from django.contrib.auth import get_user_model

from django.core.exceptions import FieldDoesNotExist
from django.db.models import DateTimeField, DateField

User = get_user_model()

class Command(BaseCommand):
    help = "Scan certificates/licenses for upcoming expiries and create Notification objects (uses Notification.tag to dedupe)."

    def handle(self, *args, **options):
        now = timezone.now()
        days_before_list = getattr(settings, 'NOTIFICATION_DAYS_BEFORE', [30, 7, 1])
        created_count = 0

        models_to_check = [
            (Certificate, 'Certificate'),
            (License, 'License'),
        ]

        for model, name in models_to_check:
            for days_before in days_before_list:
                window_start = now
                window_end = now + timedelta(days=days_before)

                # Ensure model has an expiry_date field and get its type
                try:
                    expiry_field = model._meta.get_field('expiry_date')
                except FieldDoesNotExist:
                    # skip models that do not define expiry_date
                    continue

                # Build queryset depending on whether expiry_date is DateTimeField or DateField
                if isinstance(expiry_field, DateTimeField):
                    qs = model.objects.filter(
                        expiry_date__date__lte=window_end.date(),
                        expiry_date__date__gte=window_start.date()
                    )
                elif isinstance(expiry_field, DateField):
                    qs = model.objects.filter(
                        expiry_date__lte=window_end.date(),
                        expiry_date__gte=window_start.date()
                    )
                else:
                    # unknown field type -> skip
                    continue

                for item in qs:
                    # determine owner field reliably (owner/user/created_by)
                    owner = None
                    for attr in ('owner', 'user', 'created_by'):
                        owner = getattr(item, attr, None)
                        if owner:
                            break
                    if not owner:
                        continue  # skip items without an owner

                    # create a deduplication tag
                    tag = f"{name.lower()}_exp_{days_before}_id_{getattr(item, 'pk')}"

                    # skip if a notification with same tag exists for this user
                    exists = Notification.objects.filter(user=owner, tag=tag).exists()
                    if exists:
                        continue

                    # message text
                    title = getattr(item, 'title', str(item))
                    expiry = getattr(item, 'expiry_date', None)
                    msg = f"Your {name.lower()} '{title}' is expiring in {days_before} day(s) on {expiry}."

                    # create Notification (use certificate FK only if model is Certificate)
                    if name == 'Certificate':
                        Notification.objects.create(
                            user=owner,
                            certificate=item,
                            message=msg,
                            tag=tag,
                            is_read=False,
                        )
                    else:
                        # License -> certificate FK not applicable; store message & tag only
                        Notification.objects.create(
                            user=owner,
                            certificate=None,
                            message=msg,
                            tag=tag,
                            is_read=False,
                        )

                    created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Notifications created: {created_count}"))
