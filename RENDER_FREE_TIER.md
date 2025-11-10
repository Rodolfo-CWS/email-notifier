# Configuración para Render Free Tier

## ⚠️ Importante: Limitaciones del Plan Gratuito

En Render free tier, los servicios web:
- Se **duermen** después de **15 minutos** de inactividad
- Tardan **30-50 segundos** en despertar cuando reciben un request
- Esto puede causar timeouts (502 Bad Gateway) en el primer request

## ✅ Solución Implementada

El código está optimizado para manejar estas limitaciones:

### 1. Procesamiento en Background
El endpoint `/check` ahora:
- ✅ Responde **inmediatamente** (evita timeouts)
- ✅ Procesa emails en un **thread separado**
- ✅ Previene ejecuciones concurrentes

### 2. Configuración de Cron Jobs

Necesitas **DOS cron jobs** en [cron-job.org](https://cron-job.org):

#### Cron Job #1: Keep-Alive (Mantener despierto)
```
Nombre: Email Notifier - Keep Alive
URL: https://email-notifier-eteh.onrender.com/health
Frecuencia: Cada 14 minutos
Timeout: 30 segundos
```
Este mantiene el servicio despierto para que responda rápido.

#### Cron Job #2: Check Emails (Revisar emails)
```
Nombre: Email Notifier - Check Emails
URL: https://email-notifier-eteh.onrender.com/check
Frecuencia: Cada 5 minutos (o según prefieras)
Timeout: 60 segundos
```
Este ejecuta la revisión de emails.

## 🔍 Endpoints Disponibles

| Endpoint | Descripción | Respuesta |
|----------|-------------|-----------|
| `/` | Home | Info básica del servicio |
| `/health` | Health check | Estado + si hay check en progreso |
| `/status` | Estado detallado | Info completa del servicio |
| `/check` | Revisar emails | Inicia revisión en background |

## 📊 Verificar que funciona

### 1. Ver logs en Render
Busca estos mensajes:
```
🚀 Iniciando revisión de emails en background...
[timestamp] Conectando a mail.cwscompany.com...
✅ Conectado exitosamente
📬 X email(s) nuevo(s)
✅ Revisión completada
```

### 2. Verificar status
```bash
curl https://email-notifier-eteh.onrender.com/status
```

Respuesta:
```json
{
  "status": "running",
  "service": "Email Notifier",
  "email": "tu@email.com",
  "check_in_progress": false,
  "render_free_tier": "Service sleeps after 15min of inactivity"
}
```

### 3. Llamar manualmente al check
```bash
curl https://email-notifier-eteh.onrender.com/check
```

Respuesta inmediata:
```json
{
  "status": "success",
  "message": "Email check started in background"
}
```

## 🐛 Troubleshooting

### Problema: Sigo viendo 502 Bad Gateway
**Causa**: El servicio está dormido y tarda en despertar
**Solución**:
1. Verifica que el cron job de keep-alive esté corriendo cada 14 minutos
2. Aumenta el timeout del cron job a 60 segundos

### Problema: No recibo notificaciones
**Causa**: Múltiples posibles causas
**Solución**:
1. Revisa los logs en Render cuando se ejecuta el cron
2. Verifica que los emails sean de menos de 7 días
3. Llama manualmente a `/check` y revisa logs

### Problema: "Email check already in progress"
**Causa**: Ya hay una revisión ejecutándose
**Solución**: Esto es normal, el sistema previene ejecuciones concurrentes

## 💡 Tips

1. **No uses frecuencia menor a 5 minutos** para el check de emails (puede causar rate limiting)
2. **El keep-alive debe ser cada 14 minutos** (no menos) para mantener el servicio despierto
3. **Revisa los logs** regularmente para ver qué emails se están filtrando
4. **La primera llamada después de dormir** puede tardar ~50 segundos, esto es normal

## 🚀 Alternativa: Upgrade a Paid Plan

Si necesitas:
- ✅ Respuesta inmediata sin sleep
- ✅ Sin timeouts
- ✅ Mayor confiabilidad

Considera el plan Starter de Render ($7/mes) que no tiene estas limitaciones.
