from celery_app import celery
from datetime import datetime

from celery_app import celery

from extensions import db

from Notifications.models.reminder import Reminder
from Notifications.services.notification_service import NotificationService


@celery.task
def create_notification_task(
    user_id,
    title,
    message,
    notification_type=None,
    entity_type=None,
    entity_id=None,
    action_url=None,
    extra_data=None
):

    return NotificationService.create_notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        entity_type=entity_type,
        entity_id=entity_id,
        action_url=action_url,
        extra_data=extra_data
    )



@celery.task
def process_due_reminders():

    reminders = Reminder.query.filter(
        Reminder.reminder_date <= datetime.utcnow(),
        Reminder.notification_sent.is_(False),
        Reminder.is_completed.is_(False)
    ).all()

    print(f"REMINDERS FOUND: {len(reminders)}")

    for reminder in reminders:

        print(f"PROCESSING REMINDER: {reminder.id}")

        result = NotificationService.create_notification(
            user_id=reminder.created_by,
            title="Candidate Reminder",
            message=reminder.title,
            notification_type="reminder",
            entity_type="candidate",
            entity_id=reminder.candidate_id
        )

        print("NOTIFICATION RESULT:", result)

        if result.get("success"):
            reminder.notification_sent = True

    db.session.commit()

    print("TASK FINISHED")