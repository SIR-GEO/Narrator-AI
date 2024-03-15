from fastapi import APIRouter, WebSocket
from elevenlabs.client import ElevenLabs
import asyncio
import os
import json
import base64
import websockets
import anthropic
import httpx

router = APIRouter()

ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

@router.websocket_route("/narrate")
async def websocket_narrate(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection accepted.")
    try:
        while True:
            data = await websocket.receive_text()
            if data == "close":
                print("Closing WebSocket connection.")
                break

            data_json = json.loads(data)
            image_data = data_json.get('image')
            selected_voice_id = data_json.get('voiceId', "4c42HvUOZ0L0feAu3r5C")
            selected_voice_name = data_json.get('voiceName', "David Attenborough")
            if image_data:
                print(f"Image data received, sending to {selected_voice_name} model for analysis.")
                message = None
                try:
                    message = anthropic_client.messages.create(
                        model="claude-3-haiku-20240307",
                        max_tokens=300,
                        temperature=1,
                        system=f"You are {selected_voice_name} and you must describe the image you are given using your unique phrases in a humorous way and you must always use less than 20 words for each response",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "base64",
                                            "media_type": "image/jpeg",
                                            "data": image_data
                                        }
                                    },
                                    {
                                        "type": "text",
                                        "text": f"As {selected_voice_name} describe this image in humorous way in 20 words or less"
                                    }
                                ]
                            }
                        ]
                    )
                    print(f"Model response: {message.content[0].text}")
                except Exception as e:
                    print(f"Error sending image to model: {e}")

                # Check if message is not None before accessing its content
                if message and message.content:
                    try:
                        model_id = "eleven_monolingual_v1"
                        text_to_speak = message.content[0].text
                        output_format = "mp3_44100_128"

                        async with httpx.AsyncClient() as http_client:
                            response = await http_client.post(
                                f"https://api.elevenlabs.io/v1/text-to-speech/{selected_voice_id}/stream",
                                json={
                                    "model_id": model_id,
                                    "text": text_to_speak,
                                    "output_format": output_format
                                },
                                headers={
                                    "Content-Type": "application/json",
                                    "xi-api-key": ELEVENLABS_API_KEY
                                },
                                timeout=None
                            )

                            if response.status_code == 200:
                                # First, send the text to the frontend
                                await websocket.send_text(json.dumps({"type": "text", "data": text_to_speak}))
                                # Then, send the audio chunks
                                async for chunk in response.aiter_bytes():
                                    await websocket.send_bytes(chunk)
                                print("Received audio from ElevenLabs, sent to client.")
                            else:
                                print(f"Error from ElevenLabs API: {response.text}")
                    except Exception as e:
                        print(f"Error during text-to-speech conversion: {e}")
                else:
                    print("No image data received, sending error message to client.")
                    await websocket.send_text("No image data received.")

        print("WebSocket connection closed.")
    except Exception as e:
        print(f"Error during WebSocket communication: {e}")
    finally:
        await websocket.close()