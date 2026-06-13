# Obrolin 💬

**Conversation Cards for Couples** — A web app that generates AI-powered conversation prompts to spark meaningful talks between partners.

Built with FastAPI backend + LLM (9router/OpenAI-compatible), served with a dark-themed static frontend.

## How It Works

1. Open the web UI
2. Pick a topic or let the app choose randomly
3. The LLM generates a unique conversation card tailored for couples
4. Discuss, swipe, or generate another — quality time, no effort

## Tech Stack

| Layer | Stack |
|-------|-------|
| **Backend** | Python, FastAPI, uvicorn |
| **Frontend** | Vanilla HTML/CSS + JS |
| **LLM** | OpenAI-compatible API (9router or any provider) |
| **HTTP** | httpx for API calls |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set your LLM API key
export LLM_API_KEY="sk-xxx"
export LLM_BASE_URL="http://127.0.0.1:20128/v1"  # default: 9router
export LLM_MODEL="9router-cheap-flash-combo"       # default model

# Run
python runner.py
```

The app starts at **http://localhost:8765**

### Using `run.sh`

```bash
chmod +x run.sh
./run.sh
```

## Configuration (env vars)

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | — | API key for the LLM provider |
| `LLM_BASE_URL` | `http://127.0.0.1:20128/v1` | OpenAI-compatible endpoint |
| `LLM_MODEL` | `9router-cheap-flash-combo` | Model name to use |

## Project Structure

```
obrolin/
├── main.py          # FastAPI app — routes, LLM client, session mgmt
├── runner.py        # Bootstrap script (loads API key from Hermes config)
├── run.sh           # Shell launcher
├── requirements.txt # Python dependencies
├── static/
│   └── index.html   # SPA-style frontend
└── .gitignore
```

## TODO / Ideas

- [ ] More card categories (deep talk, fun, romantic)
- [ ] Save favorite cards
- [ ] Multi-language support
- [ ] PWA / mobile-friendly improvements
