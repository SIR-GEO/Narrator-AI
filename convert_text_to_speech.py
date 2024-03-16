from elevenlabs.client import ElevenLabs
import os
import httpx

ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')

elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

async def convert_text_to_speech(text, selected_voice_id):
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{selected_voice_id}/stream",
                json={
                    "model_id": "eleven_monolingual_v1",
                    "text": text,
                    "output_format": "mp3_44100_128"
                },
                headers={
                    "Content-Type": "application/json",
                    "xi-api-key": ELEVENLABS_API_KEY
                },
                timeout=None
            )
            return response
    except Exception as e:
        print(f"Error during text-to-speech conversion: {e}")
        return None