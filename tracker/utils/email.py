from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_expiry_email(user, item, item_type):
    if not user.email:
        logger.warning("User %s has no email; skipping reminder", getattr(user, "id", "?"))
        return False

    if item_type.lower().startswith("cert"):
        html_template = "emails/certificate_reminder.html"
        text_template = "emails/certificate_reminder.txt"
    else:
        html_template = "emails/license_reminder.html"
        text_template = "emails/license_reminder.txt"

    item_label = getattr(item, "title", None) or getattr(item, "name", None) or str(item)
    subject = f"[Reminder] Your {item_type.title()} '{item_label}' expires on {item.expiry_date}"

    context = {"user": user, "item": item}

    try:
        text_content = render_to_string(text_template, context)
        html_content = render_to_string(html_template, context)

        msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [user.email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        return True
    except Exception as e:
        logger.error("Email failed: %s", e)
        return False

