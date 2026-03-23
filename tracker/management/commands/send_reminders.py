# tracker/management/commands/send_reminders.py
"""
send_reminders.py

Idempotent, robust reminder sender for both Certificate and License.
- Creates an in-app Notification (avoids duplicates with a tag).
- Sends an email (uses HTML templates via send_expiry_email helper; falls back to send_mail).
- Marks reminders_sent on models (if the field exists).
- Safe if models lack fields: tolerates missing attributes.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from datetime import timedelta
import logging

from tracker.models import Certificate, License, Notification
from tracker.utils.email import send_expiry_email

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send expiry reminders for certificates and licenses (idempotent & tolerant)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Number of days ahead to check for expirations (default: 7)."
        )

    def handle(self, *args, **options):
        today = timezone.now().date()
        days_window = options.get("days", 7)
        sent_count = 0

        # Query items that have expiry_date set and are within window
        cert_qs = Certificate.objects.filter(expiry_date__isnull=False)
        lic_qs = License.objects.filter(expiry_date__isnull=False)

        # Combine lists for unified processing
        items = list(cert_qs) + list(lic_qs)

        for item in items:
            # Skip if already marked as reminders_sent (idempotency)

            # Calculate days left (safe)
            try:
                days_left = (item.expiry_date - today).days
                if 0 < days_left <= item.notify_before_days and item.reminder_stage == "NONE":
                    stage = "PRE"
                elif days_left == 0:
                    stage = "ON"
                elif days_left < 0:
                    stage = "POST"
                else:
                    continue
                if item.reminder_stage == stage:
                    continue
            except Exception:
                logger.warning("Skipping item with invalid expiry_date: %s", getattr(item, "id", "?"))
                continue

            # Build a tag to avoid duplicate in-app notifications for the same item+days_left
            tag = f"{item.__class__.__name__}_{item.id}_{days_left}"

            # Skip if Notification with same tag exists for this owner
            owner = getattr(item, "owner", None)
            if not owner:
                logger.warning("Skipping item %s because it has no owner.", getattr(item, "id", "?"))
                continue

            if Notification.objects.filter(user=owner, tag=tag).exists():
                # Mark reminders_sent if supported and continue
                if hasattr(item, 'reminders_sent'):
                    try:
                        item.reminders_sent = True
                        item.save(update_fields=['reminders_sent'])
                    except Exception:
                        pass
                continue

            # Create notification and send email inside a transaction
            try:
                with transaction.atomic():
                    # Create notification (preserve existing pattern: certificate if certificate else None)
                    if stage == "PRE":
                        msg = f"Your {item.__class__.__name__} '{item}' will expire in {days_left} day(s)."
                    elif stage == "ON":
                        msg = f"Your {item.__class__.__name__} '{item}' expires today."
                    else:
                        msg = f"Your {item.__class__.__name__} '{item}' has expired."

                    Notification.objects.create(
                        user=owner,
                        certificate=item if isinstance(item, Certificate) else None,
                        message=msg,
                        tag=tag
                    )

                    # Try sending rich HTML email via helper
                    item_type = "certificate" if isinstance(item, Certificate) else "license"
                    email_ok = False
                    try:
                        email_ok = send_expiry_email(owner, item, item_type)
                    except Exception as e:
                        # Log and fall back
                        logger.exception(
                            "send_expiry_email raised an exception for item %s: %s",
                            getattr(item, "id", "?"),
                            e
                        )

                    # Fallback to a simple text email if helper failed and owner email exists
                    owner_email = getattr(owner, 'email', None)
                    if not email_ok and owner_email and getattr(settings, 'DEFAULT_FROM_EMAIL', None):

                        if days_left > 0:
                            when_text = f"in {days_left} day(s)"
                            subject = f"Reminder: {item} will expire {when_text}"
                            body_main = f"Your {item.__class__.__name__} '{item}' will expire {when_text}."
                        elif days_left == 0:
                            when_text = "today"
                            subject = f"Reminder: {item} expires today"
                            body_main = f"Your {item.__class__.__name__} '{item}' expires today."
                        else:
                            when_text = f"{abs(days_left)} day(s) ago"
                            subject = f"Reminder: {item} expired {when_text}"
                            body_main = f"Your {item.__class__.__name__} '{item}' expired {when_text}."

                        body = (
                            f"Hello {getattr(owner, 'username', '')},\n\n"
                            f"{body_main}\n\n"
                            "If this is out of date, please update your records in License Tracker.\n\n"
                            "Regards,\nLicense Tracker"
                        )

                        try:
                            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [owner_email])
                        except Exception as e:
                            # Do not stop the entire process on email failure
                            logger.warning("Fallback send_mail failed for %s: %s", getattr(item, "id", "?"), e)
                            self.stdout.write(self.style.WARNING(f"Email send failed for {item}: {e}"))

                # Mark reminder stage (PRE / ON / POST)
                item.reminder_stage = stage
                item.save(update_fields=["reminder_stage"])

                sent_count += 1

            except Exception as exc:
                # If anything goes wrong with this item, continue with next item
                logger.exception("Failed processing item %s: %s", getattr(item, "id", "?"), exc)
                self.stdout.write(self.style.ERROR(f"Failed processing {item}: {exc}"))
                continue

        self.stdout.write(self.style.SUCCESS(f"Reminders sent: {sent_count}"))
