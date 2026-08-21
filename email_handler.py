"""
email_handler.py
© 2026 Fayaz Ahmed Shaik. All rights reserved.

Handles sending transactional emails using Brevo HTTP API.
"""

import os
import logging
import requests

logger = logging.getLogger(__name__)

# ── Brevo API Configuration ────────────────────────────────────────────────
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
SENDER_NAME = "Fury AI"

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def _send_email(to_email: str, subject: str, html_body: str) -> bool:
    """
    Sends an email using Brevo's HTTP API.
    Returns True on success, False on failure.
    """

    if not BREVO_API_KEY:
        logger.error("BREVO_API_KEY is not set.")
        return False

    if not SENDER_EMAIL:
        logger.error("SENDER_EMAIL is not set.")
        return False

    payload = {
        "sender": {
            "name": SENDER_NAME,
            "email": SENDER_EMAIL
        },
        "to": [
            {
                "email": to_email
            }
        ],
        "subject": subject,
        "htmlContent": html_body
    }

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }

    try:
        response = requests.post(
            BREVO_API_URL,
            json=payload,
            headers=headers,
            timeout=15
        )

        if response.status_code == 201:
            logger.info(
                f"Email sent successfully to {to_email}"
            )
            return True

        logger.error(
            f"Brevo API error: "
            f"{response.status_code} - {response.text}"
        )
        return False

    except requests.exceptions.RequestException as e:
        logger.error(
            f"Brevo API connection error: {e}"
        )
        return False


def send_otp_email(receiver_email: str, otp: str) -> bool:
    """
    Sends a 6-digit OTP to the user's email.
    """

    subject = f"{otp} is your Fury AI verification code"

    html = f"""
    <div style="
        font-family: sans-serif;
        max-width: 600px;
        margin: auto;
        padding: 20px;
        border: 1px solid #eee;
        border-radius: 10px;
    ">

        <h2 style="color: #4285f4;">
            Verify Your Email
        </h2>

        <p>
            To complete your registration, please use
            the following one-time password (OTP):
        </p>

        <div style="
            background: #f4f4f4;
            padding: 15px;
            text-align: center;
            font-size: 32px;
            font-weight: bold;
            letter-spacing: 5px;
            border-radius: 5px;
            color: #333;
        ">
            {otp}
        </div>

        <p style="
            margin-top: 20px;
            color: #666;
        ">
            This code will expire in 10 minutes.
            If you didn't request this, you can safely
            ignore this email.
        </p>

        <hr style="
            border: none;
            border-top: 1px solid #eee;
            margin: 20px 0;
        ">

        <p style="
            font-size: 12px;
            color: #999;
        ">
            © 2026 Fayaz Ahmed Shaik. All rights reserved.
        </p>

    </div>
    """

    return _send_email(
        receiver_email,
        subject,
        html
    )


def send_welcome_email(receiver_email: str) -> bool:
    """
    Sends a welcome email after successful registration.
    """

    subject = "Welcome to Fury AI!"

    html = """
    <div style="
        font-family: sans-serif;
        max-width: 600px;
        margin: auto;
        padding: 20px;
        border: 1px solid #eee;
        border-radius: 10px;
    ">

        <h2 style="
            color: #4285f4;
            text-align: center;
        ">
            You're All Set!
        </h2>

        <p>Hello,</p>

        <p>
            Your account has been successfully verified.
            Welcome to <strong>Fury AI</strong> —
            your personal AI voice assistant.
        </p>

        <p>
            You can now start chatting, exploring history,
            and using our voice processing features.
        </p>

        <p style="color: #666;">
            If you have any questions, feel free to reply
            to this email.
        </p>

        <hr style="
            border: none;
            border-top: 1px solid #eee;
            margin: 20px 0;
        ">

        <p style="
            font-size: 12px;
            color: #999;
        ">
            © 2026 Fayaz Ahmed Shaik. All rights reserved.
        </p>

    </div>
    """

    return _send_email(
        receiver_email,
        subject,
        html
    )