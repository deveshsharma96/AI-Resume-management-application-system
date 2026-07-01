from celery import Celery

from app import create_app


flask_app = create_app()

celery = Celery(
    "hire_nest",
    broker="pyamqp://guest:guest@localhost:5672//",
    backend="rpc://",
    include=[
        "Notifications.tasks.notification_tasks"
    ]
)


class ContextTask(celery.Task):
    def __call__(self, *args, **kwargs):
        with flask_app.app_context():
            return self.run(*args, **kwargs)


celery.Task = ContextTask


celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)