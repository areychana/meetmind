from dotenv import load_dotenv
load_dotenv()

import asyncio
import base64
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from meetmind_agent.agent import agent

APP_NAME = "meetmind"

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

session_service = InMemorySessionService()
runner = Runner(app_name=APP_NAME, agent=agent, session_service=session_service)

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.websocket("/ws/{user_id}/{session_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, session_id: str):
    await websocket.accept()

    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=["AUDIO"],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        session_resumption=types.SessionResumptionConfig(),
    )

    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if not session:
        await session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )

    live_request_queue = LiveRequestQueue()

    async def upstream_task():
        try:
            while True:
                raw = await websocket.receive_text()
                message = json.loads(raw)
                msg_type = message.get("type")
                if msg_type == "audio":
                    audio_bytes = base64.b64decode(message["data"])
                    blob = types.Blob(mime_type="audio/pcm;rate=16000", data=audio_bytes)
                    live_request_queue.send_realtime(blob)
                elif msg_type == "screen":
                    image_bytes = base64.b64decode(message["data"])
                    blob = types.Blob(mime_type="image/jpeg", data=image_bytes)
                    live_request_queue.send_realtime(blob)
                elif msg_type == "text":
                    content = types.Content(parts=[types.Part(text=message["data"])])
                    live_request_queue.send_content(content)
        except WebSocketDisconnect:
            pass
        except Exception as e:
            print(f"[upstream] error: {e}")

    async def downstream_task():
        # Track last sent transcript to avoid duplicates
        last_agent_transcript = ""
        last_user_transcript = ""

        try:
            async for event in runner.run_live(
                user_id=user_id,
                session_id=session_id,
                live_request_queue=live_request_queue,
                run_config=run_config,
            ):
                # ── Audio ──
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.inline_data and part.inline_data.mime_type.startswith("audio"):
                            audio_b64 = base64.b64encode(part.inline_data.data).decode()
                            await websocket.send_text(json.dumps({"type": "audio", "data": audio_b64}))
                        elif part.text:
                            await websocket.send_text(json.dumps({"type": "text", "data": part.text}))

                # ── User transcript — only send LONGER chunks (final is longest) ──
                input_t = getattr(event, 'input_transcription', None)
                if input_t:
                    txt = (getattr(input_t, 'text', '') or '').strip()
                    if txt and len(txt) > len(last_user_transcript):
                        last_user_transcript = txt
                        last_agent_transcript = ""  # reset agent for new turn
                        print(f"[USER] {txt}")
                        await websocket.send_text(json.dumps({"type": "transcript_user", "data": txt}))


                output_t = getattr(event, 'output_transcription', None)
                if output_t:
                    txt = (getattr(output_t, 'text', '') or '').strip()
                    if txt and len(txt) > len(last_agent_transcript):
                        last_agent_transcript = txt
                        print(f"[AGENT] {txt}")
                        await websocket.send_text(json.dumps({"type": "transcript_agent", "data": txt}))

        except Exception as e:
            print(f"[downstream] error: {e}")
            try:
                await websocket.send_text(json.dumps({"type": "error", "data": str(e)}))
            except Exception:
                pass

    try:
        await asyncio.gather(upstream_task(), downstream_task(), return_exceptions=True)
    finally:
        live_request_queue.close()
