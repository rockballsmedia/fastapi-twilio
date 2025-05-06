import os
import json
import base64
import asyncio

from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Connect
from dotenv import load_dotenv
import openai

# ─── 1) Chargement de la clé OpenAI depuis .env ───────────────────────────────
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("⚠️ Définissez OPENAI_API_KEY dans .env")
openai.api_key = OPENAI_API_KEY

# ─── 2) Création de l’app FastAPI ─────────────────────────────────────────────
app = FastAPI()

# ─── 3) Endpoint Twilio pour démarrer la session media-stream ──────────────────
@app.post("/incoming-call")
async def incoming_call(request: Request):
    resp = VoiceResponse()
    connect = Connect()
    # URL absolue puisque Coolify gère déjà TLS et le domaine
    connect.stream(url=f"wss://{request.url.hostname}/media-stream")
    resp.append(connect)
    return Response(content=str(resp), media_type="application/xml")

# ─── 4) Handler WebSocket pour Twilio Media Streams ↔ OpenAI ───────────────────
@app.websocket("/media-stream")
async def media_stream(ws: WebSocket):
    await ws.accept()
    try:
        # On démarre un stream vers OpenAI (chat completion streaming)
        async with openai.ChatCompletion.acreate(
            model="gpt-4o-mini", stream=True,
            messages=[{"role":"system","content":"Tu es un assistant."}]
        ) as ai_ws:
            # Lecture des paquets entrants de Twilio
            async for msg in ws.iter_text():
                data = json.loads(msg)
                audio = base64.b64decode(data["media"]["payload"])
                await ai_ws.send(audio)
            # Envoi des réponses AI vers Twilio
            async for chunk in ai_ws:
                b64 = base64.b64encode(chunk).decode()
                await ws.send_text(json.dumps({"audio": b64}))
    except WebSocketDisconnect:
        await ws.close()

# ─── 5) Healthcheck (facultatif pour Coolify) ─────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok"}

# ─── 6) Démarrage local via Uvicorn ──────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0",
                port=int(os.getenv("PORT", 5000)), log_level="info")
