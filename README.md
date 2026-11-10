# 🎙️ NOVA 2.0 — Real-Time Voice Assistant, Web Search & Document Engine

A high-performance Full-Stack Voice Assistant featuring:
- **Interactive 3D Floating Bot Orb** with Web Audio API frequency waveform visualizer.
- **Real-Time Web Search & Source Retrieval** via DuckDuckGo Search (free/keyless) and optional Tavily API.
- **Clickable Source Citation Cards** with title, domain, and direct URL opening.
- **Multi-Format Document Generator** (PDF, PPTX, DOCX, XLSX, CSV).
- **Strict Urdu Script Fidelity** (100% Urdu script, NEVER Hindi/Devanagari).
- **Dual Voice & Text Interaction** with auto-playback of neural audio streams.

---

## ⚡ Quickstart Guide

### 1. Install Dependencies
Ensure you have Python 3.9+ installed, then install all requirements:

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
A [`.env`](file:///d:/Self%20Progress/Python%20for%20AI/Week%2009/Voice%20Agent/.env) file is pre-configured with your Groq API key:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
GROQ_WHISPER_MODEL=whisper-large-v3-turbo
DEFAULT_VOICE=en-US-ChristopherNeural
TAVILY_API_KEY=
HOST=127.0.0.1
PORT=8000
```

> **Note on Web Search**: DuckDuckGo search is active by default with zero configuration or keys required! If you have a Tavily API key, you can optionally paste it in `TAVILY_API_KEY=`.

### 3. Launch the Application Server
Run the FastAPI application with Uvicorn:

```powershell
uvicorn main.py --reload
```
or run directly via Python:
```powershell
python main.py
```

### 4. Open in Your Browser
Visit:
```
http://localhost:8000
```
*(Allow microphone permissions when prompted by your browser).*

---

## 🌟 Key Capabilities & Workflows

### 1. Real-Time Web Search & Source Citation Cards
Nova automatically detects when your query requires live web information, recent news, current events, or factual verification:
- **Zero-Key Search**: Powered by `duckduckgo-search` (with fallback to Tavily).
- **Context Injection**: Live search snippets are supplied directly to Groq Llama 3.1 to answer with up-to-the-minute accuracy.
- **Interactive Citation Chips**: Every web-assisted response renders clickable source chips under the chat bubble showing the page title, domain, and direct link (`target="_blank"`), plus a live notification below the central Bot.

**Try saying or typing:**
- *"Search the web for the latest artificial intelligence breakthroughs"*
- *"What is the latest news on SpaceX Starship?"*
- *"Who is the current Prime Minister of the UK?"*
- *"تازہ ترین بین الاقوامی خبریں تلاش کرو"*

---

### 2. Document Generation Engine (PDF, PPTX, DOCX, XLSX, CSV)
Trigger document generation directly via voice or text:
- **PDF Reports (`reportlab`)**: Styled executive documents with headers, paragraphs, bullet points, and data tables.
- **PowerPoint Decks (`python-pptx`)**: 16:9 modern dark-theme slide decks with title slides and strategic bullet cards.
- **Word Documents (`python-docx`)**: Clean business documents with styled headings and structured lists.
- **Excel Spreadsheets (`openpyxl` / `pandas`)**: Styled workbooks with purple header banners, alternate row fills, and formatted numbers.
- **CSV Data (`csv` / `pandas`)**: Comma-separated structured datasets.

**Try saying or typing:**
- *"Create a PDF report on Quantum Computing"*
- *"Generate a PPT presentation for an AI startup pitch deck"*
- *"Make an Excel sheet for 2026 marketing budget"*
- *"Create a Word document outlining project milestones"*
- *"ایک پی ڈی ایف رپورٹ بناؤ مصنوعی ذہانت پر"*

When generated, an interactive **Glassmorphic File Download Card** appears in the chat drawer and beneath the central Bot with a single-click direct download button.

---

### 3. Strict Urdu Script & Language Enforcement
- **100% Urdu Script Guarantee (اردو حروف و الفاظ)**: When interacting in Urdu (spoken or written), Nova responds strictly in authentic Urdu script.
- **Devanagari/Hindi Elimination**: Whisper transcripts and LLM generation are strictly monitored and sanitized to eliminate Hindi/Devanagari characters.
- **Authentic Neural Voices**: Automatically speaks using authentic Urdu neural voices (`ur-PK-AsadNeural` or `ur-PK-UzmaNeural`).

---

### 4. Centered Floating Bot Orb & Live Frequency Visualizer
- **Center Floating Orb**: Positioned dead-center with 3D hovering animations (`floatOrb`).
- **Click-to-Talk**: Click the central Bot or tap the microphone button or press <kbd>Spacebar</kbd> to toggle speech recording.
- **State Machine Reactivity**:
  - **`Idle`**: Soft breathing neon glow (Violet/Cyan pulse) with orbiting cosmic particles.
  - **`Listening`**: Real-time microphone audio frequency spectrum expanding outward via Web Audio API `AnalyserNode`.
  - **`Thinking`**: Fast rotating halo rings and particle shimmer while Groq synthesizes response.
  - **`Speaking`**: Dynamic sound-wave frequency expansion synchronizing with the AI voice amplitude.

---

### 5. Hands-Free Auto-Talk Mode
Toggle **"Hands-Free"** in the top navigation bar. Once Nova finishes speaking, the microphone re-opens automatically after a 400ms pause for uninterrupted hands-free voice dialogue.

---

## 📁 Project Architecture

```
Voice Agent/
├── .env                  # Groq API key, models, search key
├── .env.example          # Environment template
├── requirements.txt      # Core + search + document libraries
├── main.py               # FastAPI backend with search intent & document engine
├── search_module.py      # Real-time web search engine (DuckDuckGo + Tavily)
├── file_generator.py     # Document synthesis engine (PDF, PPTX, DOCX, XLSX, CSV)
├── downloads/            # Local directory serving generated document files
├── static/
│   ├── app.js            # AudioEngine, Web Audio visualizer, Download card & Citations renderer
│   └── style.css         # Glassmorphism styling, file cards, source chips, Urdu font
├── templates/
│   └── index.html        # Single-page interface with central Bot & sliding drawer
└── README.md             # Complete documentation
```

---

## 📡 Backend API Endpoints

### `POST /api/voice-agent`
Unified voice pipeline accepting `multipart/form-data`:
- **Parameters**: `file`, `text`, `voice_enabled`, `persona`, `voice`, `history_json`.
- **Returns**:
  ```json
  {
    "transcribed_text": "Search the web for AI breakthroughs",
    "text_response": "Recent breakthroughs in AI include...",
    "audio_base64": "data:audio/mp3;base64,...",
    "sources": [
      {
        "title": "MIT Technology Review - AI in 2026",
        "url": "https://technologyreview.com/...",
        "snippet": "Researchers unveiled new autonomous agent architectures..."
      }
    ],
    "file_url": null,
    "session_id": "default",
    "persona": "friendly"
  }
  ```

### `POST /api/chat`
JSON endpoint for text interactions with search, document generation, and TTS support.

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| <kbd>Spacebar</kbd> | Toggle Voice Recording (when not typing in textarea) |
| <kbd>Enter</kbd> | Send text message in input bar |
| <kbd>Shift + Enter</kbd> | Insert new line in textarea |
| <kbd>Escape</kbd> | Close sliding chat drawer / settings modal |

---

## 🛡️ License
MIT License. Free for personal and commercial development.
