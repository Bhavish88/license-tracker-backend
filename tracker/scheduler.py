from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_events
from apscheduler.triggers.cron import CronTrigger
from django.core.management import call_command
import logging
import os

logger = logging.getLogger(__name__)

def send_reminders_job():
    logger.info("Running daily send_reminders job...")
    call_command("send_reminders")


def start():
    # Prevent double start in Django dev server
    if os.environ.get("RUN_MAIN") != "true":
        return

    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")

    scheduler.add_job(
        send_reminders_job,
        trigger=CronTrigger(hour=9, minute=0),
        id="daily_send_reminders",
        replace_existing=True,
        max_instances=1,
    )

    register_events(scheduler)
    scheduler.start()
    logger.info("Scheduler started with daily send_reminders job")
