from flask import Flask, jsonify
import os
import threading
from email_notifier import check_emails

app = Flask(__name__)

# Variable para trackear si hay un check en progreso
check_in_progress = False

@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "service": "Email Notifier",
        "email": os.getenv('EMAIL_USER', 'Not configured')
    })

@app.route('/check')
def check():
    """Endpoint para que el cron job ejecute la revisión de emails

    Responde inmediatamente y procesa emails en background para evitar timeouts.
    Esto es especialmente importante en Render free tier donde el servicio
    puede tardar en despertar.
    """
    global check_in_progress

    if check_in_progress:
        return jsonify({
            "status": "already_running",
            "message": "Email check already in progress"
        })

    # Iniciar el check en un thread separado
    def run_check():
        global check_in_progress
        try:
            check_in_progress = True
            print("\n🚀 Iniciando revisión de emails en background...")
            check_emails()
            print("✅ Revisión completada\n")
        except Exception as e:
            print(f"❌ Error en revisión: {e}")
        finally:
            check_in_progress = False

    thread = threading.Thread(target=run_check, daemon=True)
    thread.start()

    return jsonify({
        "status": "success",
        "message": "Email check started in background"
    })

@app.route('/health')
def health():
    """Health check para mantener el servicio activo"""
    return jsonify({
        "status": "healthy",
        "check_in_progress": check_in_progress
    })

@app.route('/status')
def status():
    """Endpoint para verificar el estado del servicio"""
    return jsonify({
        "status": "running",
        "service": "Email Notifier",
        "email": os.getenv('EMAIL_USER', 'Not configured'),
        "check_in_progress": check_in_progress,
        "render_free_tier": "Service sleeps after 15min of inactivity"
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
