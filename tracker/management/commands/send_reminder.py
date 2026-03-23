# tracker/management/commands/send_reminder.py
"""
Backward-compatibility wrapper for the newer `send_reminders` command.

Older scripts or scheduled tasks that run:
    python manage.py send_reminder
will continue to work. This wrapper simply calls the new command.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = "Wrapper: call the new send_reminders command (keeps backward compatibility)."

    def add_arguments(self, parser):
        # allow passing --days through to the new command
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help="(optional) Number of days ahead to check for expirations. Passed to send_reminders."
        )

    def handle(self, *args, **options):
        days = options.get("days", None)
        cmd_args = []
        if days is not None:
            cmd_args.extend(["--days", str(days)])
        # forward to send_reminders
        call_command("send_reminders", *cmd_args)
