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

# Initialise the Anthropics client with your API key
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)  # Renamed variable here

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
            if image_data:
                print("Image data received, sending to Claude model for analysis.")
                message = None  # Initialize message to None
                try:
                    # Use the renamed anthropic_client here
                    message = anthropic_client.messages.create(
                        model="claude-3-haiku-20240307",
                        max_tokens=300,
                        temperature=1,
                        system="You are insert name here",
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
                                        "text": "describe this image in 20 words or less"
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
                        voice_id = "4c42HvUOZ0L0feAu3r5C"  # Ensure this is a valid voice ID
                        model_id = "eleven_monolingual_v1"
                        text_to_speak = message.content[0].text  # Use the text from the model response
                        output_format = "mp3_44100_128"

                        # Use a different variable name for httpx.AsyncClient to avoid conflict
                        async with httpx.AsyncClient() as http_client:
                            response = await http_client.post(
                                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream",
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
        # Ensure the WebSocket is closed in case of an error or if the connection is supposed to be closed.
        await websocket.close()