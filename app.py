from flask import Flask, jsonify
import os
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
        check_emails()
        return jsonify({"status": "success", "message": "Emails checked"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health')
def health():
    """Health check para mantener el servicio activo"""
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
