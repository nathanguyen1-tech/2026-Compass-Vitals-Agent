"""Voice Safety — Real-time + post-hoc safety checks on voice transcripts.

Reuses existing emergency_detector, phi_deidentifier, cultural_mapper
WITHOUT modifying any of those modules.
"""

import structlog

from app.agents.tools.emergency_detector import detect_emergency, get_emergency_keywords_found
from app.nlp.cultural_mapper import CulturalMapper

logger = structlog.get_logger()

_cultural_mapper = CulturalMapper()


def quick_emergency_check(text: str) -> bool:
    """Ultra-fast emergency keyword check on transcript text.

    Reuses existing detect_emergency() from emergency_detector.py.
    Called on EVERY input transcript in real-time (< 1ms).
    """
    return detect_emergency(text)


def get_emergency_details(text: str) -> list[str]:
    """Get list of emergency keywords found. For UI display."""
    return get_emergency_keywords_found(text)


def extract_cultural_expressions(text: str) -> list[dict]:
    """Run cultural mapper on transcript text. Reuses existing CulturalMapper."""
    return _cultural_mapper.map_expressions(text)


async def run_post_session_safety(
    session: dict,
    transcript_log: list[dict],
    phi_deidentifier,
) -> dict:
    """Run full safety pipeline on accumulated voice transcripts AFTER session ends.

    This ensures all safety layers are applied even though Gemini Live
    processed the audio directly.

    Args:
        session: The in-memory session dict from _sessions
        transcript_log: List of {"role": "user"|"assistant", "text": str, "timestamp": str}
        phi_deidentifier: PHIDeidentifier instance from chat.py

    Returns:
        dict with safety results
    """
    user_texts = [t["text"] for t in transcript_log if t["role"] == "user" and t["text"]]
    full_user_text = " ".join(user_texts)

    results = {
        "is_emergency": False,
        "emergency_keywords": [],
        "cultural_expressions": [],
        "phi_detected": False,
        "deidentified_transcript": [],
    }

    if not full_user_text:
        return results

    # 1. Full emergency detection (reuse existing)
    results["is_emergency"] = detect_emergency(full_user_text)
    results["emergency_keywords"] = get_emergency_keywords_found(full_user_text)

    # 2. Cultural expression mapping (reuse existing)
    results["cultural_expressions"] = _cultural_mapper.map_expressions(full_user_text)

    # 3. PHI de-identification for medical records
    if phi_deidentifier:
        deidentified_log = []
        for entry in transcript_log:
            if entry["text"]:
                clean_text, mapping = phi_deidentifier.deidentify(entry["text"])
                deidentified_log.append({
                    "role": entry["role"],
                    "text": clean_text,
                    "timestamp": entry.get("timestamp", ""),
                    "had_phi": bool(mapping),
                })
                if mapping:
                    results["phi_detected"] = True
            else:
                deidentified_log.append(entry)
        results["deidentified_transcript"] = deidentified_log

    # 4. Update session
    session["is_emergency"] = session.get("is_emergency", False) or results["is_emergency"]
    session["cultural_expressions"] = results["cultural_expressions"]
    session["voice_transcripts"] = results.get("deidentified_transcript") or transcript_log

    logger.info(
        "voice_safety.post_session",
        is_emergency=results["is_emergency"],
        cultural_count=len(results["cultural_expressions"]),
        phi_detected=results["phi_detected"],
        total_turns=len(transcript_log),
    )

    return results
