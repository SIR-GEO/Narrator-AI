"""
Auto-run on first launch: Generate voice embeddings from Voice_Files
Runs automatically when main.py detects Voice_Files folder
"""

import os

# Auto-agree to Coqui license for non-commercial use (MUST be before TTS import)
os.environ["COQUI_TOS_AGREED"] = "1"

import torch
from TTS.api import TTS

if os.path.exists("voice_embeddings") and len(os.listdir("voice_embeddings")) > 0:
    print("Embeddings already exist, skipping setup")
    exit(0)

print("\nLoading XTTS model...")
from TTS.api import TTS
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
model = tts.synthesizer.tts_model
print("Model loaded")

os.makedirs("voice_embeddings", exist_ok=True)

# Voice mapping
voice_folders = {
    "Clarkson": "Voice_Files/Clarkson",
    "David Attenborough": "Voice_Files/David Attenborough",
    "Joanna Lumley": "Voice_Files/Joanna Lumlee",
    "John Cleese": "Voice_Files/John Cleese",
    "Judi Dench": "Voice_Files/Judi Dench",
    "James May": "Voice_Files/May",
    "Michael Caine": "Voice_Files/Michael Caine",
    "Morgan Freeman": "Voice_Files/Morgan Freeman",
    "Stephen Fry": "Voice_Files/Stephen Fry"
}

print(f"\nProcessing {len(voice_folders)} voices...")

for voice_name, folder_path in voice_folders.items():
    print(f"\n{voice_name}...", end=" ")
    
    if not os.path.exists(folder_path):
        print("folder not found")
        continue
    
    audio_files = []
    for ext in ['.mp3', '.mp4', '.wav', '.m4a']:
        audio_files.extend([
            os.path.join(folder_path, f) 
            for f in os.listdir(folder_path) 
            if f.lower().endswith(ext)
        ])
    
    if not audio_files:
        print("no audio files")
        continue
    
    audio_files = audio_files[:3]
    
    try:
        gpt_cond_latent, speaker_embedding = model.get_conditioning_latents(
            audio_path=audio_files,
            gpt_cond_len=30,
            gpt_cond_chunk_len=4,
            max_ref_length=60
        )
        
        safe_name = voice_name.replace(" ", "_")
        torch.save(gpt_cond_latent, f"voice_embeddings/{safe_name}_gpt.pth")
        torch.save(speaker_embedding, f"voice_embeddings/{safe_name}_speaker.pth")
        
        with open(f"voice_embeddings/{safe_name}_info.txt", "w") as f:
            f.write(f"{voice_name}\n{len(audio_files)} files\n")
        
        print("done")
        
    except Exception as e:
        print(f"error: {str(e)}")

print("\n" + "=" * 50)
print("COMPLETE!")
embedding_count = len([f for f in os.listdir("voice_embeddings") if f.endswith("_gpt.pth")])
print(f"{embedding_count} embeddings created")
print("\nChange startup to: python main.py")
print("=" * 50)

