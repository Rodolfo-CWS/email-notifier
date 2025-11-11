# 📧 Email Notifier - Telegram

Recibe notificaciones automáticas en Telegram con resúmenes de tus emails usando GPT-4o-mini.

## 🎯 Características

- ✅ Lee emails vía IMAP
- ✅ Resume emails con GPT-4o-mini
- ✅ Notificaciones automáticas en Telegram
- ✅ Botón en Telegram para abrir el email directamente
- ✅ Tracking de emails procesados
- ✅ Deploy gratuito en Render

## 📋 Requisitos

1. Bot de Telegram + Chat ID
2. API Key de OpenAI
3. Cuenta de correo con IMAP habilitado
4. Cuenta gratuita en Render

## 🚀 Instalación Local (Pruebas)

### 1. Clonar repositorio
```bash
git clone <tu-repo>
cd email-notifier
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
Copia `.env.example` a `.env` y completa:

```bash
cp .env.example .env
```

Edita `.env` con tus credenciales:
```
IMAP_SERVER=mail.cwscompany.com
IMAP_PORT=143
EMAIL_USER=tu@email.com
EMAIL_PASS=tu_contraseña

TELEGRAM_BOT_TOKEN=123456789:ABCdef...
TELEGRAM_CHAT_ID=987654321

OPENAI_API_KEY=sk-proj-abc123...

WEBMAIL_URL=https://mail.cwscompany.com
```

**Nota sobre WEBMAIL_URL**: Esta URL se usa para el botón "Abrir Email" en los mensajes de Telegram. Si tu servidor de correo tiene una interfaz webmail, puedes configurar esta URL para que el botón redirija directamente al email.

### 4. Probar localmente
```bash
# Solo revisar emails
python email_notifier.py

# O iniciar servidor web
python app.py
```

Luego visita: http://localhost:10000/check

## 🌐 Deploy en Render

### 1. Crear Web Service en Render

1. Ve a: https://dashboard.render.com/
2. Click en "New +" → "Web Service"
3. Conecta tu repositorio de GitHub
4. Configura:
   - **Name**: email-notifier
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app.py`
   - **Plan**: Free

### 2. Agregar Variables de Entorno

En Render, ve a "Environment" y agrega:

```
IMAP_SERVER = mail.cwscompany.com
IMAP_PORT = 143
EMAIL_USER = tu@email.com
EMAIL_PASS = tu_contraseña
TELEGRAM_BOT_TOKEN = 123456789:ABCdef...
TELEGRAM_CHAT_ID = 987654321
OPENAI_API_KEY = sk-proj-abc123...
WEBMAIL_URL = https://mail.cwscompany.com
```

### 3. Deploy
Click en "Create Web Service" y espera el deploy.

## ⏰ Configurar Cron Job (Automatización)

### Opción A: Render Cron Jobs (Recomendado)

1. En Render, crea un nuevo "Cron Job"
2. Configura:
   - **Name**: email-checker
   - **Command**: `python email_notifier.py`
   - **Schedule**: `*/10 * * * *` (cada 10 minutos)
3. Usa las mismas variables de entorno

### Opción B: Cron-job.org (Gratis)

1. Ve a: https://cron-job.org
2. Crea cuenta
3. Crear nuevo cron job:
   - **URL**: `https://tu-app.onrender.com/check`
   - **Intervalo**: Cada 10 minutos
4. Guarda

## 🧪 Probar el Sistema

### 1. Envíate un email de prueba

Envía un email a tu cuenta configurada.

### 2. Ejecutar manualmente

**Localmente:**
```bash
python email_notifier.py
```

**En Render:**
Visita: `https://tu-app.onrender.com/check`

### 3. Verificar Telegram

Deberías recibir algo como:
```
📧 Juan de Ventas pregunta por cotización de proyecto
[📬 Abrir Email] <- Botón clickeable
```

El botón te llevará directamente al email en tu webmail.

## 📁 Estructura del Proyecto

```
email-notifier/
├── app.py                 # Servidor Flask
├── email_notifier.py      # Lógica principal
├── requirements.txt       # Dependencias
├── .env.example          # Ejemplo de configuración
└── README.md             # Este archivo
```

## 🔧 Endpoints

- `GET /` - Estado del servicio
- `GET /check` - Ejecuta revisión de emails
- `GET /health` - Health check

## 💰 Costos Estimados

- Render Free: $0
- Telegram: $0
- OpenAI (GPT-4o-mini): ~$2-3/mes

## 🐛 Troubleshooting

### Error: "Authentication failed"
- Verifica usuario y contraseña IMAP
- Algunos servidores requieren "contraseña de aplicación"

### Error: "Connection refused"
- Verifica IMAP_SERVER y IMAP_PORT
- Prueba puerto 993 si 143 no funciona

### No llegan notificaciones
- Verifica TELEGRAM_BOT_TOKEN
- Verifica TELEGRAM_CHAT_ID
- Prueba enviar mensaje manual al bot

### Render se duerme
- Configura cron job externo cada 10-14 min
- O usa Render Cron Jobs

## 🔒 Seguridad

⚠️ **NUNCA** subas tu archivo `.env` a GitHub
⚠️ Mantén tus API keys seguras
⚠️ Usa variables de entorno en Render

## 📝 Próximos Pasos (con Claude Code)

- [ ] Agregar base de datos (Supabase)
- [ ] Tracking de respuestas pendientes
- [ ] Filtros personalizados
- [ ] Múltiples cuentas de correo
- [ ] Dashboard web

## 🤝 Contribuir

Este es un proyecto personal, pero pull requests son bienvenidos.

## 📄 Licencia

MIT
