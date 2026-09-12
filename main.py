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

TG_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ==========================================
# 1. WEBHOOK PARA TRADINGVIEW (Señales)
# ==========================================
@app.route('/webhook', methods=['POST'])
def tv_webhook():
    data = request.json
    if not data:
        return "No data", 400
    
    # TradingView enviará el mensaje en la clave "message"
    message = data.get('message', str(data))
    
    # Formatear mensaje para Telegram
    tg_message = f"🚨 *ALERTA DMCRIPTO*\n\n{message}"
    
    payload = {
        "chat_id": CHAT_ID,
        "text": tg_message,
        "parse_mode": "Markdown"
    }
    
    response = requests.post(f"{TG_URL}/sendMessage", json=payload)
    if response.status_code == 200:
        return "OK", 200
    else:
        logging.error(f"Error Telegram: {response.text}")
        return "Error", 500

# ==========================================
# 2. WEBHOOK PARA TELEGRAM (Comandos y Moderación)
# ==========================================
@app.route('/tg_webhook', methods=['POST'])
def tg_webhook():
    update = request.json
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
            requests.post(f"{TG_URL}/sendMessage", json={
                "chat_id": chat_id, "text": reply, "parse_mode": "Markdown", "reply_to_message_id": msg_id
            })
        
        elif text == '/faq':
            requests.post(f"{TG_URL}/sendMessage", json={
                "chat_id": chat_id, "text": "📚 *FAQ*\n1. ¿Qué es un OB? Zona de oferta/demanda institucional.\n2. ¿Cómo entro al VIP? Escribe a @AdminDMCripto.", 
                "parse_mode": "Markdown", "reply_to_message_id": msg_id
            })

        # Moderación básica: Borrar enlaces no autorizados
        elif 'http' in text or 't.me' in text:
            requests.post(f"{TG_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id})
            requests.post(f"{TG_URL}/sendMessage", json={
                "chat_id": chat_id, "text": "⚠️ *Spam detectado y eliminado.* Respeta las normas.", "parse_mode": "Markdown"
            })

    return "OK", 200

# ==========================================
# 3. RUTA PARA ACTIVAR EL WEBHOOK EN TELEGRAM
# ==========================================
@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    webhook_url = f"{APP_URL}/tg_webhook"
    url = f"{TG_URL}/setWebhook?url={requests.utils.quote(webhook_url)}"
    res = requests.get(url)
    return res.json()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)