import os
import json
import base64
import asyncio
import websockets
from datetime import datetime

from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Connect
from dotenv import load_dotenv
import openai

# ─── Chargement de la clé OpenAI depuis .env ──────────────────────────────────
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("⚠️ Définissez OPENAI_API_KEY dans .env")
openai.api_key = OPENAI_API_KEY

# ─── Préparation du dossier de logs ───────────────────────────────────────────
LOGS_DIRECTORY = "conversation_logs"
os.makedirs(LOGS_DIRECTORY, exist_ok=True)

# ─── Instructions et paramètres pour l'IA ───────────────────────────────────
SYSTEM_MESSAGE = (
    "Vous êtes un agent immobilier AI joyeux et serviable, "
    "capable de comprendre les besoins du client et de proposer des biens adaptés."
)
VOICE = "alloy"
LOG_EVENT_TYPES = [
    "response.content.done",
    "rate_limits.updated",
    "response.done",
    "input_audio_buffer.committed",
    "input_audio_buffer.speech_stopped",
    "input_audio_buffer.speech_started",
    "session.created"
]

# ─── Création de l'application FastAPI ───────────────────────────────────────
app = FastAPI()

@app.api_route("/", methods=["GET"])
async def index_page():
    return HTMLResponse("<h1>✅ FastAPI Twilio↔OpenAI Realtime OK</h1>")

@app.api_route("/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call(request: Request):
    """
    Webhook Twilio : renvoie le TwiML pour ouvrir le media-stream.
    """
    host = request.url.hostname
    resp = VoiceResponse()
    conn = Connect()
    conn.stream(url=f"wss://{host}/media-stream")
    resp.append(conn)
    return HTMLResponse(content=str(resp), media_type="application/xml")

@app.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    """
    WebSocket qui relie Twilio et OpenAI Realtime en duplex.
    """
    print("Client connected")
    await websocket.accept()

    # 1) On se connecte au WebSocket Realtime d'OpenAI
    openai_url = (
        "wss://api.openai.com/v1/realtime"
        "?model=gpt-4o-realtime-preview-2024-10-01"
    )
    extra_headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1"
    }

    async with websockets.connect(openai_url, extra_headers=extra_headers) as openai_ws:
        # 2) Envoi de la configuration de session (VAD, formats, instructions…)
        await send_session_update(openai_ws)

        # 3) Préparation des fichiers de logs pour cet appel
        stream_sid = None
        conversation_id = datetime.now().strftime("%Y%m%d%H%M%S")
        audio_log = open(f"{LOGS_DIRECTORY}/{conversation_id}_audio.txt", "a")
        text_log  = open(f"{LOGS_DIRECTORY}/{conversation_id}_text.txt",  "a")

        # ── Tâche A : réception des paquets Twilio → envoi à OpenAI ─────────────
        async def receive_from_twilio():
            nonlocal stream_sid
            try:
                async for message in websocket.iter_text():
                    data = json.loads(message)
                    evt = data.get("event")
                    if evt == "media" and openai_ws.open:
                        # envoi du chunk audio codé en Base64
                        await openai_ws.send(json.dumps({
                            "type": "input_audio_buffer.append",
                            "audio": data["media"]["payload"]
                        }))
                        audio_log.write(f"Received audio: {data['media']['payload']}\n")
                    elif evt == "start":
                        stream_sid = data["start"]["streamSid"]
                        print(f"Incoming stream has started ({stream_sid})")
            except WebSocketDisconnect:
                print("Client disconnected in receive_from_twilio")
                if openai_ws.open:
                    await openai_ws.close()

        # ── Tâche B : réception OpenAI → renvoi à Twilio ────────────────────────
        async def send_to_twilio():
            nonlocal stream_sid
            try:
                async for msg in openai_ws:
                    response = json.loads(msg)
                    # logs pour le debug
                    if response.get("type") in LOG_EVENT_TYPES:
                        print(f"Received event: {response['type']}", response)

                    # audio de réponse IA → renvoi à Twilio
                    if response.get("type") == "response.audio.delta" and response.get("data"):
                        audio_payload = response["data"]
                        await websocket.send_json({
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {"payload": audio_payload}
                        })
                        audio_log.write(f"Sent audio: {audio_payload}\n")

                    # texte de réponse IA → log texte
                    if response.get("type") == "response.text" and response.get("text"):
                        text_log.write(f"AI response: {response['text']}\n")
            except Exception as e:
                print(f"Error in send_to_twilio: {e}")

        # 4) Lancement simultané des deux tâches
        await asyncio.gather(
            receive_from_twilio(),
            send_to_twilio()
        )

        # 5) Fermeture des fichiers de log
        audio_log.close()
        text_log.close()

async def send_session_update(openai_ws: websockets.WebSocketClientProtocol):
    """
    Envoie, une fois, la configuration initiale pour la session Realtime.
    """
    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "input_audio_format":  "g711_ulaw",
            "output_audio_format": "g711_ulaw",
            "voice": VOICE,
            "instructions": SYSTEM_MESSAGE,
            "modalities": ["text", "audio"],
            "temperature": 0.8
        }
    }
    await openai_ws.send(json.dumps(session_update))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        log_level="info"
    )
