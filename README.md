# DMCripto Bot

Bot de Telegram que recibe señales de trading desde **TradingView** (vía webhook)
y las publica automáticamente en un chat, grupo o canal de Telegram. También
responde a comandos básicos (`/start`, `/ayuda`, `/faq`) y modera enlaces no
autorizados en el chat.

## Cómo funciona

1. **TradingView → Bot**: creas una alerta en TradingView cuyo webhook apunta a
   `https://TU_DOMINIO/webhook`. El bot reenvía el mensaje de la alerta a
   Telegram con formato `🚨 ALERTA DMCRIPTO`.
2. **Telegram → Bot**: Telegram envía las actualizaciones del bot (mensajes,
   comandos) a `https://TU_DOMINIO/tg_webhook`.

## Variables de entorno

Copia `.env.example` a `.env` (o configura las variables en tu plataforma de
despliegue, p. ej. Railway) y rellena:

| Variable            | Descripción                                                                 |
|---------------------|------------------------------------------------------------------------------|
| `BOT_TOKEN`          | Token del bot, obtenido de [@BotFather](https://t.me/BotFather).             |
| `CHAT_ID`            | ID del chat/grupo/canal de Telegram donde se publican las señales.          |
| `APP_URL`            | URL pública del despliegue (sin `/` final), ej. `https://miapp.up.railway.app`. |
| `PORT`               | Puerto del servidor (Railway lo asigna solo).                               |
| `TV_WEBHOOK_SECRET`  | (Opcional pero recomendado) Secreto para validar las alertas de TradingView. |
| `TG_WEBHOOK_SECRET`  | (Opcional pero recomendado) Secreto para validar que los webhooks vienen de Telegram. |

## Despliegue (Railway u otro PaaS)

1. Sube el repo y configura las variables de entorno anteriores.
2. El `Procfile` ya define `web: gunicorn main:app`.
3. Una vez desplegado y con `APP_URL` configurado, activa el webhook de
   Telegram visitando en el navegador:

   ```
   https://TU_DOMINIO/set_webhook
   ```

   Esto registra `https://TU_DOMINIO/tg_webhook` en Telegram (incluyendo el
   `TG_WEBHOOK_SECRET` si lo configuraste).

## Configurar la alerta en TradingView

En el mensaje de la alerta de TradingView, usa un JSON como este:

```json
{
  "message": "Señal LONG en BTCUSDT - Order Block + ADX confirmado",
  "secret": "EL_MISMO_VALOR_QUE_TV_WEBHOOK_SECRET"
}
```

Y en la configuración del webhook de la alerta, apunta a:

```
https://TU_DOMINIO/webhook
```

Si no configuras `TV_WEBHOOK_SECRET`, el campo `secret` no es necesario, pero
cualquiera que conozca la URL podría enviar mensajes falsos al canal — se
recomienda encarecidamente configurarlo en producción.

## Desarrollo local

```bash
pip install -r requirements.txt
export BOT_TOKEN=... CHAT_ID=... APP_URL=http://localhost:8080
python main.py
```

Para probar el webhook de TradingView localmente:

```bash
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{"message": "Prueba de señal"}'
```
