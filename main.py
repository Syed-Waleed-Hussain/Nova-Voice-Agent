import os
import io
import re
import json
import base64
import logging
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from groq import AsyncGroq, Groq

import file_generator
import search_module

# -----------------------------------------------------------------------------
# Configuration & Setup
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("voice_agent")

# Attempt to read GROQ_API_KEY from environment or api.txt fallback
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
if not GROQ_API_KEY:
    api_txt_path = BASE_DIR / "api.txt"
    if api_txt_path.exists():
        try:
            GROQ_API_KEY = api_txt_path.read_text(encoding="utf-8").strip()
            logger.info("Loaded GROQ_API_KEY from api.txt fallback.")
        except Exception as e:
            logger.warning(f"Could not read api.txt: {e}")

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()
GROQ_WHISPER_MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo").strip()
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "en-US-ChristopherNeural").strip()
URDU_VOICE = "ur-PK-AsadNeural"

# Global cache for dynamically discovered Groq models
_discovered_models: List[str] = []

# Initialize FastAPI App
app = FastAPI(
    title="Nova Voice Assistant API",
    description="High-performance bidirectional voice and text AI assistant with Document Generation (PDF, PPTX, DOCX, XLSX, CSV) and strict Urdu script enforcement",
    version="2.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Directories: Static Files, Templates, and Downloads
static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
templates_dir = BASE_DIR / "templates"
templates_dir.mkdir(parents=True, exist_ok=True)
if os.environ.get("VERCEL"):
    downloads_dir = Path("/tmp/downloads")
else:
    downloads_dir = BASE_DIR / "downloads"

downloads_dir.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.mount("/downloads", StaticFiles(directory=str(downloads_dir)), name="downloads")


@app.get("/downloads/{filename}")
async def get_download_file(filename: str):
    """Direct route for downloading generated files (Vercel & local fallback)."""
    target = downloads_dir / filename
    if not target.exists():
        raise HTTPException(status_code=404, detail="Requested file was not found or has expired.")
    return FileResponse(target, filename=filename)

# -----------------------------------------------------------------------------
# Language Detection & Urdu Script Directives
# -----------------------------------------------------------------------------
URDU_SCRIPT_DIRECTIVE = (
    "\n\n[STRICT LANGUAGE & SCRIPT DIRECTIVE]:\n"
    "1. If the user speaks or writes in Urdu (or Roman Urdu), respond STRICTLY in Urdu language written in authentic Urdu script (اردو حروف و الفاظ).\n"
    "2. Under NO circumstances should you EVER output Hindi or Devanagari script (e.g., हिन्दी / देवनागरी). Hindi/Devanagari characters are strictly forbidden.\n"
    "3. Keep your spoken responses concise, pleasant, and natural for real-time voice conversation."
)


def is_urdu_text(text: str) -> bool:
    """Detects if text is in Urdu/Arabic script or Roman Urdu."""
    if not text:
        return False
    # Arabic/Urdu unicode range
    if re.search(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]", text):
        return True
    # Roman Urdu common signal words
    roman_urdu_words = {"aap", "kya", "hai", "hain", "humein", "banao", "kaise", "kijiye", "shukriya", "theek", "acha"}
    words = set(re.findall(r"\b\w+\b", text.lower()))
    return len(words.intersection(roman_urdu_words)) >= 2


def sanitize_no_devanagari(text: str) -> str:
    """Removes any inadvertent Devanagari characters from output."""
    if not text:
        return ""
    # Strip Devanagari Unicode range U+0900 to U+097F
    return re.sub(r"[\u0900-\u097F]+", "", text).strip()

# -----------------------------------------------------------------------------
# Personas & System Prompts
# -----------------------------------------------------------------------------
PERSONAS: Dict[str, Dict[str, Any]] = {
    "friendly": {
        "id": "friendly",
        "name": "Nova (Friendly Companion)",
        "voice": "en-US-ChristopherNeural",
        "urdu_voice": "ur-PK-AsadNeural",
        "tagline": "Warm, engaging, and conversational partner",
        "prompt": (
            "You are Nova, an intelligent, empathetic, and warm voice assistant. "
            "You communicate primarily via spoken voice and text. "
            "Keep your responses concise, natural, and conversational (1 to 3 short paragraphs). "
            "Avoid overly long monologues unless generating documents."
            + URDU_SCRIPT_DIRECTIVE
        )
    },
    "tech": {
        "id": "tech",
        "name": "Nexus (Tech & Systems Architect)",
        "voice": "en-US-ChristopherNeural",
        "urdu_voice": "ur-PK-AsadNeural",
        "tagline": "Senior engineer, architectural precision, sharp advice",
        "prompt": (
            "You are Nexus, a Principal Software Engineer and AI Systems Architect. "
            "Deliver authoritative, practical, and highly accurate technical answers. "
            "Explain concepts crisply for spoken conversation."
            + URDU_SCRIPT_DIRECTIVE
        )
    },
    "bilingual": {
        "id": "bilingual",
        "name": "Zara (Urdu/English Bilingual)",
        "voice": "ur-PK-UzmaNeural",
        "urdu_voice": "ur-PK-UzmaNeural",
        "tagline": "Fluent in English & pure Urdu script companion",
        "prompt": (
            "You are Zara, a courteous, highly articulate bilingual assistant fluent in both English and Urdu. "
            "If the user speaks or writes in Urdu or Roman Urdu, respond exclusively in pure Urdu language written in Urdu script (اردو حروف). "
            "NEVER use Hindi or Devanagari script. If the user speaks in English, respond in articulate English."
            + URDU_SCRIPT_DIRECTIVE
        )
    },
    "executive": {
        "id": "executive",
        "name": "Aura (Executive Strategist)",
        "voice": "en-GB-SoniaNeural",
        "urdu_voice": "ur-PK-UzmaNeural",
        "tagline": "Crisp, structured, priority-focused executive adviser",
        "prompt": (
            "You are Aura, an executive chief-of-staff and strategic adviser. "
            "Deliver high-impact, direct, bottom-line-first responses optimized for rapid voice briefings."
            + URDU_SCRIPT_DIRECTIVE
        )
    },
    "storyteller": {
        "id": "storyteller",
        "name": "Lyra (Creative Philosopher)",
        "voice": "en-GB-RyanNeural",
        "urdu_voice": "ur-PK-AsadNeural",
        "tagline": "Articulate, imaginative, philosophical storyteller",
        "prompt": (
            "You are Lyra, a creative storyteller and curious philosophical companion. "
            "Speak with evocative phrasing and thoughtful analogies."
            + URDU_SCRIPT_DIRECTIVE
        )
    }
}

AVAILABLE_VOICES = [
    {"id": "en-US-ChristopherNeural", "name": "Christopher (US English - Authoritative, Male)", "lang": "en-US", "gender": "Male"},
    {"id": "en-US-AriaNeural", "name": "Aria (US English - Expressive, Female)", "lang": "en-US", "gender": "Female"},
    {"id": "en-US-GuyNeural", "name": "Guy (US English - Confident, Male)", "lang": "en-US", "gender": "Male"},
    {"id": "ur-PK-AsadNeural", "name": "Asad (Urdu Pakistan - Authentic, Male)", "lang": "ur-PK", "gender": "Male"},
    {"id": "ur-PK-UzmaNeural", "name": "Uzma (Urdu Pakistan - Warm, Female)", "lang": "ur-PK", "gender": "Female"},
    {"id": "en-GB-SoniaNeural", "name": "Sonia (British English - Crisp, Female)", "lang": "en-GB", "gender": "Female"},
    {"id": "en-GB-RyanNeural", "name": "Ryan (British English - Rich, Male)", "lang": "en-GB", "gender": "Male"}
]

# -----------------------------------------------------------------------------
# Groq Client Helpers
# -----------------------------------------------------------------------------
def get_groq_async_client() -> AsyncGroq:
    key = os.getenv("GROQ_API_KEY", "").strip() or GROQ_API_KEY
    if not key:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY is missing. Please set it in your .env file or environment."
        )
    return AsyncGroq(api_key=key, timeout=20.0)


def get_groq_sync_client() -> Groq:
    key = os.getenv("GROQ_API_KEY", "").strip() or GROQ_API_KEY
    if not key:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY is missing. Please set it in your .env file or environment."
        )
    return Groq(api_key=key, timeout=30.0)


async def get_active_groq_models(client: AsyncGroq) -> List[str]:
    """Dynamically queries Groq API to discover which models are active for this account."""
    global _discovered_models
    if _discovered_models:
        return _discovered_models
    try:
        model_list = await client.models.list()
        chat_models = []
        for m in model_list.data:
            mid = m.id.lower()
            if any(skip in mid for skip in ["whisper", "guard", "embed", "vision"]):
                continue
            chat_models.append(m.id)
        if chat_models:
            _discovered_models = chat_models
            logger.info(f"Discovered {len(chat_models)} active Groq chat models: {_discovered_models}")
            return _discovered_models
    except Exception as e:
        logger.warning(f"Could not fetch dynamic models list: {e}")
    return []

# -----------------------------------------------------------------------------
# Text-to-Speech (TTS) Engine
# -----------------------------------------------------------------------------
def clean_markdown_for_speech(text: str) -> str:
    """Cleans markdown formatting and JSON blocks before sending to TTS."""
    if not text:
        return ""
    # Remove JSON or document data blocks
    text = re.sub(r"```(?:json|document_data)?[\s\S]*?```", "", text)
    # Remove inline code
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove markdown links [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove headers (#, ##)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold and italic (* or _)
    text = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", text)
    # Remove excessive whitespace
    text = re.sub(r"\n{2,}", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


async def generate_speech_base64(text: str, voice: str = DEFAULT_VOICE) -> Optional[str]:
    """
    Converts text to speech using Microsoft Edge-TTS with fallback to gTTS.
    Returns Base64 audio string (data:audio/mp3;base64,...).
    """
    cleaned_text = clean_markdown_for_speech(text)
    if not cleaned_text:
        return None

    # Detect if text is Urdu -> strictly enforce Urdu voice
    if is_urdu_text(cleaned_text):
        voice = URDU_VOICE

    # 1. Edge-TTS Primary
    try:
        import edge_tts
        communicate = edge_tts.Communicate(cleaned_text, voice)
        audio_stream = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_stream.write(chunk["data"])
        
        audio_bytes = audio_stream.getvalue()
        if audio_bytes:
            b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
            return f"data:audio/mp3;base64,{b64_audio}"
    except Exception as edge_err:
        logger.warning(f"Edge-TTS failed ({edge_err}), falling back to gTTS...")

    # 2. Fallback: gTTS
    try:
        from gtts import gTTS
        lang = "ur" if is_urdu_text(cleaned_text) else "en"
        tts = gTTS(text=cleaned_text[:600], lang=lang)
        fallback_stream = io.BytesIO()
        tts.write_to_fp(fallback_stream)
        audio_bytes = fallback_stream.getvalue()
        if audio_bytes:
            b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
            return f"data:audio/mp3;base64,{b64_audio}"
    except Exception as gtts_err:
        logger.error(f"gTTS fallback also failed: {gtts_err}")

    return None

# -----------------------------------------------------------------------------
# LLM Generation & Document Intent Processor
# -----------------------------------------------------------------------------
async def query_llm_response(
    user_prompt: str,
    persona_id: str = "friendly",
    custom_prompt: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
    doc_type: Optional[str] = None,
    search_context: Optional[str] = None
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Queries Groq LLM with persona system prompt, live web search context,
    and structured document instructions.
    Returns (conversational_text, parsed_document_data_dict_or_None).
    """
    client = get_groq_async_client()

    persona_info = PERSONAS.get(persona_id, PERSONAS["friendly"])
    system_instruction = custom_prompt if custom_prompt else persona_info["prompt"]

    # If live search context is available, inject it into the prompt
    if search_context:
        system_instruction += f"\n\n{search_context}"

    # If document creation is requested, augment system prompt
    if doc_type:
        system_instruction += (
            f"\n\n[DOCUMENT GENERATION DIRECTIVE]:\n"
            f"The user wants a {doc_type.upper()} file created for: '{user_prompt}'.\n"
            f"Your output MUST contain TWO parts:\n"
            f"1. A warm, natural conversational summary (1-2 sentences) confirming the document has been compiled.\n"
            f"2. A JSON block fenced with ```document_data containing structured content:\n"
            f"```document_data\n"
            f'{{\n'
            f'  "title": "Clear Document Title",\n'
            f'  "sections": [\n'
            f'    {{"heading": "Executive Summary", "body": "Comprehensive analysis..."}},\n'
            f'    {{"heading": "Core Insights", "bullets": ["Point A", "Point B", "Point C"]}}\n'
            f'  ],\n'
            f'  "headers": ["Metric", "Category", "Target", "Status"],\n'
            f'  "rows": [\n'
            f'    ["Revenue Growth", "Financial", "25%", "On Track"],\n'
            f'    ["System Efficiency", "Operations", "99.9%", "Verified"]\n'
            f'  ]\n'
            f'}}\n'
            f"```"
        )

    messages = [{"role": "system", "content": system_instruction}]

    if history:
        for msg in history[-8:]:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                if msg["role"] in ["user", "assistant"]:
                    messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_prompt})

    # Models priority list
    candidate_models = [
        GROQ_MODEL,
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        "llama-3.3-70b-specdec",
        "deepseek-r1-distill-llama-70b",
        "gemma2-9b-it",
        "mixtral-8x7b-32768"
    ]

    try:
        discovered = await get_active_groq_models(client)
        if discovered:
            candidate_models.extend(discovered)
    except Exception:
        pass

    candidate_models = list(dict.fromkeys(candidate_models))

    raw_response = ""
    for model_name in candidate_models:
        try:
            logger.info(f"Querying Groq LLM model: {model_name}")
            chat_completion = await client.chat.completions.create(
                messages=messages,
                model=model_name,
                temperature=0.6,
                max_tokens=900,
                top_p=0.9,
            )
            raw_response = chat_completion.choices[0].message.content.strip()
            if raw_response:
                break
        except Exception as e:
            logger.warning(f"Groq completion error with {model_name}: {str(e)[:100]}. Retrying...")
            await asyncio.sleep(0.15)

    if not raw_response:
        raise HTTPException(status_code=502, detail="Failed to generate response from Groq.")

    # Strict Urdu check: sanitize any Devanagari characters
    raw_response = sanitize_no_devanagari(raw_response)

    # Extract JSON document_data if present
    parsed_doc_data = None
    conversational_text = raw_response

    doc_match = re.search(r"```(?:document_data|json)?\s*(\{[\s\S]*?\})\s*```", raw_response)
    if doc_match:
        try:
            parsed_doc_data = json.loads(doc_match.group(1))
            # Strip the JSON block from the text response for clean vocalization
            conversational_text = raw_response[:doc_match.start()].strip()
            trailing = raw_response[doc_match.end():].strip()
            if trailing:
                conversational_text += "\n" + trailing
        except Exception as json_err:
            logger.warning(f"JSON parsing of document_data failed: {json_err}")

    if not conversational_text:
        conversational_text = f"Your {doc_type.upper() if doc_type else 'document'} has been generated successfully."

    return conversational_text, parsed_doc_data

# -----------------------------------------------------------------------------
# Whisper Transcription Helper
# -----------------------------------------------------------------------------
async def transcribe_audio_payload(audio_bytes: bytes, filename: str = "audio.webm", is_urdu: bool = False) -> str:
    """Transcribes audio bytes using Groq Whisper (whisper-large-v3-turbo)."""
    if not audio_bytes or len(audio_bytes) < 50:
        return ""

    client = get_groq_sync_client()
    ext = Path(filename).suffix or ".webm"
    temp_filename = f"speech_input{ext}"

    try:
        loop = asyncio.get_running_loop()
        def _transcribe():
            kwargs = {
                "file": (temp_filename, audio_bytes),
                "model": GROQ_WHISPER_MODEL,
                "response_format": "json",
                "temperature": 0.0
            }
            if is_urdu:
                kwargs["language"] = "ur"
            return client.audio.transcriptions.create(**kwargs)

        transcription = await loop.run_in_executor(None, _transcribe)
        text = getattr(transcription, "text", "") or ""
        # Sanitize any accidental Devanagari from Whisper
        return sanitize_no_devanagari(text.strip())
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Speech transcription failed via Groq Whisper: {str(e)}"
        )

# -----------------------------------------------------------------------------
# Request & Response Schemas
# -----------------------------------------------------------------------------
class ChatRequest(BaseModel):
    text: str
    voice_enabled: bool = True
    session_id: str = "default"
    persona: str = "friendly"
    custom_prompt: Optional[str] = None
    voice: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = []

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None

# -----------------------------------------------------------------------------
# API Endpoints
# -----------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = templates_dir / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h1>Voice Assistant Template Not Found</h1>", status_code=404)
    return FileResponse(index_file)


@app.get("/api/health")
async def health_check():
    key = os.getenv("GROQ_API_KEY", "").strip() or GROQ_API_KEY
    return {
        "status": "healthy",
        "groq_configured": bool(key),
        "groq_model": GROQ_MODEL,
        "whisper_model": GROQ_WHISPER_MODEL,
        "default_voice": DEFAULT_VOICE,
        "supported_documents": ["pdf", "pptx", "docx", "xlsx", "csv"],
        "urdu_script_enforced": True
    }


@app.get("/api/personas")
async def list_personas():
    return list(PERSONAS.values())


@app.get("/api/voices")
async def list_voices():
    return AVAILABLE_VOICES


@app.post("/api/chat")
async def chat_endpoint(payload: ChatRequest):
    """JSON chat endpoint with real-time web search, document generation & strict script enforcement."""
    user_text = payload.text.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Text message cannot be empty.")

    # 1. Detect Document Generation Intent
    doc_type = file_generator.detect_document_intent(user_text)

    # 2. Detect Live Web Search Intent & Retrieve Sources
    sources = []
    search_context = None
    if not doc_type and search_module.detect_search_intent(user_text):
        try:
            sources = search_module.perform_web_search(user_text, max_results=4)
            if sources:
                search_context = search_module.format_search_context(sources)
        except Exception as search_err:
            logger.warning(f"Web search error: {search_err}")

    # 3. Query Groq LLM
    text_response, doc_data = await query_llm_response(
        user_prompt=user_text,
        persona_id=payload.persona,
        custom_prompt=payload.custom_prompt,
        history=payload.history,
        doc_type=doc_type,
        search_context=search_context
    )

    # 4. Synthesize Document File if requested
    file_info = None
    if doc_type:
        try:
            file_info = file_generator.synthesize_document(doc_type, user_text, doc_data)
        except Exception as doc_err:
            logger.error(f"Error creating {doc_type} file: {doc_err}")

    # 5. Voice Synthesis
    audio_base64 = None
    if payload.voice_enabled:
        voice_to_use = payload.voice or PERSONAS.get(payload.persona, {}).get("voice", DEFAULT_VOICE)
        if is_urdu_text(text_response) or is_urdu_text(user_text):
            voice_to_use = URDU_VOICE
        audio_base64 = await generate_speech_base64(text_response, voice=voice_to_use)

    resp_data = {
        "transcribed_text": user_text,
        "text_response": text_response,
        "audio_base64": audio_base64,
        "sources": sources,
        "session_id": payload.session_id,
        "persona": payload.persona
    }
    if file_info:
        resp_data.update(file_info)

    return resp_data


@app.post("/api/transcribe")
async def transcribe_endpoint(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio payload received.")

    transcribed_text = await transcribe_audio_payload(audio_bytes, filename=file.filename or "audio.webm")
    return {"transcribed_text": transcribed_text}


@app.post("/api/voice-agent")
async def voice_agent_endpoint(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    voice_enabled: bool = Form(True),
    session_id: str = Form("default"),
    persona: str = Form("friendly"),
    custom_prompt: Optional[str] = Form(None),
    voice: Optional[str] = Form(None),
    history_json: Optional[str] = Form(None)
):
    """
    Unified Voice & Text Agent Pipeline:
    1. Transcribes incoming audio using Groq Whisper.
    2. Enforces Urdu script if Urdu is spoken or selected.
    3. Detects document intent & generates PDF/PPTX/DOCX/XLSX/CSV.
    4. Converts response to authentic neural audio.
    5. Returns unified payload with file download metadata.
    """
    transcribed_text = ""

    history = []
    if history_json:
        try:
            history = json.loads(history_json)
        except Exception:
            history = []

    is_urdu_session = (persona == "bilingual")

    # 1. Transcribe audio if provided
    if file is not None:
        audio_bytes = await file.read()
        if audio_bytes and len(audio_bytes) > 100:
            transcribed_text = await transcribe_audio_payload(
                audio_bytes,
                filename=file.filename or "audio.webm",
                is_urdu=is_urdu_session
            )

    if not transcribed_text and text:
        transcribed_text = text.strip()

    if not transcribed_text:
        return JSONResponse(
            status_code=200,
            content={
                "transcribed_text": "",
                "text_response": "I didn't catch any audio. Please hold the bot or microphone and try speaking again.",
                "audio_base64": None,
                "session_id": session_id,
                "persona": persona
            }
        )

    # 2. Detect Document Intent
    doc_type = file_generator.detect_document_intent(transcribed_text)

    # 3. Detect Web Search Intent & Retrieve Live Sources
    sources = []
    search_context = None
    if not doc_type and search_module.detect_search_intent(transcribed_text):
        try:
            sources = search_module.perform_web_search(transcribed_text, max_results=4)
            if sources:
                search_context = search_module.format_search_context(sources)
        except Exception as search_err:
            logger.warning(f"Web search error: {search_err}")

    # 4. Query Groq LLM
    text_response, doc_data = await query_llm_response(
        user_prompt=transcribed_text,
        persona_id=persona,
        custom_prompt=custom_prompt,
        history=history,
        doc_type=doc_type,
        search_context=search_context
    )

    # 5. Generate Document File
    file_info = None
    if doc_type:
        try:
            file_info = file_generator.synthesize_document(doc_type, transcribed_text, doc_data)
            logger.info(f"Synthesized {doc_type} document: {file_info.get('file_name')}")
        except Exception as doc_err:
            logger.error(f"Error generating document: {doc_err}")

    # 6. Synthesize Neural Audio
    audio_base64 = None
    if voice_enabled:
        voice_to_use = voice or PERSONAS.get(persona, {}).get("voice", DEFAULT_VOICE)
        if is_urdu_text(text_response) or is_urdu_text(transcribed_text) or is_urdu_session:
            voice_to_use = URDU_VOICE
        audio_base64 = await generate_speech_base64(text_response, voice=voice_to_use)

    response_payload = {
        "transcribed_text": transcribed_text,
        "text_response": text_response,
        "audio_base64": audio_base64,
        "sources": sources,
        "session_id": session_id,
        "persona": persona
    }
    if file_info:
        response_payload.update(file_info)

    return response_payload


@app.post("/api/tts")
async def tts_endpoint(payload: TTSRequest):
    if not payload.text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    voice = payload.voice or DEFAULT_VOICE
    if is_urdu_text(payload.text):
        voice = URDU_VOICE

    audio_base64 = await generate_speech_base64(payload.text, voice=voice)
    if not audio_base64:
        raise HTTPException(status_code=500, detail="Failed to synthesize speech.")

    return {"audio_base64": audio_base64}


# -----------------------------------------------------------------------------
# Main Execution Entrypoint
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting Voice Assistant server on http://localhost:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=False)
