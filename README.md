### Available to play with for free: https://huggingface.co/spaces/Mr-Geo/ai-narrator

# Narrator-AI

AI Image Narrator: upload an image, get a short description, and hear it in a cloned voice.

## Tech Stack

- **UI**: Gradio
- **Backend**: Python
- **TTS**: Coqui XTTS‑v2 (voice cloning)
- **Vision/LLM**: Anthropic (image description)

## Setup

1. Install dependencies:
   - `pip install -r requirements.txt`
2. Set environment variables:
   - `ANTHROPIC_API_KEY`
3. Run:
   - `python app.py`

## Notes

- XTTS‑v2 runs on CPU in HF free tier and can take 1–3 minutes for longer text.
- Embeddings are preloaded at startup for faster cloning.

