"""
RutasFast - Email Service using Resend
Fallback mode if RESEND_API_KEY not configured
"""
import os
import asyncio
import logging
import resend
from typing import Optional

logger = logging.getLogger(__name__)

# Initialize Resend
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "onboarding@resend.dev")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:3000")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
    logger.info("Resend email service configured")
else:
    logger.warning("RESEND_API_KEY not configured - email service disabled")


def is_email_configured() -> bool:
    """Check if email service is available"""
    return bool(RESEND_API_KEY)


async def send_email(
    to_email: str,
    subject: str,
    html_content: str
) -> dict:
    """
    Send email using Resend API
    Returns: {"success": bool, "message": str, "email_id": Optional[str]}
    """
    if not RESEND_API_KEY:
        logger.warning(f"Email not sent (service disabled): {subject} -> {to_email}")
        return {
            "success": False,
            "message": "No hay servicio de email configurado",
            "email_id": None
        }
    
    params = {
        "from": EMAIL_FROM,
        "to": [to_email],
        "subject": subject,
        "html": html_content
    }
    
    try:
        # Run sync SDK in thread to keep FastAPI non-blocking
        email = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Email sent: {subject} -> {to_email}")
        return {
            "success": True,
            "message": f"Email enviado a {to_email}",
            "email_id": email.get("id")
        }
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return {
            "success": False,
            "message": f"Error enviando email: {str(e)}",
            "email_id": None
        }


async def send_approval_email(user_email: str, user_name: str) -> dict:
    """Send account approval notification"""
    html = f"""
    <div style="font-family: 'IBM Plex Sans', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #701111; font-family: 'Chivo', sans-serif; margin: 0;">FAST</h1>
            <p style="color: #57534E; margin: 5px 0;">RutasFast</p>
        </div>
        
        <h2 style="color: #1C1917;">¡Cuenta Aprobada!</h2>
        
        <p style="color: #57534E; line-height: 1.6;">
            Hola {user_name},
        </p>
        
        <p style="color: #57534E; line-height: 1.6;">
            Tu cuenta de RutasFast ha sido verificada y aprobada por el administrador.
            Ya puedes acceder a la aplicación y comenzar a crear tus hojas de ruta.
        </p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{APP_BASE_URL}/app/login" 
               style="background-color: #701111; color: white; padding: 14px 28px; 
                      text-decoration: none; border-radius: 50px; font-weight: 600;
                      display: inline-block;">
                Iniciar Sesión
            </a>
        </div>
        
        <p style="color: #A8A29E; font-size: 12px; text-align: center; margin-top: 40px;">
            Federación Asturiana Sindical del Taxi (FAST)<br>
            Este es un email automático, no responda a este mensaje.
        </p>
    </div>
    """
    return await send_email(user_email, "Cuenta aprobada – RutasFast", html)


async def send_password_reset_email(user_email: str, user_name: str, reset_token: str) -> dict:
    """Send password reset link"""
    reset_url = f"{APP_BASE_URL}/app/reset-password?token={reset_token}"
    
    html = f"""
    <div style="font-family: 'IBM Plex Sans', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #701111; font-family: 'Chivo', sans-serif; margin: 0;">FAST</h1>
            <p style="color: #57534E; margin: 5px 0;">RutasFast</p>
        </div>
        
        <h2 style="color: #1C1917;">Recuperar Contraseña</h2>
        
        <p style="color: #57534E; line-height: 1.6;">
            Hola {user_name},
        </p>
        
        <p style="color: #57534E; line-height: 1.6;">
            Has solicitado restablecer tu contraseña. Haz clic en el siguiente botón para crear una nueva:
        </p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" 
               style="background-color: #701111; color: white; padding: 14px 28px; 
                      text-decoration: none; border-radius: 50px; font-weight: 600;
                      display: inline-block;">
                Restablecer Contraseña
            </a>
        </div>
        
        <p style="color: #57534E; line-height: 1.6;">
            Este enlace expira en <strong>60 minutos</strong>. Si no solicitaste este cambio, ignora este email.
        </p>
        
        <p style="color: #A8A29E; font-size: 12px; margin-top: 20px;">
            Si el botón no funciona, copia y pega este enlace en tu navegador:<br>
            <a href="{reset_url}" style="color: #701111;">{reset_url}</a>
        </p>
        
        <p style="color: #A8A29E; font-size: 12px; text-align: center; margin-top: 40px;">
            Federación Asturiana Sindical del Taxi (FAST)<br>
            Este es un email automático, no responda a este mensaje.
        </p>
    </div>
    """
    return await send_email(user_email, "Recuperar contraseña – RutasFast", html)
