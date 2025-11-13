# 🔔 Configuración del Sistema de Tracking con Botones

## ✨ Características Implementadas

- ✅ **Botones inline en mensajes de Telegram**
- ✅ **Menú de recordatorios** con opciones de tiempo
- ✅ **Sistema de tracking** con almacenamiento en JSON
- ✅ **Recordatorios automáticos** programables
- ✅ **Estados de seguimiento**: Nuevo, Pendiente, Urgente, Revisado

## 🎯 ¿Cómo Funciona?

### 1. Cuando recibes un email

El mensaje de Telegram ahora incluye 4 botones:

```
📧 Juan de Ventas pregunta por cotización

[⏰ Marcar Pendiente] [✅ Ya Revisado]
[🔥 Urgente]          [📋 Ver Detalles]
```

### 2. Al hacer clic en "⏰ Marcar Pendiente"

Se despliega un menú con opciones de tiempo:

```
⏰ ¿Cuándo quieres que te recuerde?

[⏰ 15 minutos] [⏰ 1 hora]
[⏰ 3 horas]    [🌅 Mañana 9 AM]
[📅 En 2 días] [📅 Esta semana]
[⬅️ Volver]
```

### 3. Seleccionas el tiempo

El sistema:
- Guarda el recordatorio
- Actualiza el mensaje mostrando cuándo te recordará
- Te envía una notificación en el momento programado

## 🚀 Configuración del Webhook en Telegram

### Paso 1: Desplegar tu aplicación en Render

Asegúrate de que tu app esté corriendo en Render y obtén tu URL:
```
https://tu-app.onrender.com
```

### Paso 2: Configurar el Webhook de Telegram

Abre tu navegador y visita esta URL (reemplaza con tus datos):

```
https://api.telegram.org/bot<TU_BOT_TOKEN>/setWebhook?url=https://tu-app.onrender.com/telegram-webhook
```

**Ejemplo:**
```
https://api.telegram.org/bot123456789:ABCdefGHIjklMNOpqrsTUVwxyz/setWebhook?url=https://email-notifier.onrender.com/telegram-webhook
```

Deberías ver una respuesta como esta:
```json
{
  "ok": true,
  "result": true,
  "description": "Webhook was set"
}
```

### Paso 3: Verificar el Webhook

Para verificar que el webhook está configurado correctamente:

```
https://api.telegram.org/bot<TU_BOT_TOKEN>/getWebhookInfo
```

Respuesta esperada:
```json
{
  "ok": true,
  "result": {
    "url": "https://tu-app.onrender.com/telegram-webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

## 📋 Nuevos Endpoints

### 1. `/telegram-webhook` (POST)
Recibe los callbacks cuando haces clic en botones de Telegram.

**No necesitas llamar este endpoint manualmente**, Telegram lo hace automáticamente.

### 2. `/check-reminders` (GET)
Verifica y envía recordatorios pendientes.

**Configurar en cron job** para que se ejecute cada 5-10 minutos:
```
URL: https://tu-app.onrender.com/check-reminders
Intervalo: */5 * * * * (cada 5 minutos)
```

### 3. `/tracking-status` (GET)
Ver el estado actual del tracking y recordatorios.

```bash
curl https://tu-app.onrender.com/tracking-status
```

Respuesta:
```json
{
  "status": "success",
  "total_tracked": 5,
  "pending_reminders": 2,
  "tracking": { ... },
  "reminders": { ... }
}
```

## 🧪 Probar el Sistema

### 1. Prueba Local

```bash
# Iniciar la aplicación
python app.py

# En otra terminal, enviar un callback de prueba
curl -X POST http://localhost:10000/telegram-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "callback_query": {
      "id": "test123",
      "data": "pending_456",
      "message": {
        "chat": {"id": 123456789},
        "message_id": 1,
        "text": "Test email"
      }
    }
  }'
```

### 2. Prueba en Producción

1. Envíate un email de prueba
2. Espera la notificación en Telegram
3. Haz clic en "⏰ Marcar Pendiente"
4. Selecciona "⏰ 15 minutos"
5. Espera 15 minutos
6. Deberías recibir el recordatorio automáticamente

## 🎮 Flujo de Uso

### Ejemplo 1: Marcar como Pendiente con Recordatorio

```
1. Recibes email → Notificación en Telegram
2. Click en [⏰ Marcar Pendiente]
3. Se despliega menú de tiempo
4. Click en [⏰ 1 hora]
5. Mensaje actualizado: "⏰ Pendiente - Recordatorio en 1 hora"
6. Después de 1 hora → 🔔 Recordatorio automático
```

### Ejemplo 2: Marcar como Urgente

```
1. Recibes email → Notificación en Telegram
2. Click en [🔥 Urgente]
3. Mensaje actualizado: "🔥 URGENTE"
4. Queda marcado en el sistema de tracking
```

### Ejemplo 3: Marcar como Revisado

```
1. Ya respondiste el email
2. Click en [✅ Ya Revisado]
3. Mensaje actualizado: "✅ Revisado"
4. Se elimina cualquier recordatorio pendiente
5. Los botones desaparecen
```

## 📊 Estructura de Datos

### Archivo: `/tmp/email_tracking.json`
```json
{
  "123": {
    "message_text": "Juan de Ventas pregunta por cotización",
    "status": "pending",
    "created_at": "2025-11-13T10:30:00",
    "reminder_at": "2025-11-13T11:30:00"
  },
  "124": {
    "message_text": "María de Soporte reporta bug",
    "status": "urgent",
    "created_at": "2025-11-13T10:35:00",
    "marked_urgent_at": "2025-11-13T10:36:00"
  }
}
```

### Archivo: `/tmp/email_reminders.json`
```json
{
  "123": {
    "message_text": "Juan de Ventas pregunta por cotización",
    "remind_at": "2025-11-13T11:30:00",
    "chat_id": 123456789,
    "created_at": "2025-11-13T10:30:00"
  }
}
```

## 🔧 Configuración de Cron Jobs

### En Render (Recomendado)

1. Ve a tu dashboard de Render
2. Crea un nuevo **Cron Job**:
   - **Name**: check-reminders
   - **Command**: `curl https://tu-app.onrender.com/check-reminders`
   - **Schedule**: `*/5 * * * *` (cada 5 minutos)

### En cron-job.org

1. Crea una cuenta en https://cron-job.org
2. Crear nuevo cron job:
   - **URL**: `https://tu-app.onrender.com/check-reminders`
   - **Intervalo**: Cada 5 minutos
3. Guardar

## 🐛 Troubleshooting

### Los botones no responden

**Verificar webhook:**
```
https://api.telegram.org/bot<TU_TOKEN>/getWebhookInfo
```

Si el webhook no está configurado o la URL es incorrecta:
```
https://api.telegram.org/bot<TU_TOKEN>/setWebhook?url=https://tu-app.onrender.com/telegram-webhook
```

### Los recordatorios no se envían

1. Verifica que el cron job esté activo
2. Visita manualmente: `https://tu-app.onrender.com/check-reminders`
3. Revisa los logs en Render
4. Verifica que el archivo `/tmp/email_reminders.json` tenga datos

### Ver logs en tiempo real (Render)

En el dashboard de Render, ve a tu servicio → **Logs**

## 💡 Próximas Mejoras

- [ ] Base de datos persistente (Supabase/PostgreSQL)
- [ ] Notificaciones de resumen diario
- [ ] Filtros por remitente
- [ ] Integración con calendario
- [ ] Comandos de Telegram (/list, /pending, /urgent)

## 🔒 Seguridad

- Los archivos JSON se guardan en `/tmp/` (temporal)
- En Render, estos archivos se borran cuando el servicio se reinicia
- Para producción, usa una base de datos persistente (ver próximas mejoras)

## 📞 Soporte

Si tienes problemas:
1. Revisa los logs en Render
2. Verifica que el webhook esté configurado
3. Prueba manualmente los endpoints
4. Verifica que las variables de entorno estén correctas
