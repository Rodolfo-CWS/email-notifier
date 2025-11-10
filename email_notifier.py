import imaplib
import email
from email.header import decode_header
import os
from datetime import datetime
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

def send_telegram_notification(message):
    """Envía notificación por Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"📧 {message}",
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data)
        return response.json()
    except Exception as e:
        print(f"Error al enviar notificación Telegram: {e}")
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
            
            # Obtener email
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Extraer información
                    sender = msg.get('From', 'Desconocido')
                    subject = decode_email_subject(msg.get('Subject'))
                    body = get_email_body(msg)
                    
                    print(f"\n--- Procesando email ---")
                    print(f"De: {sender}")
                    print(f"Asunto: {subject}")
                    
                    # Resumir con GPT
                    summary = summarize_email(sender, subject, body)
                    print(f"Resumen: {summary}")
                    
                    # Enviar notificación
                    send_telegram_notification(summary)
                    
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
