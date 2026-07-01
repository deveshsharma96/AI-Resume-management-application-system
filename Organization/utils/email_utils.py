import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
import os

SMTP_SERVER = os.getenv("EMAIL_HOST", "smtp-relay.brevo.com")
SMTP_PORT = int(os.getenv("EMAIL_PORT", 587))

SMTP_USERNAME = os.getenv("EMAIL_HOST_USER")      # MUST be 'apikey'
SMTP_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")  # Brevo SMTP key
FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")

# ----------------------------------------------------
# OTP EMAIL (LOGIN / RESET PASSWORD)
# ----------------------------------------------------
def send_verification_code(to_email, code, purpose="login"):
    """
    Send OTP for different purposes:
    - login
    - reset_password
    """

    if purpose == "reset_password":
        subject = "Reset Your CandiIQ Password – OTP Verification"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background:#f4f6f8; padding:20px;">
            <div style="max-width:520px; margin:auto; background:#ffffff;
                        padding:24px; border-radius:6px; box-shadow:0 0 10px rgba(0,0,0,0.05);">

                <h2 style="color:#333;">Reset Your Password</h2>

                <p>You requested to reset your CandiIQ account password.</p>

                <p style="margin:20px 0;">Your OTP for password reset is:</p>

                <div style="
                    font-size:26px;
                    font-weight:bold;
                    letter-spacing:5px;
                    background:#f1f1f1;
                    padding:12px;
                    text-align:center;
                    border-radius:4px;
                ">
                    {code}
                </div>

                <p style="margin-top:20px;">
                    Please verify this OTP to change your password.<br>
                    This OTP is valid for <strong>5 minutes</strong>.
                </p>

                <p style="color:#777; font-size:13px;">
                    If you did not request a password reset, please ignore this email.
                </p>

                <hr>

                <p style="font-size:12px; color:#999;">
                    CandiIQ by Yuktic
                </p>
            </div>
        </body>
        </html>
        """

    elif purpose == "registration":
        subject = "Verify Your CandiIQ Account – OTP"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background:#f4f6f8; padding:20px;">
            <div style="max-width:520px; margin:auto; background:#ffffff;
                        padding:24px; border-radius:6px; box-shadow:0 0 10px rgba(0,0,0,0.05);">

                <h2 style="color:#333;">Verify Your Email</h2>

                <p>Use the OTP below to verify your email and continue your registration.</p>

                <div style="
                    font-size:26px;
                    font-weight:bold;
                    letter-spacing:5px;
                    background:#f1f1f1;
                    padding:12px;
                    text-align:center;
                    border-radius:4px;
                    margin:20px 0;
                ">
                    {code}
                </div>

                <p>This OTP is valid for <strong>5 minutes</strong>.</p>

                <p style="color:#777; font-size:13px;">
                    If you did not request this verification, please ignore this email.
                </p>

                <hr>
                <p style="font-size:12px; color:#999;">CandiIQ by Yuktic</p>
            </div>
        </body>
        </html>
        """

    else:  # LOGIN OTP
        subject = "Your CandiIQ Login OTP"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background:#f4f6f8; padding:20px;">
            <div style="max-width:520px; margin:auto; background:#ffffff;
                        padding:24px; border-radius:6px; box-shadow:0 0 10px rgba(0,0,0,0.05);">

                <h2 style="color:#333;">Login Verification</h2>

                <p>Use the OTP below to login to your CandiIQ account.</p>

                <div style="
                    font-size:26px;
                    font-weight:bold;
                    letter-spacing:5px;
                    background:#f1f1f1;
                    padding:12px;
                    text-align:center;
                    border-radius:4px;
                    margin:20px 0;
                ">
                    {code}
                </div>

                <p>This OTP is valid for <strong>5 minutes</strong>.</p>

                <p style="color:#777; font-size:13px;">
                    If you did not attempt to login, please ignore this email.
                </p>

                <hr>

                <p style="font-size:12px; color:#999;">
                    CandiIQ by Yuktic
                </p>
            </div>
        </body>
        </html>
        """

    _send_email(to_email, subject, body)
    print(f"[INFO] OTP ({purpose}) sent to: {to_email}")

# ----------------------------------------------------
# ORGANIZATION REGISTRATION EMAIL
# ----------------------------------------------------
def send_organization_registration_email(to_email, org_name, org_id):
    subject = f"Welcome to CandiIQ, {org_name}!"

    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background:#f4f6f8; padding:20px;">

        <div style="
            max-width:520px;
            margin:auto;
            background:#ffffff;
            padding:28px;
            border-radius:8px;
            box-shadow:0 4px 12px rgba(0,0,0,0.08);
        ">

            <h2 style="color:#2563eb; margin-bottom:10px;">
                🎉 Welcome to CandiIQ
            </h2>

            <p style="font-size:15px; color:#333;">
                Dear <strong>{org_name}</strong>,
            </p>

            <p style="color:#555; font-size:14px;">
                Thank you for registering your organization with 
                <strong>CandiIQ</strong>. We’re excited to have you onboard 🚀
            </p>

            <p style="margin-top:20px; color:#333;">
                <strong>Your Organization ID:</strong>
            </p>

            <div style="
                font-size:22px;
                font-weight:bold;
                letter-spacing:2px;
                background:#eef2ff;
                color:#1e3a8a;
                padding:14px;
                text-align:center;
                border-radius:6px;
                margin:15px 0;
            ">
                {org_id}
            </div>

            <p style="font-size:14px; color:#555;">
                Please keep this ID safe. You may need it for future access and support.
            </p>

            <hr style="margin:25px 0;">

            <p style="font-size:13px; color:#777;">
                Need help? Contact our support team anytime.
            </p>

            <p style="margin-top:20px; font-size:14px;">
                Warm regards,<br>
                <strong style="color:#2563eb;">The CandiIQ Team</strong>
            </p>

        </div>

    </body>
    </html>
    """

    _send_email(to_email, subject, body)
    print(f"[INFO] Organization registration email sent to: {to_email}")
# ----------------------------------------------------
# SMTP SENDER (HTML ENABLED)
# ----------------------------------------------------
def _send_email(to_email, subject, body):
    
    if not SMTP_USERNAME or not SMTP_PASSWORD or not FROM_EMAIL:
        raise RuntimeError(
            "Brevo SMTP config missing. Check EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, DEFAULT_FROM_EMAIL"
        )

    msg = MIMEText(body, "html")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SMTP_USERNAME, SMTP_PASSWORD)
    server.send_message(msg)
    server.quit()


def send_candidate_shared_email(
    to_email,
    to_name,
    candidate_name,
    candidate_email,
    shared_by_name,
    shared_by_email
):
    subject = f"Candidate Shared for Your Review – {candidate_name}"

    platform_link = current_app.config["FRONTEND_BASE_URL"]


    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6;">
        <p>Dear {to_name},</p>

        <p>
            You are receiving this email because a candidate has been 
            <strong>shared with you for review</strong> on <strong>CandiIQ</strong>.
            As an <strong>Organization Recruiter</strong>, you can access the
            candidate profile and take further hiring actions.
        </p>

        <p><strong>Candidate Details:</strong><br>
        Name: {candidate_name}<br>
        Email: {candidate_email}</p>

        <p><strong>Shared By:</strong><br>
        {shared_by_name} (<a href="mailto:{shared_by_email}">{shared_by_email}</a>)</p>

        <p>
            👉 <strong>Action Required:</strong><br>
            Please log in to CandiIQ using the link below to view the complete
            candidate profile, review details, and proceed with the hiring process.
        </p>

        <p style="margin: 20px 0;">
            <a href="{platform_link}" 
               style="background-color: #2563eb; color: white; 
                      padding: 10px 16px; text-decoration: none;
                      border-radius: 5px; font-weight: bold;">
                View Candidate on CandiIQ
            </a>
        </p>

        <p>
            If the button above does not work, copy and paste the following URL
            into your browser:<br>
            <a href="{platform_link}">{platform_link}</a>
        </p>

        <p>Best regards,<br>
        <strong>The CandiIQ Team</strong></p>
    </body>
    </html>
    """

    _send_email(to_email, subject, body)
    print(f"[INFO] Candidate shared email sent to {to_email}")

# ----------------------------------------------------
# CONTACT CHANGE NOTIFICATION
# ----------------------------------------------------
def send_contact_change_notification_to_superadmin(
    superadmin_email,
    user_role,
    user_name,
    user_primary_email,
    changes
):
    subject = f"{user_role.title()} contact details updated"

    change_lines = ""
    for field, diff in changes.items():
        old = diff.get("old") or "N/A"
        new = diff.get("new") or "N/A"
        change_lines += f"<li>{field}: {old} → {new}</li>"

    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <p>Hello Super Admin,</p>

        <p>The following contact details have been updated on CandiIQ:</p>

        <p>
        User Role: {user_role}<br>
        User Name: {user_name}<br>
        User Email: {user_primary_email}
        </p>

        <ul>
            {change_lines}
        </ul>

        <p>This is an automated notification.</p>

        <p>Best regards,<br>The CandiIQ Team</p>
    </body>
    </html>
    """

    _send_email(superadmin_email, subject, body)
    print(f"[INFO] Contact change notification sent to SuperAdmin: {superadmin_email}")


# ----------------------------------------------------
# CANDIDATE FORM LINK EMAIL (BASIC FORM FLOW)
# ----------------------------------------------------
def send_candidate_form_link_email(to_email, candidate_name, token):
    base_url = current_app.config["FRONTEND_BASE_URL"]
    form_link = f"{base_url}/#/candidateform?token={token}"


    subject = "Complete Your Candidate Form – CandiIQ"

    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background:#f4f6f8; padding:20px;">
        <div style="max-width:520px; margin:auto; background:#ffffff;
                    padding:24px; border-radius:6px;">

            <p>Hi <strong>{candidate_name}</strong>,</p>

            <p>
                You’ve been invited to complete your candidate profile on
                <strong>CandiIQ</strong>.
            </p>

            <p style="margin: 20px 0;">
                <a href="{form_link}"
                   style="background:#2563eb; color:white;
                          padding:12px 18px;
                          text-decoration:none;
                          border-radius:5px;
                          font-weight:bold;">
                    Complete Candidate Form
                </a>
            </p>

            <p>
                ⏳ This link will expire in <strong>2 days</strong>.
            </p>

            <p>If you did not expect this email, you may safely ignore it.</p>

            <hr>
            <p style="font-size:12px; color:#999;">
                CandiIQ by Yuktic
            </p>
        </div>
    </body>
    </html>
    """

    _send_email(to_email, subject, body)
    print(f"[INFO] Candidate form link email sent to {to_email}")





# ----------------------------------------------------
# RECRUITER / ADMIN INVITATION EMAIL
# ----------------------------------------------------
# ----------------------------------------------------
# RECRUITER / ADMIN INVITATION EMAIL
# ----------------------------------------------------
def send_invitation_email(to_email, token, role):
    """
    Send invitation email to recruiter/admin using common email service.
    """

    base_url = current_app.config["FRONTEND_BASE_URL"]
    invite_link = f"{base_url}/#/onboarding?token={token}"

    subject = f"Complete Your {role} Registration – CandiIQ"

    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background:#f4f6f8; padding:20px;">
        <div style="max-width:520px; margin:auto; background:#ffffff;
                    padding:24px; border-radius:6px; box-shadow:0 2px 8px rgba(0,0,0,0.08);">

            <h2 style="color:#333;">You're Invited to Join CandiIQ</h2>

            <p>
                You have been invited to join <strong>CandiIQ</strong> as a
                <strong>{role}</strong>.
            </p>

            <p>
                Please click the button below to complete your registration
                and verify your details.
            </p>

            <p style="margin: 20px 0;">
                <a href="{invite_link}"
                   style="background-color:#2563eb; color:#ffffff;
                          padding:12px 20px; text-decoration:none;
                          font-weight:bold; border-radius:6px;">
                    Complete Registration
                </a>
            </p>

            <p style="font-size:14px; color:#555;">
                If you did not expect this invitation, you can safely ignore this email.
            </p>

            <hr>
            <p style="font-size:12px; color:#999;">
                CandiIQ by Yuktic
            </p>
        </div>
    </body>
    </html>
    """

    _send_email(to_email, subject, body)
    print(f"[INFO] Recruiter invitation email sent to: {to_email}")



# ----------------------------------------------------
# JOB SHARED EMAIL
# ----------------------------------------------------
def send_job_shared_email(
    to_email,
    to_name,
    job_title,
    job_id,
    shared_by_name,
    shared_by_email
):
    subject = f"New Job Shared for Your Review – {job_title}"

    platform_link = current_app.config["FRONTEND_BASE_URL"]

    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6;">
        <p>Dear {to_name},</p>

        <p>
            A job has been <strong>shared with you</strong> on 
            <strong>CandiIQ</strong>.
        </p>

        <p><strong>Job Details:</strong><br>
        Title: {job_title}<br>
        Job ID: {job_id}</p>

        <p><strong>Shared By:</strong><br>
        {shared_by_name} 
        (<a href="mailto:{shared_by_email}">{shared_by_email}</a>)
        </p>

        <p>
            👉 <strong>Action Required:</strong><br>
            Please log in to view the job details and take necessary action.
        </p>

        <p style="margin: 20px 0;">
            <a href="{platform_link}" 
               style="background-color: #2563eb; color: white; 
                      padding: 10px 16px; text-decoration: none;
                      border-radius: 5px; font-weight: bold;">
                View Job on CandiIQ
            </a>
        </p>

        <p>
            If the button above does not work, copy and paste this URL:<br>
            <a href="{platform_link}">{platform_link}</a>
        </p>

        <p>Best regards,<br>
        <strong>The CandiIQ Team</strong></p>
    </body>
    </html>
    """

    _send_email(to_email, subject, body)
    print(f"[INFO] Job shared email sent to {to_email}")







# ----------------------------------------------------
# HIRING MANAGER INVITATION EMAIL
# ----------------------------------------------------
def send_hiring_manager_invitation_email(
    to_email,
    token
):

    base_url = current_app.config["FRONTEND_BASE_URL"]

    invite_link = (
        f"{base_url}"
        f"/#/hiringManager-onboarding"
        f"?token={token}"
    )

    subject = (
        "Complete Your Hiring Manager "
        "Registration – CandiIQ"
    )

    body = f"""
    <html>
    <body style="
        font-family: Arial, sans-serif;
        background:#f4f6f8;
        padding:20px;
    ">

        <div style="
            max-width:520px;
            margin:auto;
            background:#ffffff;
            padding:24px;
            border-radius:6px;
            box-shadow:0 2px 8px rgba(0,0,0,0.08);
        ">

            <h2 style="color:#333;">
                You're Invited as Hiring Manager
            </h2>

            <p>
                You have been invited to join
                <strong>CandiIQ</strong>
                as a
                <strong>Hiring Manager</strong>.
            </p>

            <p>
                Click below to complete your
                onboarding and set your password.
            </p>

            <p style="margin:20px 0;">

                <a href="{invite_link}"
                   style="
                        background-color:#2563eb;
                        color:#ffffff;
                        padding:12px 20px;
                        text-decoration:none;
                        font-weight:bold;
                        border-radius:6px;
                   ">

                    Complete Registration

                </a>

            </p>

            <p style="
                font-size:14px;
                color:#555;
            ">
                This invitation link will expire
                in 24 hours.
            </p>

            <hr>

            <p style="
                font-size:12px;
                color:#999;
            ">
                CandiIQ by Yuktic
            </p>

        </div>

    </body>
    </html>
    """

    _send_email(
        to_email,
        subject,
        body
    )

    print(
        f"[INFO] Hiring manager invitation "
        f"email sent to: {to_email}"
    )


# ----------------------------------------------------
# NEW DOCUMENT REQUEST EMAIL
# ----------------------------------------------------
def send_document_request_email(
    to_email,
    candidate_name,
    upload_token,
    documents
):

    base_url = current_app.config["FRONTEND_BASE_URL"]

    upload_link = (
        f"{base_url}"
        f"/#/candidate-document-upload"
        f"?token={upload_token}"
    )

    # ------------------------------------------------
    # BUILD DOCUMENT TABLE HTML
    # ------------------------------------------------

    documents_html = ""

    for doc in documents:

        doc_name = doc.get(
            "name",
            "Document"
        )

        mandatory = (
            "Mandatory"
            if doc.get("mandatory")
            else "Optional"
        )

        note_html = ""

        if doc.get("note"):

            note_html = f"""
            <div style="
                margin-top:6px;
                font-size:13px;
                color:#555;
                line-height:1.5;
            ">
                {doc.get("note")}
            </div>
            """

        documents_html += f"""
        <tr>

            <td style="
                padding:12px;
                border:1px solid #ddd;
                vertical-align:top;
            ">

                <div style="
                    font-weight:600;
                    color:#111827;
                ">
                    {doc_name}
                </div>

                {note_html}

            </td>

            <td style="
                padding:12px;
                border:1px solid #ddd;
                vertical-align:top;
            ">

                <span style="
                    padding:4px 10px;
                    border-radius:20px;
                    font-size:12px;
                    font-weight:600;
                    color:white;
                    background:{
                        '#dc2626'
                        if doc.get('mandatory')
                        else '#16a34a'
                    };
                ">

                    {mandatory}

                </span>

            </td>

        </tr>
        """

    # ------------------------------------------------
    # EMAIL SUBJECT
    # ------------------------------------------------

    subject = "Document Upload Request – CandiIQ"

    # ------------------------------------------------
    # EMAIL BODY
    # ------------------------------------------------

    body = f"""
    <html>

    <body style="
        font-family:Arial,sans-serif;
        background:#f4f6f8;
        padding:20px;
    ">

        <div style="
            max-width:650px;
            margin:auto;
            background:#ffffff;
            border-radius:8px;
            padding:30px;
            box-shadow:0 2px 10px rgba(0,0,0,0.05);
        ">

            <h2 style="
                margin-top:0;
                color:#2563eb;
            ">
                Document Upload Request
            </h2>

            <p style="
                font-size:15px;
                color:#374151;
            ">
                Hi <strong>{candidate_name}</strong>,
            </p>

            <p style="
                line-height:1.6;
                color:#4b5563;
            ">
                Your organization has requested the
                following documents for verification
                on <strong>CandiIQ</strong>.
            </p>

            <table style="
                width:100%;
                border-collapse:collapse;
                margin-top:24px;
                margin-bottom:24px;
            ">

                <tr style="
                    background:#2563eb;
                    color:white;
                ">

                    <th style="
                        padding:14px;
                        border:1px solid #ddd;
                        text-align:left;
                    ">
                        Document Name
                    </th>

                    <th style="
                        padding:14px;
                        border:1px solid #ddd;
                        text-align:left;
                        width:160px;
                    ">
                        Requirement
                    </th>

                </tr>

                {documents_html}

            </table>

            <div style="
                margin:30px 0;
                text-align:center;
            ">

                <a href="{upload_link}"

                   style="
                        background:#2563eb;
                        color:white;
                        padding:14px 24px;
                        text-decoration:none;
                        border-radius:6px;
                        font-weight:bold;
                        display:inline-block;
                   ">

                    Upload Documents

                </a>

            </div>

            <p style="
                font-size:14px;
                line-height:1.6;
                color:#4b5563;
            ">
                Please upload all required documents
                using the secure link above.
            </p>

            <p style="
                font-size:13px;
                color:#6b7280;
            ">
                If you did not expect this email,
                you may safely ignore it.
            </p>

            <hr style="
                margin-top:30px;
                border:none;
                border-top:1px solid #e5e7eb;
            ">

            <p style="
                font-size:12px;
                color:#9ca3af;
                margin-top:20px;
            ">
                CandiIQ by Yuktic
            </p>

        </div>

    </body>

    </html>
    """

    _send_email(
        to_email,
        subject,
        body
    )

    print(
        f"[INFO] Document request email sent to {to_email}"
    )

