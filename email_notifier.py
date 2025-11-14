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

# Configuración desde variables de entorno
IMAP_SERVER = os.getenv('IMAP_SERVER', 'mail.cwscompany.com')
IMAP_PORT = int(os.getenv('IMAP_PORT', '143'))
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Directorio para datos persistentes
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
# Crear directorio si no existe
os.makedirs(DATA_DIR, exist_ok=True)

# Archivo para trackear último email procesado
LAST_EMAIL_FILE = os.path.join(DATA_DIR, 'last_email_id.txt')
TRACKING_FILE = os.path.join(DATA_DIR, 'email_tracking.json')

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

def save_email_to_tracking(email_id, sender, subject, body, email_date):
    """Guarda información completa del email en el tracking"""
    try:
        # Cargar tracking existente
        if os.path.exists(TRACKING_FILE):
            with open(TRACKING_FILE, 'r') as f:
                tracking = json.load(f)
        else:
            tracking = {}

        # Extraer email del remitente (formato: "Nombre <email@ejemplo.com>")
        sender_email = sender
        if '<' in sender and '>' in sender:
            sender_email = sender.split('<')[1].split('>')[0].strip()

        # Guardar información completa
        tracking[str(email_id)] = {
            "sender": sender,
            "sender_email": sender_email,
            "subject": subject,
            "body_preview": body[:800],  # Primeras 800 caracteres
            "email_date": email_date,
            "status": "new",
            "created_at": datetime.now().isoformat()
        }

        # Guardar archivo
        with open(TRACKING_FILE, 'w') as f:
            json.dump(tracking, f, indent=2)

        print(f"💾 Email {email_id} guardado en tracking")

    except Exception as e:
        print(f"❌ Error al guardar en tracking: {e}")

def mark_email_as_read(email_id):
    """Marca un email como leído en el servidor IMAP"""
    try:
        print(f"📖 Marcando email {email_id} como leído...")

        # Conectar a IMAP
        mail = imaplib.IMAP4(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select('INBOX')

        # Marcar como leído usando el flag \Seen
        mail.store(str(email_id).encode(), '+FLAGS', '\\Seen')

        mail.logout()
        print(f"✅ Email {email_id} marcado como leído")

    except Exception as e:
        print(f"⚠️ No se pudo marcar email {email_id} como leído: {e}")
        # No falla la operación si no se puede marcar como leído

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
        print(f"Error al verificar fecha del email: {e}")
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
        print(f"Error al resumir email: {e}")
        return f"{sender}: {subject}"

def send_telegram_notification(message, email_id, subject, sender):
    """Envía notificación por Telegram con botones inline"""
    try:
        # Validar variables de entorno
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("❌ Error: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no están configurados")
            return None

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

        # Crear botones inline - Menú simplificado
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "❌ Descartar", "callback_data": f"done_{email_id}"},
                    {"text": "📋 Ver Detalles", "callback_data": f"details_{email_id}"}
                ]
            ]
        }

        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"📧 {message}",
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard)
        }

        print(f"📤 Enviando notificación a Telegram...")
        response = requests.post(url, data=data, timeout=10)
        result = response.json()

        # Verificar si la respuesta fue exitosa
        if response.status_code == 200 and result.get('ok'):
            print(f"✅ Notificación enviada exitosamente")
            return result
        else:
            print(f"❌ Error en respuesta de Telegram:")
            print(f"   Status Code: {response.status_code}")
            print(f"   Respuesta: {result}")
            return None

    except requests.exceptions.Timeout:
        print(f"❌ Timeout al enviar notificación a Telegram")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de red al enviar notificación Telegram: {e}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado al enviar notificación Telegram: {e}")
        return None

def check_emails():
    """Revisa emails nuevos y envía notificaciones"""
    try:
        print(f"[{datetime.now()}] Conectando a {IMAP_SERVER}...")
        
        # Conectar a IMAP
        mail = imaplib.IMAP4(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select('INBOX')
        
        print("✅ Conectado exitosamente")
        
        # Buscar emails no leídos
        status, messages = mail.search(None, 'UNSEEN')
        email_ids = messages[0].split()
        
        if not email_ids:
            print("No hay emails nuevos")
            mail.logout()
            return
        
        print(f"📬 {len(email_ids)} email(s) nuevo(s)")
        
        # Obtener último ID procesado
        last_id = get_last_processed_id()
        
        # Procesar cada email nuevo
        for email_id in email_ids:
            num_id = int(email_id)

            # Si ya procesamos este email, saltarlo
            if last_id and num_id <= last_id:
                continue

            # Obtener email sin marcarlo como leído usando BODY.PEEK
            status, msg_data = mail.fetch(email_id, '(BODY.PEEK[])')

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    # Verificar si el email tiene menos de una semana
                    if not is_email_recent(msg, max_days=7):
                        print(f"\n--- Email ignorado (más de 7 días) ---")
                        print(f"De: {msg.get('From', 'Desconocido')}")
                        print(f"Fecha: {msg.get('Date', 'Sin fecha')}")
                        # Guardar como procesado para no revisarlo de nuevo
                        save_last_processed_id(num_id)
                        continue

                    # Extraer información
                    sender = msg.get('From', 'Desconocido')
                    subject = decode_email_subject(msg.get('Subject'))
                    body = get_email_body(msg)

                    print(f"\n--- Procesando email ---")
                    print(f"De: {sender}")
                    print(f"Asunto: {subject}")
                    print(f"Fecha: {msg.get('Date', 'Sin fecha')}")

                    # Resumir con GPT
                    summary = summarize_email(sender, subject, body)
                    print(f"Resumen: {summary}")

                    # Guardar información completa del email en tracking (incluyendo resumen)
                    save_email_to_tracking(num_id, sender, subject, body, msg.get('Date', 'Sin fecha'))

                    # Actualizar tracking con el resumen generado
                    if os.path.exists(TRACKING_FILE):
                        with open(TRACKING_FILE, 'r') as f:
                            tracking = json.load(f)
                        tracking[str(num_id)]["message_text"] = summary
                        with open(TRACKING_FILE, 'w') as f:
                            json.dump(tracking, f, indent=2)

                    # Enviar notificación con botones
                    send_telegram_notification(summary, num_id, subject, sender)

                    # Guardar último ID procesado
                    save_last_processed_id(num_id)

                    time.sleep(1)  # Evitar rate limits
        
        mail.logout()
        print(f"\n✅ Proceso completado [{datetime.now()}]\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Verificar variables de entorno
    required_vars = ['EMAIL_USER', 'EMAIL_PASS', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Faltan variables de entorno: {', '.join(missing_vars)}")
        exit(1)
    
    print("🚀 Iniciando Email Notifier...")
    print(f"📧 Email: {EMAIL_USER}")
    print(f"🤖 Bot Token: {TELEGRAM_BOT_TOKEN[:10]}...")
    print(f"💬 Chat ID: {TELEGRAM_CHAT_ID}")
    
    check_emails()
