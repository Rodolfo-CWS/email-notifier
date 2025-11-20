from flask import Flask, jsonify, request
import os
import requests
from email_notifier import check_emails, handle_callback_query, handle_summary_callback

app = Flask(__name__)

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

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook para recibir actualizaciones de Telegram (callbacks de botones)"""
    try:
        update = request.get_json()

        if not update:
            return jsonify({"status": "error", "message": "No data received"}), 400

        # Manejar callback_query (cuando se presiona un botón)
        if 'callback_query' in update:
            callback_query = update['callback_query']
            callback_data = callback_query.get('data', '')

            # Determinar qué tipo de callback es
            if callback_data.startswith('details_'):
                result = handle_callback_query(callback_query)
            elif callback_data.startswith('summary_'):
                result = handle_summary_callback(callback_query)
            else:
                result = False

            if result:
                return jsonify({"status": "success", "action": "callback_handled"})
            else:
                return jsonify({"status": "error", "message": "Failed to handle callback"}), 400

        # Si no es un callback, simplemente confirmar recepción
        return jsonify({"status": "ok"})

    except Exception as e:
        print(f"❌ Error en webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/setup-webhook')
def setup_webhook():
    """Configura el webhook de Telegram para recibir callbacks de botones"""
    try:
        TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

        if not TELEGRAM_BOT_TOKEN:
            return jsonify({
                "status": "error",
                "message": "TELEGRAM_BOT_TOKEN no está configurado"
            }), 400

        # Obtener la URL del servicio (debe ser HTTPS)
        # En Render, esto sería algo como https://tu-app.onrender.com
        service_url = os.getenv('RENDER_EXTERNAL_URL', os.getenv('SERVICE_URL', ''))

        if not service_url:
            return jsonify({
                "status": "error",
                "message": "SERVICE_URL o RENDER_EXTERNAL_URL no está configurado. Configura esta variable con la URL de tu servicio (ej: https://tu-app.onrender.com)"
            }), 400

        webhook_url = f"{service_url}/webhook"

        # Configurar el webhook en Telegram
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
        response = requests.post(telegram_url, data={
            "url": webhook_url,
            "allowed_updates": '["callback_query"]'  # Solo recibir callbacks de botones
        }, timeout=10)

        result = response.json()

        if response.status_code == 200 and result.get('ok'):
            return jsonify({
                "status": "success",
                "message": "Webhook configurado correctamente",
                "webhook_url": webhook_url,
                "response": result
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Error al configurar webhook",
                "response": result
            }), 400

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/webhook-info')
def webhook_info():
    """Muestra información del webhook configurado actualmente"""
    try:
        TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

        if not TELEGRAM_BOT_TOKEN:
            return jsonify({
                "status": "error",
                "message": "TELEGRAM_BOT_TOKEN no está configurado"
            }), 400

        # Obtener info del webhook
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
        response = requests.get(telegram_url, timeout=10)
        result = response.json()

        if response.status_code == 200 and result.get('ok'):
            webhook_info = result.get('result', {})
            return jsonify({
                "status": "success",
                "webhook": {
                    "url": webhook_info.get('url', 'No configurado'),
                    "has_custom_certificate": webhook_info.get('has_custom_certificate', False),
                    "pending_update_count": webhook_info.get('pending_update_count', 0),
                    "last_error_date": webhook_info.get('last_error_date'),
                    "last_error_message": webhook_info.get('last_error_message'),
                    "allowed_updates": webhook_info.get('allowed_updates', [])
                }
            })
        else:
            return jsonify({
                "status": "error",
                "response": result
            }), 400

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/delete-webhook')
def delete_webhook():
    """Elimina el webhook de Telegram (útil para debugging)"""
    try:
        TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

        if not TELEGRAM_BOT_TOKEN:
            return jsonify({
                "status": "error",
                "message": "TELEGRAM_BOT_TOKEN no está configurado"
            }), 400

        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook"
        response = requests.post(telegram_url, timeout=10)
        result = response.json()

        if response.status_code == 200 and result.get('ok'):
            return jsonify({
                "status": "success",
                "message": "Webhook eliminado correctamente"
            })
        else:
            return jsonify({
                "status": "error",
                "response": result
            }), 400

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
