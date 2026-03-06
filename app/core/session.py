"""
Manages Gemini Live sessions and the ADK runner.
"""

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from core.config import APP_NAME
from meetmind_agent.agent import agent

session_service = InMemorySessionService()
runner = Runner(
    app_name=APP_NAME,
    agent=agent,
    session_service=session_service
)


def build_run_config() -> RunConfig:
    """Build the RunConfig for a Gemini Live bidirectional session."""
    return RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=["AUDIO"],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        session_resumption=types.SessionResumptionConfig(),
    )


async def get_or_create_session(user_id: str, session_id: str) -> None:
    """Retrieve existing session or create a new one."""
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id
    )
    if not session:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id
        )
