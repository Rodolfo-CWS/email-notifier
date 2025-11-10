#!/usr/bin/env python3
"""Script para probar el filtro de fechas de emails"""

import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import os
from datetime import datetime, timedelta

# Configuración desde variables de entorno
IMAP_SERVER = os.getenv('IMAP_SERVER', 'mail.cwscompany.com')
IMAP_PORT = int(os.getenv('IMAP_PORT', '143'))
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')

def is_email_recent(msg, max_days=7):
    """Verifica si el email tiene menos de max_days días de antigüedad"""
    try:
        date_str = msg.get('Date')
        if not date_str:
            print(f"  ⚠️  Email sin fecha - se procesará")
            return True

        email_date = parsedate_to_datetime(date_str)

        # Normalizar a datetime naive para comparación
        if email_date.tzinfo is not None:
            email_date = email_date.replace(tzinfo=None)

        # Calcular la diferencia
        now = datetime.now()
        age_days = (now - email_date).days

        print(f"  📅 Fecha email: {email_date}")
        print(f"  📅 Fecha actual: {now}")
        print(f"  ⏰ Antigüedad: {age_days} días")
        print(f"  ✓ Procesará: {'SÍ' if age_days <= max_days else 'NO (>7 días)'}")

        return age_days <= max_days
    except Exception as e:
        print(f"  ❌ Error al verificar fecha: {e}")
        return True

def test_email_filter():
    """Prueba el filtro de emails sin enviar notificaciones"""
    try:
        print(f"\n🔍 Conectando a {IMAP_SERVER}...")

        # Conectar a IMAP
        mail = imaplib.IMAP4(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select('INBOX')

        print("✅ Conectado exitosamente\n")

        # Buscar emails no leídos
        status, messages = mail.search(None, 'UNSEEN')
        email_ids = messages[0].split()

        if not email_ids:
            print("📭 No hay emails no leídos")
            mail.logout()
            return

        print(f"📬 {len(email_ids)} email(s) no leído(s)\n")

        emails_recientes = 0
        emails_antiguos = 0

        # Analizar cada email
        for i, email_id in enumerate(email_ids, 1):
            print(f"{'='*60}")
            print(f"Email {i}/{len(email_ids)} (ID: {email_id.decode()})")
            print(f"{'='*60}")

            # Obtener email (sin marcar como leído)
            status, msg_data = mail.fetch(email_id, '(RFC822)')

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    # Extraer información básica
                    sender = msg.get('From', 'Desconocido')
                    subject_raw = msg.get('Subject')
                    decoded_parts = decode_header(subject_raw) if subject_raw else []
                    subject = ''.join([
                        part.decode(enc or 'utf-8') if isinstance(part, bytes) else str(part)
                        for part, enc in decoded_parts
                    ]) if decoded_parts else "Sin asunto"

                    print(f"  📧 De: {sender}")
                    print(f"  📝 Asunto: {subject}")
                    print(f"  📅 Fecha: {msg.get('Date', 'Sin fecha')}")

                    # Verificar si es reciente
                    if is_email_recent(msg, max_days=7):
                        emails_recientes += 1
                    else:
                        emails_antiguos += 1

                    print()

        print(f"{'='*60}")
        print(f"📊 RESUMEN:")
        print(f"  ✅ Emails recientes (≤7 días): {emails_recientes}")
        print(f"  ❌ Emails antiguos (>7 días): {emails_antiguos}")
        print(f"  📬 Total no leídos: {len(email_ids)}")
        print(f"{'='*60}\n")

        mail.logout()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Verificar variables de entorno
    required_vars = ['EMAIL_USER', 'EMAIL_PASS']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"❌ Faltan variables de entorno: {', '.join(missing_vars)}")
        print("💡 Asegúrate de tener un archivo .env con las credenciales")
        exit(1)

    print("🧪 Script de prueba - Filtro de fechas")
    print("📧 Email:", EMAIL_USER)
    test_email_filter()
