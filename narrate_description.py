from fastapi import APIRouter, WebSocket
from elevenlabs.client import ElevenLabs
import asyncio
import os
import json
import base64
import websockets
import anthropic

router = APIRouter()

ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# Initialise the Anthropics client with your API key
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

@router.websocket_route("/narrate")
async def websocket_narrate(websocket: WebSocket):
    print("WebSocket connection accepted.")
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        #print(f"Received data: {data}")
        if data == "close":
            print("Closing WebSocket connection.")
            break

        # Assuming the data is JSON with an 'image' field containing the base64 encoded image
        data_json = json.loads(data)
        image_data = data_json.get('image')
        if image_data:
            print("Image data received, sending to Claude model for analysis.")
            # Send the image to the Claude model for analysis
            try:
                message = client.messages.create(
                    model="claude-3-haiku-20240307",  # Adjust the model ID as needed
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

            # Assuming the message contains the text to be narrated
            if message.content:
                try:
                    david_a_voice_id = "David_A"
                    audio_generator = elevenlabs_client.generate(
                        text=message.content[0].text,
                        voice=david_a_voice_id,
                        model="eleven_monolingual_v1"
                    )

                    # Assuming the generator yields binary audio content directly
                    audio_content = next(audio_generator)  # Get the first (and possibly only) chunk of audio

                    # If the audio content is already binary, no need for base64 decoding
                    # Otherwise, adjust the handling here based on the actual format
                    audio_binary = audio_content  # Assuming audio_content is already binary

                    print("Received audio from ElevenLabs, sending to client.")
                    await websocket.send_bytes(audio_binary)
                except Exception as e:
                    print(f"Error during text-to-speech conversion: {e}")
        else:
            print("No image data received, sending error message to client.")
            await websocket.send_text("No image data received.")

    await websocket.close()
    print("WebSocket connection closed.")