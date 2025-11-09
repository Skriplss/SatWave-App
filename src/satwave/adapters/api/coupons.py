from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from satwave.adapters.api.auth import get_current_user
from satwave.config.settings import get_settings


router = APIRouter(prefix="/coupons", tags=["coupons"])


def _send_email(to: str, subject: str, text: str, html: Optional[str] = None) -> None:
    settings = get_settings()
    if not (settings.smtp_host and settings.smtp_user and settings.smtp_password and settings.smtp_from):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SMTP is not configured on the server",
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


@router.post("/send-code")
async def send_coupon_code(
    payload: dict,
    user=Depends(get_current_user),
):
    """Send coupon code to the user's email via SMTP.

    Expected payload: { code: string, title?: string, expires_at?: string, email?: string }
    If email is omitted, uses email from Supabase JWT claims.
    """
    code = (payload.get("code") or "").strip()
    title = (payload.get("title") or "Coupon code").strip()
    expires_at = (payload.get("expires_at") or "").strip()
    email = (payload.get("email") or user.get("email") or "").strip()

    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing code")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing email")

    subject = f"Your coupon code: {code}"
    text_lines = [
        f"Here is your coupon code: {code}",
    ]
    if title:
        text_lines.insert(0, title)
    if expires_at:
        text_lines.append(f"Expires: {expires_at}")
    text = "\n".join(text_lines)

    html = f"""
    <div style='font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial'>
      <h2>{title}</h2>
      <p>Here is your coupon code:</p>
      <p style='font-size:20px;font-weight:700'>{code}</p>
      {f"<p>Expires: {expires_at}</p>" if expires_at else ""}
    </div>
    """

    _send_email(email, subject, text, html)
    return {"ok": True}

