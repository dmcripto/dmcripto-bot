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

## Configurar alertas en TradingView (plan gratuito/Basic)

El plan **gratuito** de TradingView sí permite activar el webhook en las
alertas (opción "Webhook URL" en la pestaña *Notifications* del diálogo de
alerta). Las únicas limitaciones del plan gratuito son:

- No admite cabeceras HTTP personalizadas → por eso el secreto se valida
  mediante un parámetro en la propia URL (`?token=...`), no por header.
- No permite alertas "dinámicas" con `alert()` dentro del script (eso sí
  requiere un plan de pago). La solución es crear **una alerta por
  condición**: una para LONG y otra para SHORT, cada una con su propio
  mensaje estático (usando los placeholders de TradingView como
  `{{ticker}}`, `{{close}}`, `{{time}}`).

El bot detecta automáticamente si la señal es LONG o SHORT y la resalta en
Telegram (🟢 verde para LONG, 🔴 rojo para SHORT), de dos formas posibles:

1. Buscando un campo `action` / `side` / `signal` en el JSON (valores
   admitidos: `long`, `buy`, `compra`, `short`, `sell`, `venta`, etc.).
2. Si el mensaje es texto plano, buscando esas mismas palabras clave en el
   propio texto.

### 1. URL del webhook

En la pestaña *Notifications* de cada alerta, marca **"Webhook URL"** y pon:

```
https://TU_DOMINIO/webhook?token=TU_TV_WEBHOOK_SECRET
```

(si no configuraste `TV_WEBHOOK_SECRET`, usa simplemente
`https://TU_DOMINIO/webhook`, aunque no se recomienda para producción, ya que
cualquiera que conozca la URL podría enviar mensajes falsos al canal).

### 2. Alerta para LONG

En el campo "Message" de la alerta, cualquiera de estas dos opciones funciona:

Texto plano (más simple, sin necesidad de JSON):
```
🟢 LONG {{ticker}} | Entrada: {{close}} | {{interval}} | {{time}}
```

O en formato JSON (más estructurado):
```json
{
  "action": "LONG",
  "symbol": "{{ticker}}",
  "price": "{{close}}",
  "time": "{{time}}"
}
```

### 3. Alerta para SHORT

Crea una segunda alerta con la condición contraria (o el mismo script
señalando la entrada corta) y usa:

Texto plano:
```
🔴 SHORT {{ticker}} | Entrada: {{close}} | {{interval}} | {{time}}
```

O JSON:
```json
{
  "action": "SHORT",
  "symbol": "{{ticker}}",
  "price": "{{close}}",
  "time": "{{time}}"
}
```

> Nota: si usas el JSON, no hace falta incluir `"secret"` dentro del cuerpo
> porque la validación ya se hace con `?token=` en la URL; se sigue
> aceptando por compatibilidad si prefieres ponerlo ahí en vez de en la URL.

## Desarrollo local

```bash
pip install -r requirements.txt
export BOT_TOKEN=... CHAT_ID=... APP_URL=http://localhost:8080
python main.py
```

Para probar el webhook de TradingView localmente:

```bash
# JSON con acción explícita
curl -X POST "http://localhost:8080/webhook?token=$TV_WEBHOOK_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"action": "LONG", "symbol": "BTCUSDT", "price": "65000"}'

# Texto plano (como lo envía TradingView cuando el mensaje no es JSON válido)
curl -X POST "http://localhost:8080/webhook?token=$TV_WEBHOOK_SECRET" \
  -H "Content-Type: text/plain" \
  --data-raw "SHORT BTCUSDT entrada 64000"
```
