import os
import json
import asyncio
import base64

from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Connect
from dotenv import load_dotenv
import openai

# ── 1) Chargement des clés et config ─────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Définissez OPENAI_API_KEY dans .env")
openai.api_key = OPENAI_API_KEY

# ── 2) Création de l’app FastAPI ─────────────────────────────────────────────
app = FastAPI()

# ── 3) Endpoint Twilio qui renvoie le TwiML pour démarrer la session média ───
@app.post("/incoming-call")
async def incoming_call(request: Request):
    resp = VoiceResponse()
    # on connecte Twilio Media Stream au WebSocket /media-stream
    connect = Connect()
    connect.stream(url=f"wss://{request.url.hostname}/media-stream")
    resp.append(connect)
    return Response(content=str(resp), media_type="application/xml")

# ── 4) Handler WebSocket pour le media-stream ────────────────────────────────
@app.websocket("/media-stream")
async def media_stream(ws: WebSocket):
    # 1) On accepte la connexion WS de Twilio
    await ws.accept()
    try:
        # 2) On ouvre une session WebSocket avec OpenAI
        async with openai.ChatCompletion.acreate(
            model="gpt-4o-mini", stream=True,
            messages=[{"role":"system","content":"Tu es un assistant."}]
        ) as ai_ws:
            # 3) Tant que Twilio envoie des paquets audio, on les relaie
            async for msg in ws.iter_text():
                data = json.loads(msg)
                audio_chunk = base64.b64decode(data["media"]["payload"])
                # Ici, on enverrait `audio_chunk` à l’IA (via un endpoint adapté)
                await ai_ws.send(audio_chunk)

            # 4) On lit le flux de réponses d’OpenAI et on les renvoie
            async for chunk in ai_ws:
                # chunk contient une partie de la réponse AI
                # on l’encapsule en base64 pour Twilio
                b64 = base64.b64encode(chunk).decode()
                await ws.send_text(json.dumps({"audio": b64}))

    except WebSocketDisconnect:
        # Ferme proprement si l’un des deux coupe
        await ws.close()

# ── 5) Point de terminaison optionnel pour health check ──────────────────────
@app.get("/health")
async def health():
    return {"status": "ok"}

# ── 6) Démarrage en local (si on fait `python main.py`) ─────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 5000)), log_level="info")
