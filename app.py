from flask import Flask, jsonify
import os
import sys
from email_notifier import check_emails

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
        print("=" * 50, flush=True)
        print(f"[/check] Iniciando revisión de emails...", flush=True)
        sys.stdout.flush()

        check_emails()

        print(f"[/check] Revisión completada", flush=True)
        sys.stdout.flush()
        print("=" * 50, flush=True)

        return jsonify({"status": "success", "message": "Emails checked"})
    except Exception as e:
        error_msg = str(e)
        print(f"[/check] ERROR: {error_msg}", flush=True)
        sys.stdout.flush()
        return jsonify({"status": "error", "message": error_msg}), 500

@app.route('/health')
def health():
    """Health check para mantener el servicio activo"""
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
