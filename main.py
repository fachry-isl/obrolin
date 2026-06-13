"""
Obrolin — Conversation Cards for Couples
Backend: FastAPI + 9router (OpenAI-compatible) LLM
"""

import json
import logging
import os
import random
import uuid
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Setup logging to file
logging.basicConfig(
    filename="/tmp/obrolin.log",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("obrolin")

app = FastAPI(title="Obrolin")

# --- Config ---
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:20128/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "9router-cheap-flash-combo")
# API key for 9router OpenAI-compatible endpoint
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
log.info(f"Config: base_url={LLM_BASE_URL} model={LLM_MODEL} key_len={len(LLM_API_KEY)}")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8765"))
STATIC_DIR = Path(__file__).parent / "static"

# --- Question tracking ---
# session_id -> set of questions seen
_sessions: dict[str, set[str]] = {}
# Cache last N generated questions globally (to avoid repeats across sessions too)
_generated_cache: list[str] = []

# --- Fallback questions if Ollama is unavailable ---
FALLBACK_QUESTIONS = [
    # Deep Talk
    ("Apa satu hal tentang dirimu yang berubah sejak kita pacaran?", "Deep Talk"),
    ("Kalau bisa satu hari jadi orang lain, siapa yang mau kamu jadiin dan kenapa?", "Deep Talk"),
    ("Apa ketakutan terbesarmu dalam hubungan ini?", "Deep Talk"),
    ("Menurutmu, apa bahasa cinta yang paling kamu rasakan dari aku?", "Deep Talk"),
    ("Apa yang paling kamu syukuri dari hubungan kita?", "Deep Talk"),
    # Fun
    ("Kalau bisa punya hewan eksotis peliharaan, mau apa?", "Fun"),
    ("Apa film atau series yang bisa kamu tonton berkali-kali tanpa bosen?", "Fun"),
    ("Kalau besok adalah hari terakhir di bumi, apa yang mau kita lakuin bareng?", "Fun"),
    ("Apa makanan paling aneh yang pernah kamu cobain dan ternyata enak?", "Fun"),
    ("Kalau kita tukar badan sehari, apa hal pertama yang bakal kamu lakuin?", "Fun"),
    # Future
    ("Menurutmu, kita bakal kayak gimana 5 tahun dari sekarang?", "Future & Dreams"),
    ("Tempat mana yang paling pengen kamu kunjungin bareng aku?", "Future & Dreams"),
    ("Kalau menang lotre, mimpi apa yang pertama bakal kamu kejar?", "Future & Dreams"),
    ("Apa satu skill yang pengen kamu kuasain tahun ini?", "Future & Dreams"),
    ("Menurutmu, apa definisi 'sukses' buat kita berdua?", "Future & Dreams"),
    # Relationship
    ("Momen apa yang bikin kamu makin yakin sama hubungan ini?", "Relationship"),
    ("Apa kebiasaan kecilku yang paling kamu suka?", "Relationship"),
    ("Menurutmu, apa yang bikin hubungan kita beda dari yang lain?", "Relationship"),
    ("Apa satu hal yang pengen kamu perbaikin dari cara kita berkomunikasi?", "Relationship"),
    ("Kapan terakhir kali kamu merasa 'I'm so lucky to have them'?", "Relationship"),
    # Childhood & Memories
    ("Apa kenangan masa kecil paling bahagia yang pernah kamu alamin?", "Childhood"),
    ("Siapa orang yang paling berpengaruh dalam hidup kamu waktu kecil?", "Childhood"),
    ("Apa hal paling kocak yang pernah kamu lakuin pas kecil?", "Childhood"),
    ("Kalau bisa balik ke masa lalu, momen apa yang mau kamu ulang?", "Childhood"),
    ("Apa lagu atau film yang langsung bikin kamu nostalgia?", "Childhood"),
    # Random / Deep
    ("Apa prinsip hidup yang nggak akan pernah kamu kompromiin?", "Life & Values"),
    ("Kalau bisa kirim pesan ke diri kamu 10 tahun lalu, apa yang bakal kamu bilang?", "Life & Values"),
    ("Apa hal yang kamu pengen aku ngerti lebih dalam tentang diri kamu?", "Life & Values"),
    ("Menurutmu, apa superpower yang kita punya sebagai pasangan?", "Life & Values"),
    ("Apa pertanyaan yang kamu takut tanyain ke aku tapi penasaran?", "Life & Values"),
]

CATEGORIES = [
    "Deep Talk", "Fun", "Future & Dreams", "Relationship",
    "Childhood", "Life & Values", "Adventure", "Romance",
]

# --- Helpers ---

def _get_session_id(request: Request) -> str:
    """Get or create session ID from cookie."""
    sid = request.cookies.get("obrolin_session")
    if not sid or sid not in _sessions:
        sid = str(uuid.uuid4())
        _sessions[sid] = set()
    return sid



async def _generate_question_llm(category: str, seen_count: int) -> str | None:
    """Generate a question via 9router (always streams SSE)."""
    system_prompt = """Kamu adalah asisten yang membantu pasangan kekasih saling kenal lebih dalam.
Tugasmu: buat SATU pertanyaan obrolan untuk pasangan dalam Bahasa Indonesia yang natural, hangat, dan personal.

Aturan:
- 1 pertanyaan saja, langsung pertanyaannya, tanpa nomor, tanpa penjelasan
- Gaya santai, personal, relatable, kadang lucu kadang deep
- Hindari pertanyaan klise/generik
- Pertanyaan harus memancing cerita dan obrolan seru
- Dalam bentuk "kamu" ke pasangan ("Apa yang membuatmu...")
- Variasikan setiap kali, jangan ulang pola pertanyaan yang sama"""

    user_prompt = f"""Kategori: {category}
Ini pertanyaan ke-{seen_count + 1} — pastikan fresh dan belum biasa ditanyain sehari-hari.
Buat 1 pertanyaan obrolan untuk pasangan:"""

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.9,
        "max_tokens": 2048,
        "top_p": 0.9,
    }
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{LLM_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            full_body = resp.content
            raw_text = full_body.decode("utf-8", errors="replace")
            log.info(f"Response ({len(raw_text)} chars): {raw_text[:400]}")

            # Parse SSE or JSON
            content = ""
            reasoning = ""

            # Extract first complete JSON object (handle SSE extra data)
            if "{" in raw_text:
                start = raw_text.index("{")
                depth = 0
                for i, c in enumerate(raw_text[start:]):
                    if c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                        if depth == 0:
                            try:
                                data = json.loads(raw_text[start:start+i+1])
                                choice = data["choices"][0]
                                msg = choice.get("message", {})
                                content = (msg.get("content") or "")
                                reasoning = (msg.get("reasoning_content") or "")
                            except (json.JSONDecodeError, KeyError, IndexError) as e:
                                log.warning(f"JSON parse failed: {e}")
                            break

        # Use content first, fallback to reasoning_content
        text = (content or reasoning or "").strip()
        log.info(f"SSE collected: len={len(text)} first_80=[{text[:80]}]")

        # Clean artifacts
        text = text.strip('"').strip("'").strip()
        for prefix in ["Pertanyaan:", "Q:", "Question:", "1.", "1)", "- "]:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
        if text and len(text) > 15:
            log.info(f"✅ Generated [{category}]: {text[:60]}...")
            return text
    except Exception as e:
        log.error(f"9router error: {e}")
        if isinstance(e, httpx.HTTPStatusError):
            log.error(f"Body: {e.response.text[:300]}")
    return None


def _get_fallback_question(exclude: set[str]) -> tuple[str, str]:
    """Get a random fallback question, excluding seen ones."""
    available = [(q, c) for q, c in FALLBACK_QUESTIONS if q not in exclude]
    if not available:
        # Reset if all used
        available = list(FALLBACK_QUESTIONS)
    return random.choice(available)


# --- API Routes ---

@app.get("/api/question")
async def get_question(request: Request):
    """Get a unique new question, generated via LLM."""
    sid = _get_session_id(request)
    seen = _sessions[sid]

    # Pick a random category that hasn't been used too much in this session
    category = random.choice(CATEGORIES)

    # Try 9router LLM
    question = await _generate_question_llm(category, len(seen))

    # Fallback if LLM failed
    if not question or question in seen:
        fb_question, fb_category = _get_fallback_question(seen)
        question = fb_question
        category = fb_category

    # Mark as seen
    seen.add(question)

    # Build response
    response_data = {
        "question": question,
        "category": category,
        "total_seen": len(seen),
    }

    resp = JSONResponse(response_data)
    resp.set_cookie(key="obrolin_session", value=sid, max_age=86400 * 7, httponly=True)
    return resp


@app.post("/api/reset")
async def reset_session(request: Request):
    """Reset the session's seen questions."""
    sid = _get_session_id(request)
    _sessions[sid] = set()
    return {"status": "ok", "message": "Session reset. Ready for fresh questions!"}


@app.get("/api/history")
async def get_history(request: Request):
    """Get list of questions seen this session."""
    sid = _get_session_id(request)
    seen = list(_sessions.get(sid, set()))
    return {"history": seen, "count": len(seen)}


# --- Health check ---

@app.get("/api/health")
async def health():
    """Check if 9router LLM is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{LLM_BASE_URL}/models", timeout=5.0)
            data = resp.json()
            models = data.get("data", [])
            return {
                "status": "ok",
                "llm": True,
                "model": LLM_MODEL,
                "model_available": any(m["id"] == LLM_MODEL for m in models),
            }
    except Exception as e:
        return {"status": "degraded", "llm": False, "error": str(e)}


# --- Serve frontend ---

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


# --- Entry ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
    # When run via runner.py, runner.py handles uvicorn directly
