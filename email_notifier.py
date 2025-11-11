import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import os
from datetime import datetime, timedelta
import requests
from openai import OpenAI
import time
import json
from urllib.parse import quote
import re

# Configuración desde variables de entorno
IMAP_SERVER = os.getenv('IMAP_SERVER', 'mail.cwscompany.com')
IMAP_PORT = int(os.getenv('IMAP_PORT', '143'))
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
WEBMAIL_URL = os.getenv('WEBMAIL_URL', 'https://cwscompany.com/webmail')
WEBMAIL_TYPE = os.getenv('WEBMAIL_TYPE', 'generic')  # roundcube, cpanel, generic

# Archivo para trackear último email procesado
LAST_EMAIL_FILE = '/tmp/last_email_id.txt'

def get_last_processed_id():
    """Obtiene el ID del último email procesado"""
    try:
        if os.path.exists(LAST_EMAIL_FILE):
            with open(LAST_EMAIL_FILE, 'r') as f:
                return int(f.read().strip())
    except:
        pass
    return None

def save_last_processed_id(email_id):
    """Guarda el ID del último email procesado"""
    with open(LAST_EMAIL_FILE, 'w') as f:
        f.write(str(email_id))

def decode_email_subject(subject):
    """Decodifica el asunto del email"""
    if subject is None:
        return "Sin asunto"
    
    decoded_parts = decode_header(subject)
    subject_parts = []
    
    for content, encoding in decoded_parts:
        if isinstance(content, bytes):
            try:
                subject_parts.append(content.decode(encoding or 'utf-8'))
            except:
                subject_parts.append(content.decode('utf-8', errors='ignore'))
        else:
            subject_parts.append(str(content))
    
    return ''.join(subject_parts)

def is_email_recent(msg, max_days=7):
    """Verifica si el email tiene menos de max_days días de antigüedad"""
    try:
        date_str = msg.get('Date')
        if not date_str:
            # Si no tiene fecha, asumimos que es reciente para no perderlo
            return True

        email_date = parsedate_to_datetime(date_str)
        # Hacer el datetime offset-aware si no lo es
        if email_date.tzinfo is None:
            email_date = email_date.replace(tzinfo=None)

        # Calcular la diferencia
        now = datetime.now()
        age_days = (now - email_date.replace(tzinfo=None)).days

        return age_days <= max_days
    except Exception as e:
        print(f"Error al verificar fecha del email: {e}", flush=True)
        # En caso de error, procesamos el email para no perderlo
        return True

def get_email_body(msg):
    """Extrae el cuerpo del email"""
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
                except:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            body = str(msg.get_payload())

    # Limitar a primeros 1000 caracteres para el resumen
    return body[:1000]

def summarize_email(sender, subject, body):
    """Resume el email usando GPT-4o-mini"""
    try:
        # Crear cliente OpenAI sin proxies
        import os
        os.environ.pop('http_proxy', None)
        os.environ.pop('https_proxy', None)
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)
        
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = f"""Resume este email en máximo 15 palabras, mencionando el remitente y el tema clave.
        
De: {sender}
Asunto: {subject}
Contenido: {body}

Formato deseado: "[Nombre] de [Empresa/Área] [acción/necesidad]..."
Ejemplo: "Juan de Contabilidad necesita facturas del mes anterior"
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un asistente que resume emails de manera concisa y clara en español."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.3
        )
        
        summary = response.choices[0].message.content.strip()
        return summary
        
    except Exception as e:
        print(f"Error al resumir email: {e}", flush=True)
        return f"{sender}: {subject}"

def build_email_url(message_id=None, subject=None, sender=None):
    """Construye la URL para abrir el email"""

    # Si tenemos remitente, crear un mailto: link que abre la app Mail nativa
    # Esto funciona mucho mejor en iPhone que abrir webmail
    if sender:
        # Extraer el email del remitente (formato puede ser "Nombre <email@domain.com>")
        email_match = re.search(r'<(.+?)>', sender)
        sender_email = email_match.group(1) if email_match else sender

        # Limpiar el asunto si existe
        if subject:
            # Remover caracteres problemáticos en URLs
            clean_subject = subject.replace('\n', ' ').replace('\r', ' ')
            # URL encode será manejado por Telegram
            mailto_url = f"mailto:{sender_email}?subject=Re: {clean_subject}"
        else:
            mailto_url = f"mailto:{sender_email}"

        return mailto_url

    # Si no tenemos remitente, usar webmail como fallback
    return WEBMAIL_URL.rstrip('/')

def send_telegram_notification(message, sender="", subject="", message_id=None):
    """Envía notificación por Telegram con email clickeable"""
    try:
        print(f"\n🔔 Enviando notificación a Telegram...", flush=True)

        # Extraer email del remitente para mostrarlo en el mensaje
        sender_email = ""
        if sender:
            email_match = re.search(r'<(.+?)>', sender)
            sender_email = email_match.group(1) if email_match else sender

        # Construir mensaje con el email del remitente
        # En Telegram, los emails son automáticamente clickeables y abren Mail nativa
        telegram_message = f"📧 {message}"
        if sender_email:
            telegram_message += f"\n\n✉️ {sender_email}"

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": telegram_message,
            "parse_mode": "HTML"
        }

        print(f"   Chat ID: {TELEGRAM_CHAT_ID}", flush=True)
        print(f"   Mensaje: {telegram_message}", flush=True)

        response = requests.post(url, data=data)
        result = response.json()

        print(f"   Respuesta Telegram: {result}", flush=True)

        if result.get('ok'):
            print(f"✅ Notificación enviada exitosamente a Telegram", flush=True)
        else:
            print(f"❌ Telegram respondió con error: {result}", flush=True)

        return result
    except Exception as e:
        print(f"❌ Error al enviar notificación Telegram: {e}", flush=True)
        import traceback
        print(f"   Traceback: {traceback.format_exc()}", flush=True)
        return None

def check_emails():
    """Revisa emails nuevos y envía notificaciones"""
    try:
        print(f"[{datetime.now()}] Conectando a {IMAP_SERVER}...", flush=True)

        # Conectar a IMAP
        mail = imaplib.IMAP4(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select('INBOX')

        print("✅ Conectado exitosamente", flush=True)

        # Buscar emails no leídos
        status, messages = mail.search(None, 'UNSEEN')
        email_ids = messages[0].split()

        if not email_ids:
            print("No hay emails nuevos", flush=True)
            mail.logout()
            return

        print(f"📬 {len(email_ids)} email(s) nuevo(s)", flush=True)

        # Obtener último ID procesado
        last_id = get_last_processed_id()
        print(f"   Último ID procesado: {last_id}", flush=True)
        print(f"   IDs de emails encontrados: {[int(eid) for eid in email_ids]}", flush=True)

        # Procesar cada email nuevo
        for email_id in email_ids:
            num_id = int(email_id)

            # Si ya procesamos este email, saltarlo
            if last_id and num_id <= last_id:
                print(f"   ⏭️  Saltando email ID {num_id} (ya procesado, last_id={last_id})", flush=True)
                continue

            # Obtener email SIN marcarlo como leído usando BODY.PEEK
            # RFC822 marca como leído, BODY.PEEK[] NO lo marca
            status, msg_data = mail.fetch(email_id, '(BODY.PEEK[])')

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    # Verificar si el email tiene menos de una semana
                    if not is_email_recent(msg, max_days=7):
                        print(f"\n--- Email ignorado (más de 7 días) ---", flush=True)
                        print(f"De: {msg.get('From', 'Desconocido')}", flush=True)
                        print(f"Fecha: {msg.get('Date', 'Sin fecha')}", flush=True)
                        # Guardar como procesado para no revisarlo de nuevo
                        save_last_processed_id(num_id)
                        continue

                    # Extraer información
                    sender = msg.get('From', 'Desconocido')
                    subject = decode_email_subject(msg.get('Subject'))
                    body = get_email_body(msg)
                    message_id = msg.get('Message-ID', None)

                    print(f"\n--- Procesando email ---", flush=True)
                    print(f"De: {sender}", flush=True)
                    print(f"Asunto: {subject}", flush=True)
                    print(f"Fecha: {msg.get('Date', 'Sin fecha')}", flush=True)
                    if message_id:
                        print(f"Message-ID: {message_id}", flush=True)

                    # Resumir con GPT
                    summary = summarize_email(sender, subject, body)
                    print(f"Resumen: {summary}", flush=True)

                    # Enviar notificación con botón para abrir el email
                    send_telegram_notification(summary, sender, subject, message_id)

                    # Guardar último ID procesado
                    save_last_processed_id(num_id)

                    time.sleep(1)  # Evitar rate limits
        
        mail.logout()
        print(f"\n✅ Proceso completado [{datetime.now()}]\n", flush=True)

    except Exception as e:
        print(f"❌ Error: {e}", flush=True)

if __name__ == "__main__":
    # Verificar variables de entorno
    required_vars = ['EMAIL_USER', 'EMAIL_PASS', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"❌ Faltan variables de entorno: {', '.join(missing_vars)}", flush=True)
        exit(1)

    print("🚀 Iniciando Email Notifier...", flush=True)
    print(f"📧 Email: {EMAIL_USER}", flush=True)
    print(f"🤖 Bot Token: {TELEGRAM_BOT_TOKEN[:10]}...", flush=True)
    print(f"💬 Chat ID: {TELEGRAM_CHAT_ID}", flush=True)

    check_emails()
