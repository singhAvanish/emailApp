from flask import Flask, request, jsonify, redirect
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import os
import base64
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, origins=["https://email-app-xi.vercel.app"])

# OAuth2 Configuration
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
PROJECT_ID = os.getenv("PROJECT_ID")
AUTH_URI = os.getenv("AUTH_URI")
TOKEN_URI = os.getenv("TOKEN_URI")
AUTH_PROVIDER_CERT_URL = os.getenv("AUTH_PROVIDER_CERT_URL")
REDIRECT_URIS = os.getenv("REDIRECT_URIS")  # Convert to list

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
REDIRECT_URI = REDIRECT_URIS  # Use the first redirect URI

# Directory to store user tokens
TOKEN_DIR = "tokens"
os.makedirs(TOKEN_DIR, exist_ok=True)


@app.route('/auth')
def auth():
    """Start OAuth2 Authentication Flow"""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "project_id": PROJECT_ID,
                "auth_uri": AUTH_URI,
                "token_uri": TOKEN_URI,
                "auth_provider_x509_cert_url": AUTH_PROVIDER_CERT_URL,
                "redirect_uris": REDIRECT_URIS,
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    authorization_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    return redirect(authorization_url)


@app.route('/auth/callback')
def auth_callback():
    """Handle OAuth2 Callback & Store User Credentials"""
    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "project_id": PROJECT_ID,
                    "auth_uri": AUTH_URI,
                    "token_uri": TOKEN_URI,
                    "auth_provider_x509_cert_url": AUTH_PROVIDER_CERT_URL,
                    "redirect_uris": REDIRECT_URIS,
                }
            },
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials

        # Get the authenticated user's email
        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()
        user_email = user_info.get("email")

        if not user_email:
            return jsonify({"error": "Authentication failed. Unable to retrieve user email."}), 400

        # Save credentials with user email as filename
        safe_email = user_email.replace("@", "_").replace(".", "_")
        token_path = os.path.join(TOKEN_DIR, f"{safe_email}.json")

        with open(token_path, "w") as token_file:
            token_file.write(credentials.to_json())

        return jsonify({"message": f"Authentication successful for {user_email}! You can now send emails."})

    except Exception as e:
        return jsonify({"error": f"Authentication failed: {str(e)}"}), 500


def get_user_credentials(user_email):
    """Retrieve and Refresh User Credentials"""
    try:
        safe_email = user_email.replace("@", "_").replace(".", "_")
        token_path = os.path.join(TOKEN_DIR, f"{safe_email}.json")

        if not os.path.exists(token_path):
            return None

        credentials = Credentials.from_authorized_user_file(token_path)

        # Refresh token if expired
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            with open(token_path, "w") as token_file:
                token_file.write(credentials.to_json())

        return credentials
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return None


@app.route('/send-email', methods=['POST'])
def send_email():
    """Send Email with Attachment"""
    try:
        data = request.json
        user_email = data.get("user_email")  # Get user email from request
        recipient_emails = data.get('recipient_emails', [])
        subject = data.get('subject', '')
        body = data.get('body', '')
        pdf_file_base64 = data.get('pdf_file_base64', '')
        pdf_file_name = data.get('pdf_file_name', 'attachment.pdf')

        if not user_email:
            return jsonify({"error": "User email is required."}), 400

        # Get user credentials
        credentials = get_user_credentials(user_email)
        if not credentials:
            return jsonify({"error": "User not authenticated. Please log in again."}), 401

        # Decode the base64 PDF file
        pdf_file_bytes = base64.b64decode(pdf_file_base64)

        # Build Gmail service
        service = build("gmail", "v1", credentials=credentials)

        # Send email to each recipient
        for recipient in recipient_emails:
            msg = MIMEMultipart()
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            # Attach the PDF file
            part = MIMEBase("application", "octet-stream")
            part.set_payload(pdf_file_bytes)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={pdf_file_name}")
            msg.attach(part)

            # Encode the message
            raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
            message = {"raw": raw_message}

            # Send the email
            service.users().messages().send(userId="me", body=message).execute()
            print(f"Email sent successfully to {recipient}!")

        return jsonify({"message": "Emails sent successfully!"}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to send email: {str(e)}"}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Get PORT from environment, default to 5000
    app.run(host='0.0.0.0', port=port, debug=False)  # Bind to all network interfaces
