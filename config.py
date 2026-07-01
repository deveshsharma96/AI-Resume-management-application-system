import os

class Config:
    # ------------------ Core Secrets ------------------
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

    # ------------------ Database ------------------
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ------------------ App Settings ------------------
    TOKEN_EXPIRATION_HOURS = int(os.getenv("TOKEN_EXPIRATION_HOURS", 24))

    # ------------------ Frontend ------------------
    FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL")

    # ------------------ Email ------------------
    # ------------------ Email (Brevo SMTP) ------------------
    EMAIL_HOST = os.getenv("EMAIL_HOST")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"

    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")        # apikey
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")  # Brevo SMTP key

    DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")

    
    # ------------------ Object Storage (CloudPe) ------------------
    OBJECT_STORAGE_BUCKET = os.getenv("OBJECT_STORAGE_BUCKET")
    OBJECT_STORAGE_ACCESS_KEY = os.getenv("OBJECT_STORAGE_ACCESS_KEY")
    OBJECT_STORAGE_SECRET_KEY = os.getenv("OBJECT_STORAGE_SECRET_KEY")
    OBJECT_STORAGE_REGION = os.getenv("OBJECT_STORAGE_REGION")
    OBJECT_STORAGE_ENDPOINT = os.getenv("OBJECT_STORAGE_ENDPOINT")


    # ------------------ Google OAuth ------------------
    # ------------------ Google OAuth ------------------
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")