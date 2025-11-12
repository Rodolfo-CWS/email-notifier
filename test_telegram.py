#!/usr/bin/env python3
"""
Script para probar la configuración de Telegram
Ejecuta este script para verificar que tu bot está configurado correctamente
"""
import os
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def test_telegram_config():
    """Prueba la configuración de Telegram paso a paso"""

    print("=" * 60)
    print("🧪 TEST DE CONFIGURACIÓN DE TELEGRAM")
    print("=" * 60)

    # Paso 1: Verificar variables de entorno
    print("\n[1/4] Verificando variables de entorno...")

    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN no está configurado")
        print("   Configura tu token en el archivo .env")
        return False

    if not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM_CHAT_ID no está configurado")
        print("   Configura tu chat ID en el archivo .env")
        return False

    print(f"✅ TELEGRAM_BOT_TOKEN: {TELEGRAM_BOT_TOKEN[:20]}...")
    print(f"✅ TELEGRAM_CHAT_ID: {TELEGRAM_CHAT_ID}")

    # Paso 2: Verificar que el bot existe
    print("\n[2/4] Verificando bot de Telegram...")
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        result = response.json()

        if not result.get('ok'):
            print(f"❌ Token inválido o bot no encontrado")
            print(f"   Respuesta: {result}")
            return False

        bot_info = result.get('result', {})
        print(f"✅ Bot encontrado: @{bot_info.get('username')}")
        print(f"   Nombre: {bot_info.get('first_name')}")
        print(f"   ID: {bot_info.get('id')}")

    except Exception as e:
        print(f"❌ Error al verificar bot: {e}")
        return False

    # Paso 3: Verificar que el chat existe
    print("\n[3/4] Verificando chat ID...")
    try:
        # Intentar obtener información del chat
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChat"
        data = {"chat_id": TELEGRAM_CHAT_ID}
        response = requests.post(url, data=data, timeout=10)
        result = response.json()

        if not result.get('ok'):
            print(f"⚠️  No se pudo verificar el chat")
            print(f"   Esto puede ser normal si es un chat privado")
            print(f"   Código de error: {result.get('error_code')}")
            print(f"   Descripción: {result.get('description')}")
            print(f"\n   Continuando con prueba de envío...")
        else:
            chat_info = result.get('result', {})
            print(f"✅ Chat encontrado:")
            print(f"   Tipo: {chat_info.get('type')}")
            if chat_info.get('title'):
                print(f"   Título: {chat_info.get('title')}")
            if chat_info.get('username'):
                print(f"   Username: @{chat_info.get('username')}")

    except Exception as e:
        print(f"⚠️  Error al verificar chat: {e}")
        print(f"   Continuando con prueba de envío...")

    # Paso 4: Enviar mensaje de prueba
    print("\n[4/4] Enviando mensaje de prueba...")
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": "🧪 Test de Email Notifier\n\n✅ ¡Tu configuración está funcionando correctamente!",
            "parse_mode": "HTML"
        }

        response = requests.post(url, data=data, timeout=10)
        result = response.json()

        if response.status_code == 200 and result.get('ok'):
            print("✅ ¡Mensaje enviado exitosamente!")
            print(f"   ID del mensaje: {result.get('result', {}).get('message_id')}")
            print("\n" + "=" * 60)
            print("✅ TODAS LAS PRUEBAS PASARON")
            print("=" * 60)
            print("\n💡 Tu bot de Telegram está configurado correctamente.")
            print("   Ahora deberías recibir notificaciones cuando lleguen emails.")
            return True
        else:
            print(f"❌ Error al enviar mensaje:")
            print(f"   Status Code: {response.status_code}")
            print(f"   Código de error: {result.get('error_code')}")
            print(f"   Descripción: {result.get('description')}")

            # Ayuda común para errores
            error_code = result.get('error_code')
            if error_code == 400:
                print("\n💡 Posibles causas:")
                print("   - El CHAT_ID es incorrecto")
                print("   - El bot no ha sido iniciado (/start)")
                print("   - El formato del CHAT_ID es inválido")
            elif error_code == 401:
                print("\n💡 Causa:")
                print("   - El TELEGRAM_BOT_TOKEN es inválido")
            elif error_code == 403:
                print("\n💡 Posibles causas:")
                print("   - El bot fue bloqueado por el usuario")
                print("   - El bot no tiene permisos en el grupo/canal")

            return False

    except requests.exceptions.Timeout:
        print("❌ Timeout al conectar con Telegram")
        print("   Verifica tu conexión a internet")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

if __name__ == "__main__":
    success = test_telegram_config()

    if not success:
        print("\n" + "=" * 60)
        print("❌ ALGUNAS PRUEBAS FALLARON")
        print("=" * 60)
        print("\n📝 Pasos para solucionar:")
        print("\n1. Verifica que tu bot existe:")
        print("   - Habla con @BotFather en Telegram")
        print("   - Usa el comando /mybots para ver tus bots")
        print("\n2. Obtén tu CHAT_ID:")
        print("   - Envía un mensaje a tu bot")
        print("   - Visita: https://api.telegram.org/bot<TU_TOKEN>/getUpdates")
        print("   - Busca el campo 'chat' -> 'id'")
        print("\n3. Verifica tu archivo .env:")
        print("   - TELEGRAM_BOT_TOKEN debe incluir el número y el texto completo")
        print("   - TELEGRAM_CHAT_ID puede ser positivo o negativo")
        print("\n4. Si es un grupo:")
        print("   - Asegúrate de agregar el bot al grupo")
        print("   - El bot necesita permisos para enviar mensajes")
        exit(1)

    exit(0)
