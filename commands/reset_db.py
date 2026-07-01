import click
from flask.cli import with_appcontext
from sqlalchemy import text
from extensions import db
import os


@click.command("reset-db")
@with_appcontext
def reset_db():
    """Reset entire database (DEV ONLY)"""

    # 🔐 Block in production
    if os.getenv("ENV") == "production":
        print("❌ Not allowed in production")
        return

    confirm = input("⚠️ Type DELETE_ALL to reset database: ")

    if confirm != "DELETE_ALL":
        print("❌ Cancelled")
        return

    try:
        print("🚀 Resetting database...")

        db.session.execute(text("SET FOREIGN_KEY_CHECKS=0;"))

        for table in db.metadata.sorted_tables:
            table_name = table.name

            if table_name == "alembic_version":
                continue

            db.session.execute(text(f"TRUNCATE TABLE {table_name};"))
            print(f"🧹 Cleared: {table_name}")

        db.session.execute(text("SET FOREIGN_KEY_CHECKS=1;"))
        db.session.commit()

        print("✅ Database reset complete")

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error: {e}")