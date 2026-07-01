from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

from email_integration.model import EmailIntegration
from email_integration.service import refresh_access_token, should_sync
from Candidates.utils.email_fetcher import fetch_resumes_from_email_oauth
from Candidates.utils.email_processing import process_email_resumes

from extensions import db


scheduler = BackgroundScheduler()


def auto_email_sync(app):   # 👈 accept app

    with app.app_context():   # ✅ use passed app

        integrations = EmailIntegration.query.filter_by(is_active=True).all()

        for record in integrations:
            try:
                if not should_sync(record):
                    continue

                if record.is_expired():
                    token_data = refresh_access_token(record.refresh_token)
                    record.access_token = token_data["access_token"]
                    record.expires_at = datetime.utcnow() + timedelta(seconds=3600)

                # ✅ fix date
                start_date = (
                    record.last_synced_at.strftime("%Y-%m-%d")
                    if record.last_synced_at
                    else (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
                )

                end_date = datetime.utcnow().strftime("%Y-%m-%d")

                resume_files = fetch_resumes_from_email_oauth(
                    record.email,
                    record.access_token,
                    start_date=start_date,
                    end_date=end_date
                )

                if resume_files:
                    process_email_resumes(
                        record.email,
                        record.org_id,
                        record.user_id,
                        resume_files
                    )

                record.last_synced_at = datetime.utcnow()
                db.session.commit()

            except Exception as e:
                db.session.rollback()
                print("AUTO SYNC ERROR:", e)


def start_scheduler(app):   # 👈 pass app here

    if not scheduler.get_jobs():
        scheduler.add_job(
            lambda: auto_email_sync(app),   # 👈 pass app into job
            "interval",
            minutes=5
        )

    scheduler.start()