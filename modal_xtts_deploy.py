"""
Deploy XTTS model to Modal Labs for free GPU TTS
Run: modal deploy modal_xtts_deploy.py
Then set MODAL_API_URL to the endpoint URL shown
"""

import modal
import io
import base64
import os

# Note: TTS and torch will be installed in Modal's container, not needed locally

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg")
    .pip_install(
        "TTS==0.22.0",
        "torch==2.2.0",
        "torchaudio==2.2.0",
        "transformers==4.38.0",
        "numpy==1.24.3",
        "scipy==1.11.4",
        "fastapi==0.110.0",
        "pydantic==2.5.0",
    )
)

app = modal.App("xtts-tts-api")

# Persist model downloads between runs to avoid cold-start re-downloads
tts_cache = modal.Volume.from_name("xtts-model-cache", create_if_missing=True)

@app.cls(
    image=image,
    gpu="T4",  # Cheapest GPU option on Modal's free tier
    scaledown_window=100,  # Keep warm for 2 minutes
    timeout=300,
    volumes={"/root/.local/share/tts": tts_cache},
)
class XTTSModel:
    @modal.enter()
    def load_model(self):
        """Load XTTS model on container startup"""
        # Import here (inside container, not locally)
        import torch
        from TTS.api import TTS
        import os
        os.environ["COQUI_TOS_AGREED"] = "1"
        
        print("Loading XTTS model on GPU...")
        self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cuda")
        print("XTTS model loaded!")
        try:
            # Persist downloaded model files for future runs
            tts_cache.commit()
        except Exception:
            pass
    
    @modal.method()
    def tts(self, text: str, language: str = "en", embedding: dict = None):
        """
        Generate speech from text using XTTS with optional voice embedding
        
        Args:
            text: Text to convert to speech
            language: Language code (default: "en")
            embedding: Dict with 'gpt_cond_latent' and 'speaker_embedding' (lists/tensors)
        
        Returns:
            Base64 encoded audio bytes
        """
        # Import here (inside container)
        import torch
        import torchaudio
        
        try:
            # Convert embedding lists back to tensors if needed
            if embedding:
                import numpy as np
                gpt_cond = torch.tensor(embedding['gpt_cond_latent']).to("cuda")
                speaker_emb = torch.tensor(embedding['speaker_embedding']).to("cuda")
                
                # Use pre-computed embedding
                wav = self.tts.synthesizer.tts_model.inference(
                    text=text,
                    language=language,
                    gpt_cond_latent=gpt_cond,
                    speaker_embedding=speaker_emb
                )
                wav = wav["wav"]
            else:
                # Use default voice
                wav = self.tts.tts(text=text, language=language)
            
            # Convert to bytes
            if not isinstance(wav, torch.Tensor):
                wav = torch.FloatTensor(wav)
            if wav.dim() == 1:
                wav = wav.unsqueeze(0)
            
            # Save to buffer as WAV
            buffer = io.BytesIO()
            torchaudio.save(buffer, wav.cpu(), 24000, format="wav")
            audio_bytes = buffer.getvalue()
            
            return {"audio": base64.b64encode(audio_bytes).decode("utf-8")}
            
        except Exception as e:
            return {"error": str(e)}


@app.function(
    image=image,
)
@modal.asgi_app()
def fastapi_app():
    """FastAPI app for TTS endpoint"""
    from fastapi import FastAPI
    from pydantic import BaseModel
    
    class TTSRequest(BaseModel):
        text: str
        language: str = "en"
        voice_name: str = None
        embedding: dict = None
    
    web_app = FastAPI()
    
    @web_app.post("/")
    async def tts_endpoint(request: TTSRequest):
        """Web endpoint for TTS - accepts POST requests"""
        model = XTTSModel()
        result = model.tts.remote(
            text=request.text,
            language=request.language,
            embedding=request.embedding
        )
        return result
    
    return web_app
