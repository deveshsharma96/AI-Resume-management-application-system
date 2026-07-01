from extensions import db
from datetime import datetime

class ExportTemplate(db.Model):
    __tablename__ = "export_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    fields = db.Column(db.JSON, nullable=False)

    org_id = db.Column(db.String(50), nullable=False)
    created_by = db.Column(db.String(50), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "fields": self.fields,
            "org_id": self.org_id,
            "created_by": self.created_by,
            "created_at": self.created_at
        }