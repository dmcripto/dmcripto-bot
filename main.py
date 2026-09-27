import os
import logging
from flask import Flask, request
import requests

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# Variables de entorno (se configuran en Railway)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
APP_URL = os.environ.get("APP_URL") # Ej: https://tu-proyecto.up.railway.app
PORT = int(os.environ.get("PORT", 8080))

# Secretos para validar el origen de los webhooks (opcionales pero recomendados)
TV_WEBHOOK_SECRET = os.environ.get("TV_WEBHOOK_SECRET")  # Debe coincidir con el que se pone en el mensaje de la alerta de TradingView
TG_WEBHOOK_SECRET = os.environ.get("TG_WEBHOOK_SECRET")  # Se registra en Telegram vía setWebhook y se valida por cabecera

TG_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_telegram_message(chat_id, text, reply_to_message_id=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_to_message_id is not None:
        payload["reply_to_message_id"] = reply_to_message_id
    try:
        response = requests.post(f"{TG_URL}/sendMessage", json=payload, timeout=10)
        if response.status_code != 200:
            logging.error(f"Error Telegram: {response.text}")
        return response
    except requests.RequestException as exc:
        logging.error(f"Fallo al contactar Telegram: {exc}")
        return None


LONG_KEYWORDS = ('long', 'compra', 'buy', 'alcista')
SHORT_KEYWORDS = ('short', 'venta', 'sell', 'bajista')


def normalize_side_from_value(value):
    if not value:
        return None
    value = str(value).strip().lower()
    if value in LONG_KEYWORDS:
        return 'LONG'
    if value in SHORT_KEYWORDS:
        return 'SHORT'
    return None


def detect_side_from_text(text):
    text = (text or '').lower()
    has_long = any(k in text for k in LONG_KEYWORDS)
    has_short = any(k in text for k in SHORT_KEYWORDS)
    if has_long and not has_short:
        return 'LONG'
    if has_short and not has_long:
        return 'SHORT'
    return None


def build_signal_body(data, raw_text):
    """Construye el cuerpo del mensaje a partir del JSON (si lo hay) o del texto plano."""
    if data:
        message = data.get('message')
        if message:
            return str(message)
        lines = []
        symbol = data.get('symbol') or data.get('ticker')
        price = data.get('price') or data.get('close')
        time_ = data.get('time')
        if symbol:
            lines.append(f"Símbolo: {symbol}")
        if price:
            lines.append(f"Precio: {price}")
        if time_:
            lines.append(f"Hora: {time_}")
        if lines:
            return "\n".join(lines)
        return str(data)
    return raw_text.strip()


# ==========================================
# 1. WEBHOOK PARA TRADINGVIEW (Señales)
# ==========================================
# El plan gratuito de TradingView permite alertas por webhook, pero el cuerpo
# puede llegar como texto plano (no siempre JSON) y no admite cabeceras
# personalizadas, así que el secreto se valida por query string (?token=...).
@app.route('/webhook', methods=['POST'])
def tv_webhook():
    raw_body = request.get_data(as_text=True) or ""
    data = request.get_json(silent=True, force=True)

    if TV_WEBHOOK_SECRET:
        token = request.args.get('token') or (data.get('secret') if data else None)
        if token != TV_WEBHOOK_SECRET:
            logging.warning("Webhook de TradingView rechazado: secreto inválido")
            return "Unauthorized", 401

    if not data and not raw_body.strip():
        return "No data", 400

    # Detectar LONG/SHORT: primero por un campo explícito (action/side/signal),
    # y si no existe, buscando palabras clave en el texto de la alerta.
    side = normalize_side_from_value(
        data.get('action') or data.get('side') or data.get('signal')
    ) if data else None

    body = build_signal_body(data, raw_body)

    if side is None:
        side = detect_side_from_text(body)

    if side == 'LONG':
        header = "🟢🚀 *SEÑAL LONG (COMPRA)* - DMCRIPTO"
    elif side == 'SHORT':
        header = "🔴🔻 *SEÑAL SHORT (VENTA)* - DMCRIPTO"
    else:
        header = "🚨 *ALERTA DMCRIPTO*"

    tg_message = f"{header}\n\n{body}"

    response = send_telegram_message(CHAT_ID, tg_message)
    if response is not None and response.status_code == 200:
        return "OK", 200
    return "Error", 500

# ==========================================
# 2. WEBHOOK PARA TELEGRAM (Comandos y Moderación)
# ==========================================
@app.route('/tg_webhook', methods=['POST'])
def tg_webhook():
    # Si se configuró TG_WEBHOOK_SECRET, Telegram debe enviarlo en esta cabecera
    if TG_WEBHOOK_SECRET and request.headers.get('X-Telegram-Bot-Api-Secret-Token') != TG_WEBHOOK_SECRET:
        logging.warning("Webhook de Telegram rechazado: secreto inválido")
        return "Unauthorized", 401

    update = request.get_json(silent=True)
    if not update:
        return "OK", 200

    # Manejar mensajes de texto
    if 'message' in update and 'text' in update['message']:
        chat_id = update['message']['chat']['id']
        text = update['message']['text'].lower()
        msg_id = update['message']['message_id']

        # Respuesta a comandos
        if text in ['/start', '/ayuda']:
            reply = (
                "🤖 *Bot Oficial DMCRIPTO*\n\n"
                "✅ Moderación de spam activa.\n"
                "✅ Alertas de Order Blocks + ADX.\n\n"
                "Comandos:\n"
                "/estadisticas - Ver info\n"
                "/faq - Preguntas frecuentes"
            )
            send_telegram_message(chat_id, reply, reply_to_message_id=msg_id)

        elif text == '/faq':
            send_telegram_message(
                chat_id,
                "📚 *FAQ*\n1. ¿Qué es un OB? Zona de oferta/demanda institucional.\n2. ¿Cómo entro al VIP? Escribe a @AdminDMCripto.",
                reply_to_message_id=msg_id
            )

        # Moderación básica: Borrar enlaces no autorizados
        elif 'http' in text or 't.me' in text:
            try:
                requests.post(f"{TG_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id}, timeout=10)
            except requests.RequestException as exc:
                logging.error(f"No se pudo borrar el mensaje: {exc}")
            send_telegram_message(chat_id, "⚠️ *Spam detectado y eliminado.* Respeta las normas.")

    return "OK", 200

# ==========================================
# 3. RUTA PARA ACTIVAR EL WEBHOOK EN TELEGRAM
# ==========================================
@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    webhook_url = f"{APP_URL}/tg_webhook"
    params = {"url": webhook_url}
    if TG_WEBHOOK_SECRET:
        params["secret_token"] = TG_WEBHOOK_SECRET
    res = requests.get(f"{TG_URL}/setWebhook", params=params)
    return res.json()


@app.route('/', methods=['GET'])
def health():
    return "DMCripto bot activo", 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)