# Security/cors_config.py
from flask_cors import CORS

def init_cors(app):
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [

                    "http://localhost:3000",
                    
                    "http://localhost:8080",

                    "http://10.5.48.72:8080"
                ],
                "allow_headers": [
                    "Content-Type",
                    "Authorization",
                    "X-User-Email",
                    "X-Org-Id"
                ],
                "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
                "expose_headers": ["Authorization"],
                "max_age": 600
            }
        }
    )
