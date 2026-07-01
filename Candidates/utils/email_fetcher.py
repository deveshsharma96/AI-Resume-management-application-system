

"""
import imaplib
import email
from email.header import decode_header
import os
from datetime import datetime

UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "resumes")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt"]


def safe_decode(value):
    if not value:
        return ""
    decoded_parts = decode_header(value)
    decoded_strings = []
    for decoded, encoding in decoded_parts:
        if isinstance(decoded, bytes):
            try:
                decoded_strings.append(
                    decoded.decode(encoding or "utf-8", errors="ignore")
                )
            except Exception:
                decoded_strings.append(decoded.decode("utf-8", errors="ignore"))
        else:
            decoded_strings.append(str(decoded))
    return " ".join(decoded_strings).strip()


def fetch_resumes_from_email(
    user_email,
    app_password,
    start_date,
    end_date,
    mail_filter="unread",   
):
   
    saved_files = []
    existing_files = set(os.listdir(UPLOAD_DIR))
    mail = None

    try:
        if not all([user_email, app_password, start_date, end_date]):
            print("❌ Missing email credentials or date range.")
            return []

        # ---------- Date conversion ----------
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").strftime("%d-%b-%Y")
            end = datetime.strptime(end_date, "%Y-%m-%d").strftime("%d-%b-%Y")
        except Exception as e:
            print(f"❌ Invalid date format: {e}")
            return []

        # ---------- Connect ----------
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(user_email, app_password)
        mail.select("inbox")

        # ---------- IMAP SEARCH CRITERIA ----------
        if mail_filter == "unread":
            search_query = f'(UNSEEN SINCE "{start}" BEFORE "{end}")'
        elif mail_filter == "read":
            search_query = f'(SEEN SINCE "{start}" BEFORE "{end}")'
        else:  # all
            search_query = f'(SINCE "{start}" BEFORE "{end}")'

        status, data = mail.search(None, search_query)
        if status != "OK" or not data or not data[0]:
            print(f"❌ No emails found for filter: {mail_filter}")
            return []

        mail_ids = data[0].split()
        print(
            f"📬 Found {len(mail_ids)} emails "
            f"[filter={mail_filter}] between {start_date} and {end_date}"
        )

        # ---------- Process emails ----------
        for mail_id in mail_ids:
            res, msg_data = mail.fetch(mail_id, "(RFC822)")
            if res != "OK" or not msg_data:
                continue

            try:
                msg = email.message_from_bytes(msg_data[0][1])
                subject = safe_decode(msg.get("Subject"))
                from_email = safe_decode(msg.get("From"))
                print(f"📨 Processing email from {from_email}, subject: {subject}")
            except Exception as e:
                print(f"❌ Failed to parse email {mail_id}: {e}")
                continue

            for part in msg.walk():
                if part.get_content_disposition() != "attachment":
                    continue

                filename = safe_decode(part.get_filename())
                if not filename:
                    continue

                ext = os.path.splitext(filename)[1].lower()
                if ext not in ALLOWED_EXTENSIONS:
                    print(f"⛔ Skipped non-resume file: {filename}")
                    continue

                safe_name = (
                    filename.replace("/", "_")
                    .replace("\\", "_")
                    .replace(" ", "_")
                )

                if safe_name in existing_files:
                    ts = datetime.now().strftime("%Y%m%d%H%M%S")
                    safe_name = f"{os.path.splitext(safe_name)[0]}_{ts}{ext}"

                file_path = os.path.join(UPLOAD_DIR, safe_name)

                try:
                    with open(file_path, "wb") as f:
                        f.write(part.get_payload(decode=True))
                    print(f"✅ Saved resume: {file_path}")
                    saved_files.append(file_path)
                    existing_files.add(safe_name)
                except Exception as e:
                    print(f"❌ Failed to save file {filename}: {e}")

            # ---------- Mark as SEEN (only for unread/all) ----------
            if mail_filter in ("unread", "all"):
                try:
                    mail.store(mail_id, "+FLAGS", "\\Seen")
                except Exception as e:
                    print(f"❌ Failed to mark email {mail_id} as seen: {e}")

        return saved_files

    except Exception as e:
        print(f"❌ Error fetching emails: {e}")
        return []

    finally:
        if mail:
            try:
                mail.logout()
            except Exception:
                pass

                
                """



import imaplib
import email
from email.header import decode_header
import os
from datetime import datetime, timedelta
from email_integration.service import connect_imap  # ✅ for OAuth

UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "resumes")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt"]


def safe_decode(value):
    if not value:
        return ""
    decoded_parts = decode_header(value)
    decoded_strings = []
    for decoded, encoding in decoded_parts:
        if isinstance(decoded, bytes):
            try:
                decoded_strings.append(
                    decoded.decode(encoding or "utf-8", errors="ignore")
                )
            except Exception:
                decoded_strings.append(decoded.decode("utf-8", errors="ignore"))
        else:
            decoded_strings.append(str(decoded))
    return " ".join(decoded_strings).strip()


def fetch_resumes_from_email(
    user_email,
    app_password,
    start_date,
    end_date,
    mail_filter="all",   # ✅ default changed to ALL
):
    """
    Fetch resume attachments from Gmail.

    mail_filter:
    - unread → UNSEEN
    - read   → SEEN
    - all    → ALL
    """

    saved_files = []
    existing_files = set(os.listdir(UPLOAD_DIR))
    mail = None

    try:
        # ---------------- VALIDATION ----------------
        if not all([user_email, app_password, start_date, end_date]):
            print("❌ Missing email credentials or date range.")
            return []

        # ---------------- DATE FIX ----------------
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").strftime("%d-%b-%Y")

            # ✅ FIX: include end date
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            end = end_dt.strftime("%d-%b-%Y")

        except Exception as e:
            print(f"❌ Invalid date format: {e}")
            return []

        # ---------------- CONNECT ----------------
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(user_email, app_password)
        mail.select("inbox")

        # ---------------- SEARCH QUERY FIX ----------------
        if mail_filter == "unread":
            search_query = f'(UNSEEN SINCE {start} BEFORE {end})'
        elif mail_filter == "read":
            search_query = f'(SEEN SINCE {start} BEFORE {end})'
        else:
            search_query = f'(SINCE {start} BEFORE {end})'

        print("🔍 SEARCH QUERY:", search_query)

        status, data = mail.search(None, search_query)

        if status != "OK" or not data or not data[0]:
            print("❌ No emails found")
            return []

        mail_ids = data[0].split()

        print(f"📬 Found {len(mail_ids)} emails")

        # ---------------- PROCESS EMAILS ----------------
        for mail_id in mail_ids:
            res, msg_data = mail.fetch(mail_id, "(RFC822)")

            if res != "OK":
                continue

            try:
                msg = email.message_from_bytes(msg_data[0][1])
                subject = safe_decode(msg.get("Subject"))
                from_email = safe_decode(msg.get("From"))

                print(f"📨 Email: {subject} | From: {from_email}")

            except Exception as e:
                print(f"❌ Failed to parse email: {e}")
                continue

            # ---------------- EXTRACT FILES ----------------
            for part in msg.walk():

                filename = safe_decode(part.get_filename())

                # ✅ FIX: don't rely on content_disposition
                if not filename:
                    continue

                ext = os.path.splitext(filename)[1].lower()

                if ext not in ALLOWED_EXTENSIONS:
                    print(f"⛔ Skipped: {filename}")
                    continue

                safe_name = (
                    filename.replace("/", "_")
                    .replace("\\", "_")
                    .replace(" ", "_")
                )

                # avoid overwrite
                if safe_name in existing_files:
                    ts = datetime.now().strftime("%Y%m%d%H%M%S")
                    safe_name = f"{os.path.splitext(safe_name)[0]}_{ts}{ext}"

                file_path = os.path.join(UPLOAD_DIR, safe_name)

                try:
                    with open(file_path, "wb") as f:
                        f.write(part.get_payload(decode=True))

                    print(f"✅ Saved: {file_path}")

                    saved_files.append(file_path)
                    existing_files.add(safe_name)

                except Exception as e:
                    print(f"❌ Save failed: {e}")

            # ---------------- MARK AS SEEN ----------------
            try:
                mail.store(mail_id, "+FLAGS", "\\Seen")
            except Exception:
                pass

        print(f"✅ TOTAL FILES SAVED: {len(saved_files)}")

        return saved_files

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return []

    finally:
        if mail:
            try:
                mail.logout()
            except Exception:
                pass




# ==========================================================
# OAUTH VERSION (NEW)
# ==========================================================
def fetch_resumes_from_email_oauth(
    user_email,
    access_token,
    start_date,
    end_date,
    mail_filter="all",
):

    saved_files = []
    existing_files = set(os.listdir(UPLOAD_DIR))
    mail = None

    try:
        if not all([user_email, access_token, start_date, end_date]):
            print("❌ Missing OAuth credentials")
            return []

        start = datetime.strptime(start_date, "%Y-%m-%d").strftime("%d-%b-%Y")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        end = end_dt.strftime("%d-%b-%Y")

        # 🔥 OAuth IMAP connection
        mail = connect_imap(user_email, access_token)
        mail.select("inbox")

        if mail_filter == "unread":
            search_query = f'(UNSEEN SINCE {start} BEFORE {end})'
        elif mail_filter == "read":
            search_query = f'(SEEN SINCE {start} BEFORE {end})'
        else:
            search_query = f'(SINCE {start} BEFORE {end})'

        status, data = mail.search(None, search_query)

        if status != "OK" or not data or not data[0]:
            return []

        mail_ids = data[0].split()

        for mail_id in mail_ids:
            res, msg_data = mail.fetch(mail_id, "(RFC822)")
            if res != "OK":
                continue

            msg = email.message_from_bytes(msg_data[0][1])

            for part in msg.walk():
                filename = safe_decode(part.get_filename())
                if not filename:
                    continue

                ext = os.path.splitext(filename)[1].lower()
                if ext not in ALLOWED_EXTENSIONS:
                    continue

                safe_name = filename.replace("/", "_").replace("\\", "_").replace(" ", "_")

                if safe_name in existing_files:
                    ts = datetime.now().strftime("%Y%m%d%H%M%S")
                    safe_name = f"{os.path.splitext(safe_name)[0]}_{ts}{ext}"

                file_path = os.path.join(UPLOAD_DIR, safe_name)

                with open(file_path, "wb") as f:
                    f.write(part.get_payload(decode=True))

                saved_files.append(file_path)
                existing_files.add(safe_name)

            try:
                mail.store(mail_id, "+FLAGS", "\\Seen")
            except Exception:
                pass

        return saved_files

    except Exception as e:
        print("❌ OAUTH ERROR:", e)
        return []

    finally:
        if mail:
            try:
                mail.logout()
            except Exception:
                pass