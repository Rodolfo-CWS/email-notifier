from flask import Flask, jsonify, request
import os
import json
from datetime import datetime, timedelta
import requests
import html
from urllib.parse import quote
from email_notifier import check_emails, mark_email_as_read

app = Flask(__name__)

# Directorio para datos persistentes
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
# Crear directorio si no existe
os.makedirs(DATA_DIR, exist_ok=True)

# Archivo para tracking de emails
TRACKING_FILE = os.path.join(DATA_DIR, 'email_tracking.json')
REMINDERS_FILE = os.path.join(DATA_DIR, 'email_reminders.json')

# Migrar archivos de /tmp/ a ./data/ si existen (solo la primera vez)
def migrate_from_tmp():
    """Migra archivos de tracking de /tmp/ a ./data/ si existen"""
    old_tracking = '/tmp/email_tracking.json'
    old_reminders = '/tmp/email_reminders.json'

    try:
        # Migrar tracking
        if os.path.exists(old_tracking) and not os.path.exists(TRACKING_FILE):
            import shutil
            shutil.copy2(old_tracking, TRACKING_FILE)
            print(f"✅ Migrado tracking de {old_tracking} a {TRACKING_FILE}")

        # Migrar reminders
        if os.path.exists(old_reminders) and not os.path.exists(REMINDERS_FILE):
            import shutil
            shutil.copy2(old_reminders, REMINDERS_FILE)
            print(f"✅ Migrado reminders de {old_reminders} a {REMINDERS_FILE}")
    except Exception as e:
        print(f"⚠️ Error en migración (no crítico): {e}")

# Ejecutar migración al iniciar
migrate_from_tmp()

@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "service": "Email Notifier",
        "email": os.getenv('EMAIL_USER', 'Not configured')
    })

@app.route('/check')
def check():
    """Endpoint para que el cron job ejecute la revisión de emails"""
    try:
        check_emails()
        return jsonify({"status": "success", "message": "Emails checked"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health')
def health():
    """Health check para mantener el servicio activo"""
    return jsonify({"status": "healthy"})

@app.route('/test-telegram')
def test_telegram():
    """Endpoint para probar la configuración de Telegram"""
    import requests

    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

    # Verificar variables
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return jsonify({
            "status": "error",
            "message": "Variables de entorno no configuradas",
            "missing": {
                "TELEGRAM_BOT_TOKEN": not TELEGRAM_BOT_TOKEN,
                "TELEGRAM_CHAT_ID": not TELEGRAM_CHAT_ID
            }
        }), 400

    # Probar el bot
    try:
        # Verificar bot
        bot_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        bot_response = requests.get(bot_url, timeout=10)
        bot_result = bot_response.json()

        if not bot_result.get('ok'):
            return jsonify({
                "status": "error",
                "step": "bot_verification",
                "message": "Token inválido",
                "response": bot_result
            }), 401

        bot_info = bot_result.get('result', {})

        # Enviar mensaje de prueba
        send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        send_data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": "🧪 Test desde Render\n\n✅ Tu configuración de Telegram está funcionando correctamente!",
            "parse_mode": "HTML"
        }

        send_response = requests.post(send_url, data=send_data, timeout=10)
        send_result = send_response.json()

        if send_response.status_code == 200 and send_result.get('ok'):
            return jsonify({
                "status": "success",
                "message": "✅ Configuración de Telegram correcta",
                "bot": {
                    "username": bot_info.get('username'),
                    "id": bot_info.get('id'),
                    "name": bot_info.get('first_name')
                },
                "test_message_sent": True,
                "message_id": send_result.get('result', {}).get('message_id')
            }), 200
        else:
            return jsonify({
                "status": "error",
                "step": "send_message",
                "message": "Error al enviar mensaje",
                "error_code": send_result.get('error_code'),
                "description": send_result.get('description'),
                "response": send_result
            }), 400

    except requests.exceptions.Timeout:
        return jsonify({
            "status": "error",
            "message": "Timeout al conectar con Telegram"
        }), 504
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# ============================================
# Sistema de Tracking y Recordatorios
# ============================================

def load_tracking():
    """Carga el archivo de tracking"""
    try:
        if os.path.exists(TRACKING_FILE):
            with open(TRACKING_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_tracking(data):
    """Guarda el archivo de tracking"""
    with open(TRACKING_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_reminders():
    """Carga los recordatorios programados"""
    try:
        if os.path.exists(REMINDERS_FILE):
            with open(REMINDERS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_reminders(data):
    """Guarda los recordatorios"""
    with open(REMINDERS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def edit_telegram_message(chat_id, message_id, text, reply_markup=None):
    """Edita un mensaje de Telegram"""
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"

    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    }

    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)

    print(f"🔧 Editando mensaje {message_id} en chat {chat_id}")
    print(f"🔧 Texto length: {len(text)} caracteres")

    response = requests.post(url, data=data, timeout=10)
    result = response.json()

    print(f"🔧 Respuesta de Telegram: {response.status_code}")
    print(f"🔧 Resultado: {result}")

    if not result.get('ok'):
        print(f"❌ ERROR al editar mensaje: {result.get('description')}")

    return result

def answer_callback_query(callback_query_id, text):
    """Responde a un callback query (notificación pequeña en Telegram)"""
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery"

    data = {
        "callback_query_id": callback_query_id,
        "text": text,
        "show_alert": False
    }

    requests.post(url, data=data, timeout=10)

def create_time_menu(email_id):
    """Crea el menú de selección de tiempo para recordatorios"""
    return {
        "inline_keyboard": [
            [
                {"text": "⏰ 15 minutos", "callback_data": f"remind_{email_id}_15m"},
                {"text": "⏰ 1 hora", "callback_data": f"remind_{email_id}_1h"}
            ],
            [
                {"text": "⏰ 3 horas", "callback_data": f"remind_{email_id}_3h"},
                {"text": "🌅 Mañana 9 AM", "callback_data": f"remind_{email_id}_tomorrow"}
            ],
            [
                {"text": "📅 En 2 días", "callback_data": f"remind_{email_id}_2days"},
                {"text": "📅 Esta semana", "callback_data": f"remind_{email_id}_week"}
            ],
            [
                {"text": "⬅️ Volver", "callback_data": f"back_{email_id}"}
            ]
        ]
    }

def create_main_menu(email_id):
    """Crea el menú principal de botones - Simple y limpio"""
    return {
        "inline_keyboard": [
            [
                {"text": "❌ Descartar", "callback_data": f"done_{email_id}"},
                {"text": "📋 Ver Detalles", "callback_data": f"details_{email_id}"}
            ]
        ]
    }

def create_details_menu(email_id, sender_email, subject):
    """Crea el menú de detalles con acciones"""
    # Crear URL mailto para responder (codificar subject para evitar caracteres inválidos)
    mailto_url = f"mailto:{sender_email}?subject={quote('Re: ' + subject)}"

    return {
        "inline_keyboard": [
            [
                {"text": "📤 Compartir", "callback_data": f"share_{email_id}"},
                {"text": "📧 Responder", "url": mailto_url}
            ],
            [
                {"text": "🤖 Sugerencia", "callback_data": f"suggest_{email_id}"}
            ],
            [
                {"text": "⬅️ Volver", "callback_data": f"back_{email_id}"}
            ]
        ]
    }

def create_post_action_menu(email_id, sender_email, subject):
    """Crea el menú después de realizar una acción (Compartir/Responder/Sugerencia)"""
    # Crear URL mailto para responder (codificar subject para evitar caracteres inválidos)
    mailto_url = f"mailto:{sender_email}?subject={quote('Re: ' + subject)}"

    return {
        "inline_keyboard": [
            [
                {"text": "📤 Compartir", "callback_data": f"share_{email_id}"},
                {"text": "📧 Responder", "url": mailto_url}
            ],
            [
                {"text": "🤖 Sugerencia", "callback_data": f"suggest_{email_id}"}
            ],
            [
                {"text": "🔔 Recuérdame en", "callback_data": f"remind_setup_{email_id}"}
            ],
            [
                {"text": "⬅️ Volver", "callback_data": f"back_{email_id}"}
            ]
        ]
    }

def create_suggestion_menu(email_id, sender_email, subject):
    """Crea el menú para cuando se muestra una sugerencia de IA"""
    # Crear URL mailto para responder (codificar subject para evitar caracteres inválidos)
    mailto_url = f"mailto:{sender_email}?subject={quote('Re: ' + subject)}"

    return {
        "inline_keyboard": [
            [
                {"text": "📤 Compartir", "callback_data": f"share_{email_id}"},
                {"text": "📧 Responder", "url": mailto_url}
            ],
            [
                {"text": "🔄 Refinar Sugerencia", "callback_data": f"refine_{email_id}"}
            ],
            [
                {"text": "🔔 Recuérdame en", "callback_data": f"remind_setup_{email_id}"}
            ],
            [
                {"text": "⬅️ Volver", "callback_data": f"back_{email_id}"}
            ]
        ]
    }

def calculate_reminder_time(time_option):
    """Calcula la fecha/hora del recordatorio según la opción seleccionada"""
    now = datetime.now()

    if time_option == "15m":
        return now + timedelta(minutes=15)
    elif time_option == "1h":
        return now + timedelta(hours=1)
    elif time_option == "3h":
        return now + timedelta(hours=3)
    elif time_option == "tomorrow":
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
    elif time_option == "2days":
        return now + timedelta(days=2)
    elif time_option == "week":
        return now + timedelta(days=7)

    return now + timedelta(hours=1)  # Default

def calculate_time_elapsed(created_at):
    """Calcula el tiempo transcurrido desde una fecha"""
    try:
        created = datetime.fromisoformat(created_at)
        elapsed = datetime.now() - created

        days = elapsed.days
        hours = int(elapsed.seconds // 3600)
        minutes = int((elapsed.seconds % 3600) // 60)

        if days > 0:
            return f"{days}d {hours}h"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    except:
        return "N/A"

def send_telegram_message(chat_id, text, reply_markup=None):
    """Envía un nuevo mensaje de Telegram"""
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }

    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)

    response = requests.post(url, data=data, timeout=10)
    return response.json()

def generate_ai_suggestion(sender, subject, body_preview):
    """Genera una sugerencia de acción usando IA"""
    try:
        from openai import OpenAI

        # Limpiar variables de proxy
        import os as os_module
        os_module.environ.pop('http_proxy', None)
        os_module.environ.pop('https_proxy', None)
        os_module.environ.pop('HTTP_PROXY', None)
        os_module.environ.pop('HTTPS_PROXY', None)

        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        prompt = f"""Analiza este email y sugiere una acción concreta y específica.

De: {sender}
Asunto: {subject}
Contenido: {body_preview}

Proporciona:
1. Acción recomendada (clara y específica)
2. Prioridad (Alta/Media/Baja) con justificación breve
3. Tiempo estimado para completar

Formato: Sé directo y práctico. Máximo 100 palabras."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un asistente ejecutivo que ayuda a priorizar y responder emails de manera eficiente."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.3
        )

        suggestion = response.choices[0].message.content.strip()
        return suggestion

    except Exception as e:
        print(f"❌ Error al generar sugerencia de IA: {e}")
        return "No se pudo generar sugerencia. Intenta de nuevo más tarde."

def refine_ai_suggestion(sender, subject, body_preview, original_suggestion, user_feedback):
    """Refina una sugerencia de IA basándose en el feedback del usuario"""
    try:
        from openai import OpenAI

        # Limpiar variables de proxy
        import os as os_module
        os_module.environ.pop('http_proxy', None)
        os_module.environ.pop('https_proxy', None)
        os_module.environ.pop('HTTP_PROXY', None)
        os_module.environ.pop('HTTPS_PROXY', None)

        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        prompt = f"""Refina tu sugerencia anterior considerando el feedback del usuario.

CONTEXTO ORIGINAL:
De: {sender}
Asunto: {subject}
Contenido: {body_preview}

TU SUGERENCIA ANTERIOR:
{original_suggestion}

FEEDBACK DEL USUARIO:
{user_feedback}

Genera una nueva sugerencia incorporando los ajustes solicitados. Mantén el mismo formato:
1. Acción recomendada (clara y específica)
2. Prioridad con justificación
3. Tiempo estimado

Máximo 100 palabras."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un asistente ejecutivo que ayuda a priorizar y responder emails. Adaptas tus sugerencias según el feedback del usuario."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.3
        )

        refined_suggestion = response.choices[0].message.content.strip()
        return refined_suggestion

    except Exception as e:
        print(f"❌ Error al refinar sugerencia: {e}")
        return "No se pudo refinar la sugerencia. Intenta de nuevo."

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    """Webhook para recibir callbacks de Telegram y mensajes de texto"""
    try:
        data = request.json
        print(f"📥 Webhook recibido: {json.dumps(data, indent=2)}")

        # Manejar mensajes de texto (para refinamiento de sugerencias)
        if 'message' in data and 'text' in data['message']:
            message = data['message']
            chat_id = message['chat']['id']
            user_feedback = message['text']

            # Buscar emails en estado "waiting_refinement"
            tracking = load_tracking()

            for email_id, email_data in tracking.items():
                if email_data.get('status') == 'waiting_refinement':
                    print(f"🔄 Procesando refinamiento para email {email_id}")

                    # Obtener información necesaria
                    sender = email_data.get('sender', 'Desconocido')
                    subject = email_data.get('subject', 'Sin asunto')
                    body_preview = email_data.get('body_preview', 'Sin contenido')
                    original_suggestion = email_data.get('ai_suggestion', '')
                    last_message_id = email_data.get('last_message_id')

                    # Enviar mensaje de carga
                    if last_message_id:
                        loading_text = "🔄 <b>Refinando sugerencia...</b>"
                        edit_telegram_message(chat_id, last_message_id, loading_text, None)

                    # Refinar sugerencia con IA
                    refined_suggestion = refine_ai_suggestion(sender, subject, body_preview, original_suggestion, user_feedback)

                    # Actualizar tracking
                    tracking[email_id]["status"] = "suggested"
                    tracking[email_id]["ai_suggestion"] = refined_suggestion
                    tracking[email_id]["refinement_history"] = tracking[email_id].get('refinement_history', []) + [
                        {
                            "feedback": user_feedback,
                            "timestamp": datetime.now().isoformat()
                        }
                    ]
                    save_tracking(tracking)

                    # Mostrar sugerencia refinada (con HTML escapado)
                    result_text = f"📋 <b>Detalles del Email</b>\n\n"
                    result_text += f"📧 <b>De:</b> {html.escape(email_data.get('sender_email', 'N/A'))}\n"
                    result_text += f"📝 <b>Asunto:</b> {html.escape(email_data.get('subject', 'N/A'))}\n\n"
                    result_text += f"🤖 <b>Sugerencia Refinada:</b>\n\n"
                    result_text += f"<i>{html.escape(refined_suggestion)}</i>"

                    sender_email = email_data.get('sender_email', 'unknown@example.com')
                    if last_message_id:
                        edit_telegram_message(chat_id, last_message_id, result_text, create_suggestion_menu(email_id, sender_email, subject))

                    # Solo procesar el primer email en waiting_refinement
                    break

            return jsonify({"status": "ok"})

        # Manejar callback queries (clicks en botones)
        if 'callback_query' in data:
            callback_query = data['callback_query']
            callback_data = callback_query['data']
            callback_id = callback_query['id']
            message = callback_query['message']
            chat_id = message['chat']['id']
            message_id = message['message_id']
            message_text = message['text']

            print(f"🔘 Callback recibido: {callback_data}")

            # Parsear callback_data
            parts = callback_data.split('_')
            action = parts[0]
            email_id = parts[1] if len(parts) > 1 else None

            tracking = load_tracking()

            # Inicializar tracking para este email si no existe
            if email_id and email_id not in tracking:
                tracking[email_id] = {
                    "message_text": message_text,
                    "status": "new",
                    "created_at": datetime.now().isoformat()
                }

            # Manejar "remind_setup" - Mostrar menú de tiempo
            if action == "remind" and len(parts) > 2 and parts[1] == "setup":
                # Este es "remind_setup_123"
                email_id = parts[2]
                answer_callback_query(callback_id, "⏰ Selecciona cuándo quieres el recordatorio")

                # Editar mensaje para mostrar opciones de tiempo
                new_text = f"{message_text}\n\n⏰ <b>¿Cuándo quieres que te recuerde?</b>"
                edit_telegram_message(chat_id, message_id, new_text, create_time_menu(email_id))

                tracking[email_id]["status"] = "pending_time_selection"
                save_tracking(tracking)

            # Manejar selección de tiempo de recordatorio (remind_123_15m)
            elif action == "remind" and len(parts) > 2 and parts[1] != "setup":
                time_option = parts[2]
                reminder_time = calculate_reminder_time(time_option)

                # Obtener texto original del mensaje (sin el texto de "¿Cuándo quieres...")
                original_text = message_text.split('\n\n⏰')[0]

                # Guardar recordatorio
                reminders = load_reminders()
                reminders[email_id] = {
                    "message_text": original_text,
                    "remind_at": reminder_time.isoformat(),
                    "chat_id": chat_id,
                    "created_at": datetime.now().isoformat()
                }
                save_reminders(reminders)

                tracking[email_id]["status"] = "reminder_set"
                tracking[email_id]["reminder_at"] = reminder_time.isoformat()
                save_tracking(tracking)

                # Formatear tiempo para mostrar
                time_labels = {
                    "15m": "15 minutos",
                    "1h": "1 hora",
                    "3h": "3 horas",
                    "tomorrow": "mañana a las 9 AM",
                    "2days": "2 días",
                    "week": "1 semana"
                }
                time_label = time_labels.get(time_option, time_option)

                answer_callback_query(callback_id, f"✅ Recordatorio programado")

                # Actualizar mensaje con estado
                new_text = f"{original_text}\n\n🔔 <b>Recordatorio programado</b> en {time_label}"
                edit_telegram_message(chat_id, message_id, new_text, create_main_menu(email_id))

            # Volver al menú principal
            elif action == "back":
                answer_callback_query(callback_id, "Volviendo al menú principal")
                email_data = tracking.get(email_id, {})

                # Restaurar mensaje original con resumen del email
                original_summary = email_data.get('message_text', message_text.split('\n\n')[0])

                # Si hay recordatorio activo, mostrarlo
                if 'reminder_at' in email_data:
                    time_label = "programado"  # Por defecto
                    try:
                        remind_time = datetime.fromisoformat(email_data['reminder_at'])
                        now = datetime.now()
                        diff = remind_time - now
                        minutes = int(diff.total_seconds() // 60)
                        if minutes < 60:
                            time_label = f"{minutes} minutos"
                        else:
                            hours = minutes // 60
                            time_label = f"{hours}h"
                    except:
                        pass

                    original_text = f"📧 {original_summary}\n\n🔔 <b>Recordatorio programado</b> en {time_label}"
                else:
                    original_text = f"📧 {original_summary}"

                edit_telegram_message(chat_id, message_id, original_text, create_main_menu(email_id))

            # Marcar como revisado
            elif action == "done":
                answer_callback_query(callback_id, "✅ Marcado como revisado")
                tracking[email_id]["status"] = "done"
                tracking[email_id]["completed_at"] = datetime.now().isoformat()

                # Marcar email como leído en el servidor IMAP (solo si no se ha marcado antes)
                if not tracking[email_id].get("marked_as_read"):
                    mark_email_as_read(email_id)
                    tracking[email_id]["marked_as_read"] = True

                save_tracking(tracking)

                # Remover recordatorio si existe
                reminders = load_reminders()
                if email_id in reminders:
                    del reminders[email_id]
                    save_reminders(reminders)

                new_text = f"{message_text}\n\n✅ <b>Revisado</b>"
                edit_telegram_message(chat_id, message_id, new_text, None)

            # Ver detalles
            elif action == "details":
                email_data = tracking.get(email_id, {})

                print(f"🔍 DEBUG - Ver detalles para email_id: {email_id}")
                print(f"🔍 DEBUG - Tracking keys: {list(tracking.keys())}")
                print(f"🔍 DEBUG - Email data encontrado: {bool(email_data)}")
                print(f"🔍 DEBUG - Email data: {email_data}")

                # Verificar si el email existe en tracking y tiene la información completa
                if not email_data or not email_data.get('sender_email') or not email_data.get('subject'):
                    print(f"⚠️ Email {email_id} no encontrado en tracking o incompleto")
                    answer_callback_query(callback_id, "❌ Información no disponible")

                    error_message = f"{message_text}\n\n"
                    error_message += "❌ <b>Error:</b> No se pudo cargar la información del email.\n\n"
                    error_message += "<i>Intenta hacer clic en el check de emails nuevamente.</i>"

                    # Mantener el menú simple para permitir descartar
                    edit_telegram_message(chat_id, message_id, error_message, create_main_menu(email_id))

                else:
                    # Tenemos información completa, mostrar detalles
                    answer_callback_query(callback_id, "📋 Mostrando detalles")

                    # Marcar email como leído en el servidor IMAP (primera vez que ve detalles)
                    if not email_data.get("marked_as_read"):
                        mark_email_as_read(email_id)
                        tracking[email_id]["marked_as_read"] = True
                        save_tracking(tracking)

                    # Calcular tiempo transcurrido
                    elapsed = calculate_time_elapsed(email_data.get('created_at', ''))

                    # Construir detalles mejorados con HTML escapado
                    details = f"📋 <b>Detalles del Email</b>\n\n"
                    details += f"📧 <b>De:</b> {html.escape(email_data.get('sender_email', 'N/A'))}\n"
                    details += f"📝 <b>Asunto:</b> {html.escape(email_data.get('subject', 'N/A'))}\n"
                    details += f"📅 <b>Fecha:</b> {html.escape(email_data.get('email_date', 'N/A'))}\n"
                    details += f"⏱️ <b>Hace:</b> {html.escape(elapsed)}\n"
                    details += f"📊 <b>Estado:</b> {html.escape(email_data.get('status', 'nuevo'))}\n"

                    if 'reminder_at' in email_data:
                        details += f"🔔 <b>Recordatorio:</b> {html.escape(email_data['reminder_at'])}\n"

                    # Vista previa del contenido
                    body_preview = email_data.get('body_preview', '')
                    if body_preview:
                        preview = body_preview[:300] + "..." if len(body_preview) > 300 else body_preview
                        details += f"\n📄 <b>Vista previa:</b>\n<i>{html.escape(preview)}</i>"

                    # Usar menú de detalles con acciones
                    sender_email = email_data.get('sender_email', 'unknown@example.com')
                    subject = email_data.get('subject', 'Sin asunto')
                    edit_telegram_message(chat_id, message_id, details, create_details_menu(email_id, sender_email, subject))

            # Compartir email
            elif action == "share":
                answer_callback_query(callback_id, "📤 Preparando mensaje para compartir...")
                email_data = tracking.get(email_id, {})

                # Marcar email como leído en el servidor IMAP (usuario está interactuando con él)
                if not email_data.get("marked_as_read"):
                    mark_email_as_read(email_id)
                    tracking[email_id]["marked_as_read"] = True

                # Crear mensaje formateado para compartir (con HTML escapado)
                share_text = f"📧 <b>Email recibido</b>\n\n"
                share_text += f"<b>De:</b> {html.escape(email_data.get('sender', 'N/A'))}\n"
                share_text += f"<b>Email:</b> {html.escape(email_data.get('sender_email', 'N/A'))}\n"
                share_text += f"<b>Asunto:</b> {html.escape(email_data.get('subject', 'N/A'))}\n"
                share_text += f"<b>Fecha:</b> {html.escape(email_data.get('email_date', 'N/A'))}\n\n"

                body_preview = email_data.get('body_preview', '')
                if body_preview:
                    share_text += f"<b>Contenido:</b>\n{html.escape(body_preview)}\n"

                share_text += f"\n<i>📱 Puedes reenviar este mensaje desde Telegram</i>"

                # Enviar nuevo mensaje que sea fácil de compartir/reenviar
                send_telegram_message(chat_id, share_text)

                # Actualizar mensaje original con estado "compartido" y menú post-acción
                tracking[email_id]["status"] = "shared"
                tracking[email_id]["shared_at"] = datetime.now().isoformat()
                save_tracking(tracking)

                # Mostrar mensaje con menú post-acción (incluye botón Recuérdame)
                elapsed = calculate_time_elapsed(email_data.get('created_at', ''))
                status_text = f"📋 <b>Detalles del Email</b>\n\n"
                status_text += f"📧 <b>De:</b> {html.escape(email_data.get('sender_email', 'N/A'))}\n"
                status_text += f"📝 <b>Asunto:</b> {html.escape(email_data.get('subject', 'N/A'))}\n"
                status_text += f"⏱️ <b>Hace:</b> {html.escape(elapsed)}\n"
                status_text += f"\n✅ <b>Mensaje compartido</b>"

                sender_email = email_data.get('sender_email', 'unknown@example.com')
                subject = email_data.get('subject', 'Sin asunto')
                edit_telegram_message(chat_id, message_id, status_text, create_post_action_menu(email_id, sender_email, subject))

            # Sugerir acción con IA
            elif action == "suggest":
                answer_callback_query(callback_id, "🤖 Analizando email...")
                email_data = tracking.get(email_id, {})

                # Mostrar mensaje de carga
                loading_text = f"{message_text}\n\n⏳ <b>Analizando email con IA...</b>"
                edit_telegram_message(chat_id, message_id, loading_text, None)

                # Generar sugerencia de IA
                sender = email_data.get('sender', 'Desconocido')
                subject = email_data.get('subject', 'Sin asunto')
                body_preview = email_data.get('body_preview', 'Sin contenido')

                suggestion = generate_ai_suggestion(sender, subject, body_preview)

                # Guardar estado
                tracking[email_id]["status"] = "suggested"
                tracking[email_id]["ai_suggestion"] = suggestion
                tracking[email_id]["suggested_at"] = datetime.now().isoformat()
                tracking[email_id]["last_message_id"] = message_id  # Para el refinamiento
                save_tracking(tracking)

                # Mostrar sugerencia con menú especial (incluye botón Refinar)
                result_text = f"📋 <b>Detalles del Email</b>\n\n"
                result_text += f"📧 <b>De:</b> {html.escape(email_data.get('sender_email', 'N/A'))}\n"
                result_text += f"📝 <b>Asunto:</b> {html.escape(email_data.get('subject', 'N/A'))}\n\n"
                result_text += f"🤖 <b>Sugerencia de Acción:</b>\n\n"
                result_text += f"<i>{html.escape(suggestion)}</i>"

                sender_email = email_data.get('sender_email', 'unknown@example.com')
                edit_telegram_message(chat_id, message_id, result_text, create_suggestion_menu(email_id, sender_email, subject))

            # Refinar sugerencia con feedback del usuario
            elif action == "refine":
                answer_callback_query(callback_id, "💬 Escribe tus ajustes")
                email_data = tracking.get(email_id, {})

                # Cambiar estado a esperando refinamiento
                tracking[email_id]["status"] = "waiting_refinement"
                tracking[email_id]["last_message_id"] = message_id
                save_tracking(tracking)

                # Mostrar instrucciones
                instruction_text = f"{message_text}\n\n💬 <b>Responde a este mensaje</b> con tus ajustes.\n\n"
                instruction_text += f"<i>Ejemplo: \"Considera mejor 6 semanas y añade que estamos dispuestos a negociar\"</i>"

                edit_telegram_message(chat_id, message_id, instruction_text, None)

            return jsonify({"status": "ok"})

        return jsonify({"status": "ok"})

    except Exception as e:
        print(f"❌ Error en webhook: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/check-reminders')
def check_reminders():
    """Endpoint para verificar y enviar recordatorios pendientes"""
    try:
        reminders = load_reminders()
        now = datetime.now()
        sent_count = 0

        TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

        for email_id, reminder in list(reminders.items()):
            remind_at = datetime.fromisoformat(reminder['remind_at'])

            if now >= remind_at:
                # Enviar recordatorio
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                data = {
                    "chat_id": reminder['chat_id'],
                    "text": f"🔔 <b>Recordatorio</b>\n\n{reminder['message_text']}",
                    "parse_mode": "HTML",
                    "reply_markup": json.dumps(create_main_menu(email_id))
                }

                response = requests.post(url, data=data, timeout=10)
                if response.status_code == 200:
                    sent_count += 1
                    # Remover recordatorio enviado
                    del reminders[email_id]

        save_reminders(reminders)

        return jsonify({
            "status": "success",
            "reminders_sent": sent_count,
            "pending_reminders": len(reminders)
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/tracking-status')
def tracking_status():
    """Endpoint para ver el estado del tracking"""
    try:
        tracking = load_tracking()
        reminders = load_reminders()

        print(f"📊 Tracking status requested")
        print(f"📊 Total emails tracked: {len(tracking)}")
        print(f"📊 Tracking keys: {list(tracking.keys())}")

        return jsonify({
            "status": "success",
            "total_tracked": len(tracking),
            "pending_reminders": len(reminders),
            "tracking_keys": list(tracking.keys()),
            "tracking": tracking,
            "reminders": reminders
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/debug-tracking/<email_id>')
def debug_tracking(email_id):
    """Endpoint de debug para ver un email específico"""
    try:
        tracking = load_tracking()
        email_data = tracking.get(email_id, None)

        return jsonify({
            "status": "success",
            "email_id": email_id,
            "found": email_data is not None,
            "data": email_data,
            "all_keys": list(tracking.keys())
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
