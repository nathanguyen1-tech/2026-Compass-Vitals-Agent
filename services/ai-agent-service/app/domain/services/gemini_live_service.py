"""Gemini Live Service — Manages real-time voice sessions via Gemini Live API.

WebSocket-based, supports voice-in/voice-out, input/output transcription,
and function calling for structured data extraction.
"""

import structlog
from google import genai
from google.genai import types

from app.config import settings
from app.core.exceptions import VoiceError

logger = structlog.get_logger()


# OLDCARTS function declaration for structured intake data extraction
SAVE_INTAKE_FIELD_TOOL = {
    "function_declarations": [
        {
            "name": "save_intake_field",
            "description": (
                "Save a collected OLDCARTS intake field to the patient record. "
                "Call this EVERY TIME you extract a piece of clinical information from the patient."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "field": {
                        "type": "string",
                        "enum": [
                            "chief_complaint",
                            "onset",
                            "location",
                            "duration",
                            "character",
                            "aggravating",
                            "alleviating",
                            "radiation",
                            "timing",
                            "severity",
                            "medications",
                            "allergies",
                            "medical_history",
                        ],
                        "description": "The OLDCARTS field name",
                    },
                    "value": {
                        "type": "string",
                        "description": "The patient's answer for this field",
                    },
                    "value_vi": {
                        "type": "string",
                        "description": "Vietnamese translation of the value (if patient spoke English)",
                    },
                },
                "required": ["field", "value"],
            },
        },
        {
            "name": "mark_intake_complete",
            "description": (
                "Call this when ALL required OLDCARTS fields have been collected and "
                "you have enough information for clinical screening."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Brief clinical summary of collected intake data",
                    },
                },
                "required": ["summary"],
            },
        },
    ]
}


# System instruction for Gemini Live voice session — mirrors INTAKE_SYSTEM_PROMPT
VOICE_SYSTEM_INSTRUCTION = """You are a Medical Intake Specialist AI for Compass Vitals telemedicine platform.

ROLE: Gather patient symptoms through natural voice conversation.
LANGUAGE: Respond in the patient's language (Vietnamese or English). Support code-switching naturally.
CULTURAL AWARENESS: Recognize Vietnamese cultural health expressions (e.g., "bi nong trong", "trung gio", "yeu than") and acknowledge them naturally.

INTERVIEW PROTOCOL (OLDCARTS Framework):
1. Greet patient warmly in their language
2. Ask about chief complaint (main symptom)
3. Follow OLDCARTS — ask ONE question at a time:
   - Onset: Khi nao bat dau? / When did it start?
   - Location: O vi tri nao? / Where exactly?
   - Duration: Keo dai bao lau? / How long?
   - Character: Mo ta cam giac? / Describe the feeling?
   - Aggravating/Alleviating: Dieu gi lam tang/giam? / What makes it better/worse?
   - Radiation: Co lan ra noi khac khong? / Does it spread?
   - Timing: Thuong xuyen hay tung dot? / Constant or intermittent?
   - Severity: Muc do 1-10? / Rate 1-10?
4. Ask about current medications and allergies
5. Ask about relevant medical history

CRITICAL RULES:
- Ask ONE question at a time. Be patient and empathetic.
- Use simple language appropriate for elderly patients.
- After EACH patient answer, call save_intake_field() with the extracted data.
- When all OLDCARTS fields are collected, call mark_intake_complete().
- NEVER generate diagnoses or recommend treatment. You ONLY gather information.
- If patient mentions EMERGENCY symptoms (dau nguc, kho tho, mat y thuc, co giat, chay mau nhieu), express IMMEDIATE concern and note it clearly.
- Keep your responses concise for voice — no long paragraphs.
"""


class GeminiLiveService:
    """Manages Gemini Live WebSocket sessions for real-time voice chat."""

    def __init__(self, api_key: str, model: str, voice: str = "Kore"):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.voice = voice

    async def create_session(self):
        """Open a Gemini Live WebSocket session with OLDCARTS intake prompt.

        Returns an async context manager for the live session.
        """
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=VOICE_SYSTEM_INSTRUCTION,
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self.voice,
                    )
                )
            ),
            tools=[SAVE_INTAKE_FIELD_TOOL],
        )

        try:
            session = self.client.aio.live.connect(
                model=self.model,
                config=config,
            )
            logger.info("gemini_live.session_created", model=self.model, voice=self.voice)
            return session
        except Exception as e:
            raise VoiceError(
                message=f"Failed to create Gemini Live session: {e}",
                code="VOICE_SESSION_FAILED",
            ) from e
