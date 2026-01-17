from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from narrate_description import router as narrate_description_router
from convert_text_to_speech import get_tts_model, preload_all_embeddings, warm_up_tts, is_tts_ready

import os

app = FastAPI()

# Add CORS middleware to allow WebSocket connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(narrate_description_router)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/templates", StaticFiles(directory="templates"), name="templates")

@app.get("/", response_class=HTMLResponse)
async def get_root(request: Request):
    return FileResponse("templates/main.html")

@app.get("/health")
async def health():
    return {"ready": is_tts_ready()}

# Pre-load TTS model and embeddings at startup
print("Pre-loading XTTS model and voice embeddings...")
try:
    get_tts_model()
    print("XTTS model pre-loaded!")
    preload_all_embeddings()
    print("All voice embeddings pre-loaded and ready!")
    warm_up_tts()
    print("XTTS warm-up complete!")
except Exception as e:
    print(f"Failed to pre-load: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
