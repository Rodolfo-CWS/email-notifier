import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import os
import json
from datetime import datetime, timedelta
import requests
from openai import OpenAI
import time

# Configuración desde variables de entorno
IMAP_SERVER = os.getenv('IMAP_SERVER', 'mail.cwscompany.com')
IMAP_PORT = int(os.getenv('IMAP_PORT', '143'))
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Archivo para trackear último email procesado
LAST_EMAIL_FILE = '/tmp/last_email_id.txt'
# Archivo para almacenar detalles de emails (para el botón "Ver detalles")
EMAIL_DETAILS_FILE = '/tmp/email_details.json'

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

def load_email_details():
    """Carga los detalles de emails almacenados"""
    try:
        if os.path.exists(EMAIL_DETAILS_FILE):
            with open(EMAIL_DETAILS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error al cargar detalles de emails: {e}")
    return {}

def save_email_details(email_id, details):
    """Guarda los detalles de un email para acceso posterior"""
    try:
        all_details = load_email_details()

        # Limpiar emails antiguos (mantener solo los últimos 100)
        if len(all_details) > 100:
            # Ordenar por timestamp y mantener los más recientes
            sorted_ids = sorted(all_details.keys(),
                               key=lambda x: all_details[x].get('timestamp', ''),
                               reverse=True)
            all_details = {k: all_details[k] for k in sorted_ids[:100]}

        all_details[str(email_id)] = details

        with open(EMAIL_DETAILS_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_details, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"Error al guardar detalles del email: {e}")

def get_email_details(email_id):
    """Obtiene los detalles de un email específico"""
    all_details = load_email_details()
    return all_details.get(str(email_id))

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

def send_telegram_notification(message, email_id=None):
    """Envía notificación por Telegram con botón 'Ver detalles'"""
    try:
        # Validar variables de entorno
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("❌ Error: TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no están configurados")
            return None

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

        # Preparar datos del mensaje
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"📧 {message}",
            "parse_mode": "HTML"
        }

        # Agregar botón "Ver detalles" si tenemos email_id
        if email_id:
            inline_keyboard = {
                "inline_keyboard": [[
                    {
                        "text": "📋 Ver detalles",
                        "callback_data": f"details_{email_id}"
                    }
                ]]
            }
            data["reply_markup"] = json.dumps(inline_keyboard)

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

def handle_callback_query(callback_query):
    """Maneja los callbacks de los botones de Telegram"""
    try:
        callback_id = callback_query.get('id')
        callback_data = callback_query.get('data', '')
        message = callback_query.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        message_id = message.get('message_id')

        # Verificar que es un callback de detalles
        if not callback_data.startswith('details_'):
            return False

        email_id = callback_data.replace('details_', '')
        details = get_email_details(email_id)

        if not details:
            # Responder que no se encontraron los detalles
            answer_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
            requests.post(answer_url, data={
                "callback_query_id": callback_id,
                "text": "⚠️ Detalles no disponibles (email antiguo)",
                "show_alert": True
            }, timeout=10)
            return False

        # Construir mensaje con detalles completos
        detail_text = f"""📧 <b>Detalles del Email</b>

<b>De:</b> {details.get('sender', 'Desconocido')}
<b>Asunto:</b> {details.get('subject', 'Sin asunto')}
<b>Fecha:</b> {details.get('date', 'Sin fecha')}

<b>Resumen:</b>
{details.get('summary', 'Sin resumen')}

<b>Contenido:</b>
{details.get('body', 'Sin contenido')[:2000]}"""

        # Editar el mensaje original para mostrar los detalles
        edit_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
        edit_data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": detail_text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps({
                "inline_keyboard": [[
                    {
                        "text": "📝 Ver resumen",
                        "callback_data": f"summary_{email_id}"
                    }
                ]]
            })
        }

        response = requests.post(edit_url, data=edit_data, timeout=10)
        result = response.json()

        # Responder al callback
        answer_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
        requests.post(answer_url, data={
            "callback_query_id": callback_id
        }, timeout=10)

        if response.status_code == 200 and result.get('ok'):
            print(f"✅ Detalles mostrados para email {email_id}")
            return True
        else:
            print(f"❌ Error al mostrar detalles: {result}")
            return False

    except Exception as e:
        print(f"❌ Error en handle_callback_query: {e}")
        return False

def handle_summary_callback(callback_query):
    """Maneja el callback para volver al resumen"""
    try:
        callback_id = callback_query.get('id')
        callback_data = callback_query.get('data', '')
        message = callback_query.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        message_id = message.get('message_id')

        if not callback_data.startswith('summary_'):
            return False

        email_id = callback_data.replace('summary_', '')
        details = get_email_details(email_id)

        if not details:
            answer_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
            requests.post(answer_url, data={
                "callback_query_id": callback_id,
                "text": "⚠️ Información no disponible",
                "show_alert": True
            }, timeout=10)
            return False

        # Volver al mensaje con resumen
        summary_text = f"📧 {details.get('summary', 'Sin resumen')}"

        edit_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
        edit_data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": summary_text,
            "parse_mode": "HTML",
            "reply_markup": json.dumps({
                "inline_keyboard": [[
                    {
                        "text": "📋 Ver detalles",
                        "callback_data": f"details_{email_id}"
                    }
                ]]
            })
        }

        response = requests.post(edit_url, data=edit_data, timeout=10)

        # Responder al callback
        answer_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
        requests.post(answer_url, data={
            "callback_query_id": callback_id
        }, timeout=10)

        return response.status_code == 200

    except Exception as e:
        print(f"❌ Error en handle_summary_callback: {e}")
        return False

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
                    email_date = msg.get('Date', 'Sin fecha')

                    print(f"\n--- Procesando email ---")
                    print(f"De: {sender}")
                    print(f"Asunto: {subject}")
                    print(f"Fecha: {email_date}")

                    # Resumir con GPT
                    summary = summarize_email(sender, subject, body)
                    print(f"Resumen: {summary}")

                    # Guardar detalles del email para el botón "Ver detalles"
                    email_details = {
                        'sender': sender,
                        'subject': subject,
                        'body': body,
                        'date': email_date,
                        'summary': summary,
                        'timestamp': datetime.now().isoformat()
                    }
                    save_email_details(num_id, email_details)

                    # Enviar notificación con botón "Ver detalles"
                    send_telegram_notification(summary, email_id=num_id)

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
