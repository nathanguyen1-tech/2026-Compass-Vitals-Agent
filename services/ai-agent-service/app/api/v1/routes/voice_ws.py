"""Voice WebSocket endpoint — Real-time voice chat via Gemini Live API.

Browser <-> WebSocket <-> Backend <-> Gemini Live API (WebSocket)

Audio flows bidirectionally. Transcripts are collected for safety pipeline.
Emergency detection runs in real-time on every user transcript.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google.genai import types

from app.api.v1.routes.chat import _sessions, _phi
from app.config import settings
from app.domain.services.gemini_live_service import GeminiLiveService
from app.domain.services.voice_safety import (
    quick_emergency_check,
    get_emergency_details,
    extract_cultural_expressions,
    run_post_session_safety,
)

logger = structlog.get_logger()
router = APIRouter()

# Initialize Gemini Live service
_gemini_live: GeminiLiveService | None = (
    GeminiLiveService(
        api_key=settings.gemini_api_key,
        model=settings.gemini_live_model,
        voice=settings.tts_voice,
    )
    if settings.gemini_api_key
    else None
)


@router.websocket("/ws/voice/{session_id}")
async def voice_websocket(websocket: WebSocket, session_id: str | None = None):
    """Handle real-time voice chat via WebSocket.

    Protocol (Browser -> Server):
        - Binary frames: Raw PCM audio (16-bit, 16kHz, mono)
        - JSON frames: {"type": "end_session"} to gracefully close

    Protocol (Server -> Browser):
        - Binary frames: PCM audio response from Gemini (24kHz)
        - JSON frames:
            {"type": "user_transcript", "text": "..."}
            {"type": "model_transcript", "text": "..."}
            {"type": "emergency", "text": "...", "keywords": [...]}
            {"type": "session_info", "session_id": "..."}
            {"type": "intake_field", "field": "...", "value": "..."}
            {"type": "intake_complete", "summary": "..."}
            {"type": "cultural", "expressions": [...]}
            {"type": "error", "message": "..."}
    """
    await websocket.accept()

    if not _gemini_live:
        await websocket.send_json({"type": "error", "message": "Voice service not configured. Set GEMINI_API_KEY."})
        await websocket.close()
        return

    # Get or create session (shared with text chat)
    sid = session_id if session_id and session_id != "null" else str(uuid.uuid4())
    session = _sessions.get(sid)
    if session is None:
        session = {
            "messages": [],
            "patient_id": str(uuid.uuid4()),
            "case_id": str(uuid.uuid4()),
            "organization_id": str(uuid.uuid4()),
            "intake_data": {},
            "intake_complete": False,
            "is_emergency": False,
            "detected_language": "vi",
            "cultural_expressions": [],
            "voice_transcripts": [],
            "input_mode": "voice",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _sessions[sid] = session

    session["input_mode"] = "voice"

    await websocket.send_json({"type": "session_info", "session_id": sid})

    transcript_log: list[dict] = []
    stop_event = asyncio.Event()

    try:
        async with await _gemini_live.create_session() as live_session:

            async def forward_browser_audio():
                """Receive audio from browser and forward to Gemini Live."""
                try:
                    while not stop_event.is_set():
                        data = await websocket.receive()
                        if data.get("type") == "websocket.disconnect":
                            stop_event.set()
                            break
                        if "bytes" in data and data["bytes"]:
                            # Binary frame = PCM audio
                            await live_session.send_realtime_input(
                                audio=types.Blob(
                                    data=data["bytes"],
                                    mime_type="audio/pcm;rate=16000",
                                )
                            )
                        elif "text" in data and data["text"]:
                            # JSON frame = control message
                            msg = json.loads(data["text"])
                            if msg.get("type") == "end_session":
                                stop_event.set()
                                break
                except WebSocketDisconnect:
                    stop_event.set()
                except Exception as e:
                    logger.warning("voice_ws.browser_audio_error", error=str(e))
                    stop_event.set()

            async def forward_gemini_responses():
                """Receive responses from Gemini and forward to browser."""
                try:
                    while not stop_event.is_set():
                        async for response in live_session.receive():
                            if stop_event.is_set():
                                break

                            # Input transcription (what user said)
                            if (
                                response.server_content
                                and response.server_content.input_transcription
                                and response.server_content.input_transcription.text
                            ):
                                user_text = response.server_content.input_transcription.text
                                timestamp = datetime.now(timezone.utc).isoformat()

                                transcript_log.append({
                                    "role": "user",
                                    "text": user_text,
                                    "timestamp": timestamp,
                                })

                                await websocket.send_json({
                                    "type": "user_transcript",
                                    "text": user_text,
                                })

                                # REAL-TIME emergency check (< 1ms)
                                if quick_emergency_check(user_text):
                                    keywords = get_emergency_details(user_text)
                                    session["is_emergency"] = True
                                    await websocket.send_json({
                                        "type": "emergency",
                                        "text": user_text,
                                        "keywords": keywords,
                                    })
                                    logger.critical(
                                        "voice.emergency_detected",
                                        session_id=sid,
                                        keywords=keywords,
                                    )
                                    stop_event.set()
                                    break

                                # Real-time cultural expression check
                                cultural = extract_cultural_expressions(user_text)
                                if cultural:
                                    await websocket.send_json({
                                        "type": "cultural",
                                        "expressions": cultural,
                                    })

                            # Output transcription (what AI said)
                            if (
                                response.server_content
                                and response.server_content.output_transcription
                                and response.server_content.output_transcription.text
                            ):
                                model_text = response.server_content.output_transcription.text
                                transcript_log.append({
                                    "role": "assistant",
                                    "text": model_text,
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                })
                                await websocket.send_json({
                                    "type": "model_transcript",
                                    "text": model_text,
                                })

                            # Audio output (forward to browser for playback)
                            if (
                                response.server_content
                                and response.server_content.model_turn
                                and response.server_content.model_turn.parts
                            ):
                                for part in response.server_content.model_turn.parts:
                                    if part.inline_data and part.inline_data.data:
                                        await websocket.send_bytes(part.inline_data.data)

                            # Function calls (save_intake_field, mark_intake_complete)
                            if response.tool_call and response.tool_call.function_calls:
                                function_responses = []
                                for fc in response.tool_call.function_calls:
                                    result = handle_function_call(fc, session, sid)
                                    function_responses.append(
                                        types.FunctionResponse(
                                            id=fc.id,
                                            name=fc.name,
                                            response=result,
                                        )
                                    )
                                    # Notify browser
                                    await websocket.send_json({
                                        "type": "intake_field" if fc.name == "save_intake_field" else "intake_complete",
                                        **result,
                                    })

                                await live_session.send_tool_response(
                                    function_responses=function_responses
                                )

                except Exception as e:
                    if not stop_event.is_set():
                        logger.warning("voice_ws.gemini_response_error", error=str(e))
                        stop_event.set()

            # Run both tasks concurrently
            await asyncio.gather(
                forward_browser_audio(),
                forward_gemini_responses(),
                return_exceptions=True,
            )

    except Exception as e:
        logger.error("voice_ws.session_error", error=str(e), session_id=sid)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass

    finally:
        # POST-HOC: Run full safety pipeline on collected transcripts
        if transcript_log:
            try:
                await run_post_session_safety(session, transcript_log, _phi)
            except Exception as e:
                logger.error("voice_ws.safety_pipeline_error", error=str(e))

        logger.info(
            "voice_ws.session_ended",
            session_id=sid,
            total_turns=len(transcript_log),
            is_emergency=session.get("is_emergency", False),
        )

        try:
            await websocket.close()
        except Exception:
            pass


def handle_function_call(fc, session: dict, session_id: str) -> dict:
    """Handle Gemini Live function calls for OLDCARTS data extraction."""
    args = fc.args if hasattr(fc, "args") else {}

    if fc.name == "save_intake_field":
        field = args.get("field", "")
        value = args.get("value", "")
        value_vi = args.get("value_vi", "")

        if "intake_data" not in session or session["intake_data"] is None:
            session["intake_data"] = {}
        session["intake_data"][field] = {
            "value": value,
            "value_vi": value_vi,
            "source": "voice",
        }

        logger.info(
            "voice.intake_field_saved",
            session_id=session_id,
            field=field,
        )
        return {"status": "saved", "field": field, "value": value}

    elif fc.name == "mark_intake_complete":
        summary = args.get("summary", "")
        session["intake_complete"] = True

        logger.info(
            "voice.intake_complete",
            session_id=session_id,
            fields_collected=list((session.get("intake_data") or {}).keys()),
        )
        return {"status": "completed", "summary": summary}

    return {"status": "unknown_function", "name": fc.name}
