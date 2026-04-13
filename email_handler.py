"""
email_handler.py
© 2026 Fayaz Ahmed Shaik. All rights reserved.
─────────────────────────────────────────────
Handles sending transactional emails using Resend.
"""

import os
import logging
import resend

logger = logging.getLogger(__name__)

# Configure Resend API Key
resend.api_key = os.getenv("RESEND_API_KEY")

def send_otp_email(receiver_email: str, otp: str) -> bool:
    """
    Sends a 6-digit OTP to the user's email for verification.
    """
    if not resend.api_key:
        logger.error("RESEND_API_KEY is not set. Email sending failed.")
        return False

    try:
        params = {
            "from": "Fury AI <onboarding@resend.dev>",
            "to": [receiver_email],
            "subject": f"{otp} is your Fury AI verification code",
            "html": f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                <h2 style="color: #4285f4;">Verify Your Email</h2>
                <p>To complete your registration, please use the following one-time password (OTP):</p>
                <div style="background: #f4f4f4; padding: 15px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 5px; border-radius: 5px; color: #333;">
                    {otp}
                </div>
                <p style="margin-top: 20px; color: #666;">This code will expire in 10 minutes. If you didn't request this, you can safely ignore this email.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="font-size: 12px; color: #999;">© 2026 Fayaz Ahmed Shaik. All rights reserved.</p>
            </div>
            """,
        }
        resend.Emails.send(params)
        logger.info(f"Verification OTP sent to {receiver_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {receiver_email}: {e}")
        return False

def send_welcome_email(receiver_email: str) -> bool:
    """
    Sends a welcome email after successful registration.
    """
    if not resend.api_key:
        return False

    try:
        params = {
            "from": "Fury AI <onboarding@resend.dev>",
            "to": [receiver_email],
            "subject": "Welcome to Fury AI!",
            "html": f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                <h2 style="color: #4285f4; text-align: center;">You're All Set!</h2>
                <p>Hello,</p>
                <p>Your account has been successfully verified. Welcome to <strong>Fury AI</strong> — your personal AI voice assistant.</p>
                <p>You can now start chatting, exploring history, and using our voice processing features.</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="#" style="background: #4285f4; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Get Started</a>
                </div>
                <p style="color: #666;">If you have any questions, feel free to reply to this email.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="font-size: 12px; color: #999;">© 2026 Fayaz Ahmed Shaik. All rights reserved.</p>
            </div>
            """,
        }
        resend.Emails.send(params)
        logger.info(f"Welcome email sent to {receiver_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send welcome email to {receiver_email}: {e}")
        return False
