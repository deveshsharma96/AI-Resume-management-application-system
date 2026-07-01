from dotenv import load_dotenv
load_dotenv()

import warnings
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API",
)

from flask import Flask,request
from config import Config
from extensions import db
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from Security.cors_config import init_cors
from email_integration.scheduler import start_scheduler

from Organization.routes.organization_routes import organization_bp
from Organization.routes.super_admin_routes import super_admin_bp
from recruiter.routes.recruiter_routes import recruiter_bp
from auth.routes.auth_routes import auth_bp
from Candidates.routes.candidate_routes import candidate_bp
from dashboard.routes.dashboard_routes import dashboard_bp
from Organization.routes.org_admin_recruiter_routes import org_admin_recruiter_bp
from dashboard.routes.Candidates_information import candidates_info_bp 
from jobs.route.job_routes import job_bp
from jobs.route.job_candidate_routes import job_candidate_bp
from Candidates.routes.job_candidate_journey_routes import job_candidate_journey_bp
from Candidates.routes.journey_interview_routes import journey_bp
from Organization.routes.team_routes import team_bp
from Candidates.routes.otp_routes import otp_bp
from Organization.routes.profile_routes import profile_bp
from Candidates.routes.candidate_listing_routes import candidate_listing_bp
from Candidates.routes.candidate_visibility_routes import candidate_visibility_bp
from auth.candidate.routes.otp_login import candidate_otp_bp
from support.routes.support_routes import support_bp
from common.routes.document_routes import documents_bp
from common.routes.skills import skill_bp
from GlobalRecruiter.routes.recruiter_invite_routes import recruiter_v2_bp
from GlobalRecruiter.routes.recruiter_collaboration_routes import collaboration_bp
from common.routes.location_routes import location_bp
from email_integration.routes import email_bp
from GlobalRecruiter.routes.notification_routes import notification_bp
from GlobalRecruiter.routes.organization_routes import organization_v2_bp
from Organization.routes.org_management import org_management_bp
from recruiter.routes.recruiter_management import recruiter_mgmt_bp
from common.routes.version_routes import version_bp


from Organization.routes.hiring_manager_routes import hiring_manager_bp
from Notifications.routes.notification_routes import app_notification_bp


from flask_cors import CORS


from commands.reset_db import reset_db



# New Candidate Register & Login
from auth.candidate.routes.candidate_auth_routes import candidate_auth_bp
from auth.candidate.routes.otp_login import (
    candidate_password_login_bp,
    candidate_otp_bp
)


# # New Candidate documents request send by recruiter 
from recruiter.routes.document_request_routes import (
    document_request_bp
)




# New Candidate documents request send by org 
from Candidates.routes.document_asset_routes import (
    document_asset_bp
)

# New Candidate documents request send by org
from Candidates.routes.candidate_document_routes import (
    candidate_document_bp
)
# New Candidate documents request send by org
from recruiter.routes.document_review_routes import (
    document_review_bp
)





def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config["UPLOAD_FOLDER"] = "temp"
    app.config.from_object(Config)

    app.config["MAX_CONTENT_LENGTH"] = 150 * 1024 * 1024 
    init_cors(app)


    jwt = JWTManager(app)

    db.init_app(app)
    migrate = Migrate(app, db)
    import models_imports

    # Register blueprints
    app.register_blueprint(organization_bp, url_prefix="/api/organization")
    app.register_blueprint(org_admin_recruiter_bp, url_prefix="/api/org")
    app.register_blueprint(super_admin_bp, url_prefix="/api/super-admin")
    app.register_blueprint(recruiter_bp, url_prefix="/api/recruiter")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    app.register_blueprint(candidate_bp, url_prefix="/api/candidate")  
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(candidates_info_bp, url_prefix="/api/dashboard")

    app.register_blueprint(job_bp, url_prefix="/api/job")
    app.register_blueprint(job_candidate_bp, url_prefix="/api/jobs")

    app.register_blueprint(job_candidate_journey_bp, url_prefix="/api/journey")
    app.register_blueprint(journey_bp, url_prefix="/api/journey")
    app.register_blueprint(team_bp, url_prefix="/api/teams")

    app.register_blueprint(otp_bp, url_prefix="/api/otp")

    app.register_blueprint(profile_bp, url_prefix="/api/profile")
    
    app.register_blueprint(candidate_listing_bp)
    app.register_blueprint(candidate_visibility_bp)
    app.register_blueprint(candidate_otp_bp)

    app.register_blueprint(support_bp)
    app.register_blueprint(documents_bp, url_prefix="/api/documents")

    app.register_blueprint(skill_bp, url_prefix="/api")
    app.register_blueprint(recruiter_v2_bp,url_prefix="/api")
    
    app.register_blueprint(collaboration_bp,url_prefix="/api")


    app.register_blueprint(location_bp, url_prefix="/api")
    app.register_blueprint(email_bp, url_prefix="/api")

    app.register_blueprint(notification_bp, url_prefix="/api")
    app.register_blueprint(organization_v2_bp, url_prefix="/api/organization")



    # New Candidate Register blueprints & Login
    app.register_blueprint(candidate_auth_bp, url_prefix="/api/candidate/auth")
    app.register_blueprint(candidate_password_login_bp)

    app.register_blueprint(org_management_bp, url_prefix="/api")
    app.register_blueprint(recruiter_mgmt_bp, url_prefix="/api")


    app.register_blueprint(version_bp, url_prefix="/api")
    app.register_blueprint(hiring_manager_bp, url_prefix="/api")
    app.register_blueprint(
        app_notification_bp,
        url_prefix="/api/notifications"
    )
    
    
    # New Candidate document request blueprints
    app.register_blueprint(
        document_request_bp,
        url_prefix="/api/document-request"
    )
    
    

    
    # New Candidate document upload org
    app.register_blueprint(
        document_asset_bp,
        url_prefix="/api/candidate/document"
    )
    # New Candidate document upload org
    app.register_blueprint(
        candidate_document_bp,
        url_prefix="/api/candidate/documents"
    )
    # New Candidate document upload org
    app.register_blueprint(
        document_review_bp,
        url_prefix="/api/document-review"
    )
    
   

    app.cli.add_command(reset_db)


    @app.route("/")
    def index():
        return "Recruitment Platform API running"    

    return app
app = create_app()

if __name__ == "__main__":

    
    start_scheduler(app)

    app.run(host="0.0.0.0", port=5001, debug=True)

