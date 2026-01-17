import os

# Auto-agree to Coqui license for non-commercial use (MUST be before TTS import)
os.environ["COQUI_TOS_AGREED"] = "1"

import io
import torch
import torchaudio
from TTS.api import TTS
import asyncio

# Voice to folder mapping
VOICE_FOLDERS = {
    "Clarkson": "Voice_Files/Clarkson",
    "David Attenborough": "Voice_Files/David Attenborough",
    "Joanna Lumley": "Voice_Files/Joanna Lumlee",
    "John Cleese": "Voice_Files/John Cleese",
    "Judi Dench": "Voice_Files/Judi Dench",
    "James May": "Voice_Files/May",
    "Michael Caine": "Voice_Files/Michael Caine",
    "Morgan Freeman": "Voice_Files/Morgan Freeman",
    "Stephen Fry": "Voice_Files/Stephen Fry",
}

VOICE_DISPLAY_NAMES = [
    "Clarkson",
    "David Attenborough",
    "James May",
    "John Cleese",
    "Michael Caine",
    "Morgan Freeman",
    "Joanna Lumley",
    "Judi Dench",
    "Stephen Fry",
]

_tts_model = None
_embeddings_cache = {}
_embeddings_preloaded = False
_tts_ready = False

def get_tts_model():
    global _tts_model
    if _tts_model is None:
        print("Loading XTTS model...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cpu":
            # Optimise for 2 vCPU on HF free tier
            torch.set_num_threads(2)
            torch.set_num_interop_threads(1)
        _tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
        print(f"Model loaded on {device}")
    return _tts_model

def warm_up_tts():
    """Run a tiny inference to warm up the model."""
    global _tts_ready
    try:
        tts = get_tts_model()
        if not _embeddings_cache:
            print("Warm-up skipped: no embeddings loaded yet")
            _tts_ready = False
            return
        voice_name = next(iter(_embeddings_cache.keys()))
        embedding = _embeddings_cache[voice_name]
        _ = tts.synthesizer.tts_model.inference(
            text="Hi.",
            language="en",
            gpt_cond_latent=embedding['gpt_cond_latent'],
            speaker_embedding=embedding['speaker_embedding']
        )
        _tts_ready = True
    except Exception as e:
        print(f"Warm-up failed: {e}")
        _tts_ready = False

def is_tts_ready():
    return _tts_ready

def preload_all_embeddings():
    """Preload all voice embeddings at startup for faster access"""
    global _embeddings_cache, _embeddings_preloaded
    
    if _embeddings_preloaded:
        return
    
    print("Preloading all voice embeddings...")
    embeddings_dir = "voice_embeddings"
    
    if not os.path.exists(embeddings_dir):
        print("No embeddings directory found")
        return
    
    # Find all voice embeddings
    gpt_files = [f for f in os.listdir(embeddings_dir) if f.endswith("_gpt.pth")]
    
    for gpt_file in gpt_files:
        voice_name = gpt_file.replace("_gpt.pth", "").replace("_", " ")
        safe_name = voice_name.replace(" ", "_")
        
        gpt_path = f"{embeddings_dir}/{safe_name}_gpt.pth"
        speaker_path = f"{embeddings_dir}/{safe_name}_speaker.pth"
        
        if os.path.exists(speaker_path):
            try:
                embedding = {
                    'gpt_cond_latent': torch.load(gpt_path, map_location='cpu'),
                    'speaker_embedding': torch.load(speaker_path, map_location='cpu')
                }
                _embeddings_cache[voice_name] = embedding
                print(f"  Preloaded: {voice_name}")
            except Exception as e:
                print(f"  Failed: {voice_name} - {e}")
    
    _embeddings_preloaded = True
    print(f"Preloaded {len(_embeddings_cache)} voice embeddings")

def load_voice_embedding(voice_name):
    """Load voice embedding (from cache if preloaded)"""
    global _embeddings_cache
    
    # Return from cache if available
    if voice_name in _embeddings_cache:
        return _embeddings_cache[voice_name]
    
    # Try to load from disk
    safe_name = voice_name.replace(" ", "_")
    gpt_path = f"voice_embeddings/{safe_name}_gpt.pth"
    speaker_path = f"voice_embeddings/{safe_name}_speaker.pth"
    
    if os.path.exists(gpt_path) and os.path.exists(speaker_path):
        try:
            embedding = {
                'gpt_cond_latent': torch.load(gpt_path, map_location='cpu'),
                'speaker_embedding': torch.load(speaker_path, map_location='cpu')
            }
            print(f"Loaded embedding for {voice_name}")
            _embeddings_cache[voice_name] = embedding
            return embedding
        except Exception as e:
            print(f"Failed to load embedding: {e}")
    
    return None

def get_voice_asset_status(voice_name):
    """Return readiness status for a voice based on available assets."""
    safe_name = voice_name.replace(" ", "_")
    gpt_path = f"voice_embeddings/{safe_name}_gpt.pth"
    speaker_path = f"voice_embeddings/{safe_name}_speaker.pth"
    has_embedding = os.path.exists(gpt_path) and os.path.exists(speaker_path)
    has_voice_files = voice_name in VOICE_FOLDERS and os.path.exists(VOICE_FOLDERS[voice_name])

    if has_embedding:
        return "ready"
    if has_voice_files:
        return "partial"
    return "missing"

def get_voice_statuses():
    """Return status for each voice button."""
    return {voice_name: get_voice_asset_status(voice_name) for voice_name in VOICE_DISPLAY_NAMES}

def get_voice_files(voice_name):
    folder = VOICE_FOLDERS.get(voice_name, "Voice_Files/David Attenborough")
    if not os.path.exists(folder):
        return ["Voice_Files/David Attenborough/david 1a.mp3"]
    
    files = []
    for ext in ['.mp3', '.mp4', '.wav', '.m4a']:
        files.extend([os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(ext)])
    
    return files[:3] if files else ["Voice_Files/David Attenborough/david 1a.mp3"]

async def convert_text_to_speech(text, voice_name):
    try:
        print(f"Generating speech: {voice_name}")
        
        loop = asyncio.get_event_loop()
        
        def generate():
            import time
            start = time.time()
            
            tts = get_tts_model()
            embedding = load_voice_embedding(voice_name)
            
            if embedding:
                print("Using pre-computed embedding")
                # Use synthesizer directly with pre-computed embeddings
                wav = tts.synthesizer.tts_model.inference(
                    text=text,
                    language="en",
                    gpt_cond_latent=embedding['gpt_cond_latent'],
                    speaker_embedding=embedding['speaker_embedding']
                )
                wav = wav["wav"]
            else:
                print("Computing embedding on-the-fly")
                voice_files = get_voice_files(voice_name)
                print(f"Using {len(voice_files)} voice file(s)")
                
                wav = tts.tts(
                    text=text,
                    speaker_wav=voice_files,
                    language="en",
                    split_sentences=False
                )
            
            print(f"Generated in {time.time() - start:.1f}s")
            return wav
        
        wav = await loop.run_in_executor(None, generate)
        
        # Convert to MP3
        if not isinstance(wav, torch.Tensor):
            wav = torch.FloatTensor(wav)
        if wav.dim() == 1:
            wav = wav.unsqueeze(0)
        
        buffer = io.BytesIO()
        try:
            # Try saving as MP3
            torchaudio.save(buffer, wav, 24000, format="mp3")
        except (ImportError, RuntimeError):
            # Fallback: save as WAV first, then convert
            import scipy.io.wavfile as wavfile
            import numpy as np
            wav_np = wav.cpu().numpy()
            if wav_np.ndim > 1:
                wav_np = wav_np[0]  # Take first channel if stereo
            # Normalise to int16 range
            wav_np = np.int16(wav_np / np.max(np.abs(wav_np)) * 32767)
            wavfile.write(buffer, 24000, wav_np)
            buffer.seek(0)
        audio_data = buffer.getvalue()
        
        # Send as a single chunk to avoid stutter
        yield audio_data
            
    except Exception as e:
        print(f"TTS error: {e}")
        import traceback
        traceback.print_exc()

