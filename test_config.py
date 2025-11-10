#!/usr/bin/env python3
"""
Script de prueba para verificar que todas las configuraciones funcionan
Ejecuta esto ANTES de hacer deploy a Render
"""

import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def check_env_var(var_name):
    """Verifica que una variable de entorno esté configurada"""
    value = os.getenv(var_name)
    if not value:
        print(f"❌ {var_name}: NO configurada")
        return False
    else:
        # Mostrar solo primeros caracteres por seguridad
        display_value = value[:10] + "..." if len(value) > 10 else value
        print(f"✅ {var_name}: {display_value}")
        return True

def test_imap():
    """Prueba conexión IMAP"""
    import imaplib
    
    print("\n📧 Probando conexión IMAP...")
    try:
        server = os.getenv('IMAP_SERVER')
        port = int(os.getenv('IMAP_PORT', '143'))
        user = os.getenv('EMAIL_USER')
        password = os.getenv('EMAIL_PASS')
        
        mail = imaplib.IMAP4(server, port)
        mail.login(user, password)
        mail.select('INBOX')
        
        # Contar emails
        status, messages = mail.search(None, 'ALL')
        total_emails = len(messages[0].split())
        
        mail.logout()
        
        print(f"✅ Conexión IMAP exitosa")
        print(f"📬 Total de emails en bandeja: {total_emails}")
        return True
        
    except Exception as e:
        print(f"❌ Error IMAP: {e}")
        return False

def test_telegram():
    """Prueba envío de mensaje a Telegram"""
    import requests
    
    print("\n💬 Probando Telegram Bot...")
    try:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": "🧪 Prueba de Email Notifier - ¡Configuración exitosa!"
        }
        
        response = requests.post(url, data=data)
        
        if response.status_code == 200:
            print("✅ Mensaje de prueba enviado a Telegram")
            print("   Verifica tu app de Telegram")
            return True
        else:
            print(f"❌ Error al enviar mensaje: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error Telegram: {e}")
        return False

def test_openai():
    """Prueba API de OpenAI"""
    from openai import OpenAI
    
    print("\n🤖 Probando OpenAI API...")
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Di solo 'OK' si funcionas correctamente"}
            ],
            max_tokens=10
        )
        
        result = response.choices[0].message.content
        print(f"✅ OpenAI API funcional")
        print(f"   Respuesta: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Error OpenAI: {e}")
        return False

def main():
    print("="*50)
    print("🧪 EMAIL NOTIFIER - TEST DE CONFIGURACIÓN")
    print("="*50)
    
    # Verificar variables de entorno
    print("\n📋 Verificando variables de entorno...\n")
    
    required_vars = [
        'IMAP_SERVER',
        'IMAP_PORT',
        'EMAIL_USER',
        'EMAIL_PASS',
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID',
        'OPENAI_API_KEY'
    ]
    
    all_vars_ok = all(check_env_var(var) for var in required_vars)
    
    if not all_vars_ok:
        print("\n❌ Faltan variables de entorno. Configura tu archivo .env")
        print("   Copia .env.example a .env y completa los valores")
        sys.exit(1)
    
    print("\n" + "="*50)
    print("🔧 Probando servicios...")
    print("="*50)
    
    # Probar cada servicio
    results = {
        'IMAP': test_imap(),
        'Telegram': test_telegram(),
        'OpenAI': test_openai()
    }
    
    # Resumen
    print("\n" + "="*50)
    print("📊 RESUMEN DE PRUEBAS")
    print("="*50 + "\n")
    
    for service, status in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {service}")
    
    all_ok = all(results.values())
    
    if all_ok:
        print("\n🎉 ¡Todo configurado correctamente!")
        print("   Puedes proceder con el deploy a Render")
        print("\nPróximos pasos:")
        print("1. Sube tu código a GitHub")
        print("2. Crea Web Service en Render")
        print("3. Configura variables de entorno en Render")
        print("4. Configura Cron Job")
    else:
        print("\n⚠️  Hay errores en la configuración")
        print("   Corrige los problemas antes de hacer deploy")
        sys.exit(1)

if __name__ == "__main__":
    # Instalar dotenv si no está
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("Instalando python-dotenv...")
        os.system("pip install python-dotenv")
        from dotenv import load_dotenv
    
    main()
