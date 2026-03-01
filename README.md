<div align="center">
  <img src="screenshots/screenshot_hero_offline.png" alt="MeetMind" width="100%"/>
  <br/><br/>
  <h1>MeetMind</h1>
  <p><strong>A real-time AI meeting co-pilot powered by Gemini Live API</strong></p>

  <p>
    <img src="https://img.shields.io/badge/Gemini-Live%20API-4285F4?style=flat-square&logo=google" />
    <img src="https://img.shields.io/badge/Google-ADK-34A853?style=flat-square&logo=google" />
    <img src="https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi" />
    <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python" />
  </p>

  <p><em>"The smartest voice in the room is always yours."</em></p>
</div>

---

## Overview

MeetMind is your intelligent meeting assistant—silently monitoring while you attend meetings on Zoom, Teams, Google Meet, or any platform. Need clarification on something discussed? Whisper a question and get an instant, private answer through your earphones. No interruptions, no alert to the room, complete discretion.

---

## Features

- **Real-time voice AI** — Ultra-low latency responses via Gemini Live API
- **Private audio responses** — Answers delivered through your speakers only
- **Screen awareness** — Share your screen and ask context-aware questions
- **Silent input mode** — Type questions when you can't speak
- **Voice Activity Detection** — AI pauses when you speak, you stay in control
- **Live transcripts** — See the conversation unfold in real time
- **Platform agnostic** — Works alongside Zoom, Teams, Meet, or any meeting tool

---

## Screenshots

The interface features:
- **Landing page** — Simple, minimal entry point with session controls
- **Live session** — Active conversation stream with real-time updates
- **Voice chat** — Dual transcript showing your questions and AI responses
- **Screen sharing** — Share your screen for visual context awareness
- **Fluid canvas background** — Responsive, elegant design with cursor effects

---

## Architecture

```
+-------------------------------------------------------------+
|                        Browser                              |
|                                                             |
|   Microphone  -->  Web Audio API  -->  PCM 16kHz chunks     |
|   Screen      -->  ImageCapture   -->  JPEG frames          |
|   Text Input  -->  WebSocket Client                         |
|                          |                                  |
|   Audio Output  <--  AudioContext (24kHz scheduled queue)   |
|   Transcript    <--  WebSocket Messages                     |
+--------------------------|----------------------------------+
                           |  WebSocket (ws://)
                           |  audio / text / screen
                           |
+--------------------------|----------------------------------+
|                     FastAPI Server                         |
|                                                             |
|   upstream_task   receives browser messages                 |
|     audio   -->  Blob(audio/pcm;rate=16000)                 |
|     screen  -->  Blob(image/jpeg)                           |
|     text    -->  Content(parts=[Part(text=...)])            |
|                                                             |
|   downstream_task   streams Gemini responses                |
|     audio chunks   -->  base64  -->  WebSocket              |
|     transcriptions -->  WebSocket                           |
|                                                             |
|   ADK Runner.run_live()  +  LiveRequestQueue                |
+--------------------------|----------------------------------+
                           |  Google ADK
                           |  StreamingMode.BIDI
                           |
+--------------------------|----------------------------------+
|                   Gemini Live API                          |
|                                                             |
|   Model:  gemini-2.0-flash-live-001                        |
|   Input:  audio/pcm 16kHz  +  image/jpeg  +  text          |
|   Output: audio/pcm 24kHz  +  transcriptions               |
+-------------------------------------------------------------+
```

### Tech Stack

| Layer     | Technology                           |
|-----------|--------------------------------------|
| Frontend  | Vanilla JS, Web Audio API, Canvas    |
| Backend   | Python, FastAPI, WebSockets          |
| AI Model  | Google Gemini 2.0 Flash Live         |
| Agent SDK | Google ADK (LiveRequestQueue)        |
| Audio In  | PCM 16kHz via ScriptProcessorNode   |
| Audio Out | PCM 24kHz via AudioBufferSourceNode  |

---

## Project Structure

```
meetmind/
└── app/
    ├── main.py                  # FastAPI server, WebSocket handler,
    │                            # upstream/downstream ADK bridge
    ├── requirements.txt
    ├── Dockerfile
    ├── .env                     # GOOGLE_API_KEY
    │
    ├── meetmind_agent/
    │   ├── agent.py             # Gemini Live agent definition,
    │   │                        # system prompt, model config
    │   └── __init__.py
    │
    └── static/
        └── index.html           # Single-file frontend:
                                 # UI, Web Audio, VAD, WebSocket client,
                                 # fluid canvas background, cursor effects
```

---

## Getting Started

### Prerequisites

- **Python 3.11+** — Download from [python.org](https://www.python.org)
- **Google API key** — Obtain from [Google Cloud Console](https://console.cloud.google.com) with Gemini Live API access
- **Chrome** — Recommended browser for optimal Web Audio API support

### Installation & Setup

1. **Clone and navigate:**
   ```bash
   git clone https://github.com/areychana/meetmind.git
   cd meetmind/app
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   # source .venv/bin/activate   # macOS / Linux
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API key:**
   ```bash
   # Copy the example and add your actual API key
   cp .env.example .env
   
   # Then edit .env and replace the placeholder with your actual key
   # GOOGLE_API_KEY=your_actual_api_key_here
   ```

5. **Start the server:**
   ```bash
   uvicorn main:app --reload
   ```

   Open your browser to `http://127.0.0.1:8000`

### Usage

1. **Start the session** — Click "Start Session" and grant microphone access when prompted
2. **Join your meeting** — Open Zoom, Teams, Google Meet, or your meeting platform as usual
3. **Ask questions** — Either:
   - **Voice input:** Whisper a question naturally (VAD detects your speech automatically)
   - **Text input:** Type silently if you can't speak
4. **Add context** — Click "Share Screen" to let MeetMind see what you see
5. **Receive answers** — Listen to private responses through your speakers or read transcripts
6. **End session** — Click "End Session" when done

> **Tip:** For best results, keep your microphone close and whisper clearly to avoid meeting noise interference.

---

## How It Works

### Voice Activity Detection
A `ScriptProcessorNode` monitors audio energy (RMS) in real time. When energy spikes across 3 consecutive frames, the AI is interrupted immediately, ensuring your voice always takes priority—no awkward overlaps.

### Audio Scheduling
Incoming 24kHz PCM chunks from Gemini are decoded and queued sequentially using `AudioBufferSourceNode.start(when)` with a rolling `nextStartTime` cursor. This prevents gaps and overlaps, delivering seamless playback.

### Bidirectional Streaming
The FastAPI backend runs two concurrent asyncio tasks per WebSocket connection:
- **`upstream_task`** — Consumes browser messages (audio blobs, text input, screen frames) and pushes to `LiveRequestQueue`
- **`downstream_task`** — Iterates through `runner.run_live()` and forwards audio chunks and transcription events back to the browser

### Screen Context
Screen frames are captured every 5 seconds at 1280x720 resolution (JPEG quality 0.4) via `ImageCapture.grabFrame()` and sent as realtime blobs. The agent references screen content only when you explicitly ask.

---

## Environment Variables

Create a `.env` file in the `app/` directory (see `.env.example` for reference):

```bash
# Required
GOOGLE_API_KEY=sk-...  # Your Google API key from https://console.cloud.google.com

# Optional
MEETMIND_MODEL=gemini-2.5-flash-native-audio-preview-09-2025  # Gemini model to use
```

**Important:** Never commit `.env` to version control. It's excluded by `.gitignore`.

---

## Security & Privacy

MeetMind is designed with privacy in mind:

### Data Handling
- **All conversations are private** — Audio and transcripts stay between your browser and the Gemini API
- **No servers store your data** — Conversations are not logged or persisted by MeetMind
- **Screen shares are temporary** — Screen frames are only used during your session and discarded after

### Best Practices
- Use HTTPS/WSS in production for end-to-end encryption
- Never share your `.env` file or API key
- Use separate API keys for development and production
- Regularly rotate your Google API key
- Monitor API usage in [Google Cloud Console](https://console.cloud.google.com)

### Data Security Recommendations
- Run on a trusted network (avoid public WiFi for sensitive meetings)
- Use VPN if accessing from untrusted locations
- Keep Chrome and your OS updated for WebAudio API security patches
- Consider airgapped deployments for highly sensitive conversations

---

## Docker Deployment

### Build Docker Image
```bash
cd app
docker build -t meetmind:latest .
```

### Run with Docker
```bash
docker run -p 8000:8000 \
  -e GOOGLE_API_KEY=your_key_here \
  meetmind:latest
```

Or use docker-compose:
```yaml
version: '3.8'
services:
  meetmind:
    build: ./app
    ports:
      - "8000:8000"
    environment:
      GOOGLE_API_KEY: ${GOOGLE_API_KEY}
    restart: unless-stopped
```

Then run: `docker-compose up`

---

## Development & Debugging

### Run in Development Mode
By default, `uvicorn main:app --reload` enables hot-reloading on code changes. Debug output appears in your terminal.

### Disable Conversation Logging
To prevent logging of user conversations in development:
- Edit `main.py` lines 107, 116 to use logging module instead
- Or comment out `print()` statements during testing

### Flask-style Debugging
```bash
# Set debug mode (restarts on file changes)
uvicorn main:app --reload --log-level debug

# Run on different port
uvicorn main:app --port 8080

# Bind to all interfaces (for remote access)
uvicorn main:app --host 0.0.0.0
```

### Browser DevTools
1. Open Chrome DevTools (`F12`)
2. Go to **Console** tab to see WebSocket messages
3. Use **Network** tab to monitor real-time bidirectional communication
4. Check **Application > Cookies** for session storage

---

## WebSocket API

### Endpoint
```
ws://localhost:8000/ws/{user_id}/{session_id}
```

### Message Types

**Sending from client:**
```json
{
  "type": "audio",
  "data": "base64_encoded_pcm_16000"
}

{
  "type": "text",
  "data": "User question"
}

{
  "type": "screen",
  "data": "base64_encoded_jpeg"
}
```

**Receiving from server:**
```json
{
  "type": "audio",
  "data": "base64_encoded_pcm_24000"
}

{
  "type": "transcript_user",
  "data": "Your spoken question"
}

{
  "type": "transcript_agent",
  "data": "AI's response"
}

{
  "type": "error",
  "data": "Error message"
}
```

---

## Troubleshooting

### Microphone not working
- **Chrome permissions:** Check if Chrome has microphone access (Settings > Privacy > Microphone)
- **OS permissions:** Grant microphone access to Chrome at OS level (Windows Settings > Privacy & Security)
- **USB microphone:** Try a different microphone, some USB mics require driver updates

### No audio from AI
- **Speaker volume:** Check system and application volume levels
- **Audio output:** Verify "Audio Output" button is highlighted in MeetMind UI
- **Browser mute:** Check if Chrome tab is muted (right-click tab > Unmute)

### WebSocket connection fails
- **CORS:** Ensure server allows WebSocket connections from your domain
- **Firewall:** Some corporate networks block WebSocket; try HTTPS/WSS
- **API key:** Verify `GOOGLE_API_KEY` is valid in `.env`

### Slow/Laggy responses
- **Network latency:** Test your internet speed; high latency increases response time
- **AI model overloaded:** Try again or switch model in `.env`
- **Browser tabs:** Close unnecessary tabs to free up browser resources
- **VAD threshold:** Adjust voice sensitivity in `index.html` (search for `VAD_THRESHOLD`)

### API quota exceeded
- **Rate limiting:** You've hit Google's API rate limits
- **Check Cloud Console:** Review usage at [console.cloud.google.com](https://console.cloud.google.com)
- **Add billing:** Enable billing to increase quota limits

### Screen sharing not working
- **Browser support:** Ensure Chrome supports `getDisplayMedia()` (Chrome 72+)
- **HTTPS required:** Screen capture requires HTTPS; won't work on `http://localhost`
- **Permission denied:** Grant Chrome screen capture permission when prompted

---

## Contributing

Contributions are welcome! Please feel free to open issues for bugs or feature requests, and submit pull requests to help improve MeetMind.

## License

MIT — Feel free to use MeetMind in your own projects.

---

**Built for the Gemini Live Agent Hackathon by [areychana](https://github.com/areychana), 2026.**

*"The smartest voice in the room is always yours."*
