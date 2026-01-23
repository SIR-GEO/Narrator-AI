### Available to play with for free: https://huggingface.co/spaces/Mr-Geo/ai-narrator

# Narrator-AI

AI Image Narrator: capture images from your camera, get a short description, and hear it in a cloned voice.

## Tech Stack

- **UI**: FastAPI with custom HTML/JS (camera-based)
- **Backend**: Python (FastAPI)
- **TTS**: Coqui XTTS‑v2 (voice cloning)
- **Vision/LLM**: Anthropic (image description)
- **Real-time**: WebSocket for streaming narration

## Setup

1. Install dependencies:
   - `pip install -r requirements.txt`
2. Set environment variables:
   - `ANTHROPIC_API_KEY`
3. Run:
   - `python main.py` or `uvicorn main:app --host 0.0.0.0 --port 7860`

## Notes

- XTTS‑v2 runs on CPU in HF free tier and can take 1–3 minutes for longer text.
- Embeddings are preloaded at startup for faster cloning.
- Camera access requires HTTPS (automatically provided by HuggingFace Spaces).

