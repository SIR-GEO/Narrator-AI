from fastapi import APIRouter, WebSocket
import json
from generate_description import generate_description
from convert_text_to_speech import convert_text_to_speech

router = APIRouter()

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
            selected_voice_id = data_json.get('voiceId')
            selected_voice_name = data_json.get('voiceName')
            if image_data:
                print(f"Image data received, sending to {selected_voice_name} model for analysis.")
                description_text = await generate_description(image_data, selected_voice_name)
                if description_text:
                    print(f"Model response: {description_text}")
                    response = await convert_text_to_speech(description_text, selected_voice_id)
                    if response and response.status_code == 200:
                        # First, send the text to the frontend
                        await websocket.send_text(json.dumps({"type": "text", "data": description_text}))
                        # Then, send the audio chunks
                        async for chunk in response.aiter_bytes():
                            await websocket.send_bytes(chunk)
                        print("Received audio from ElevenLabs, sent to client.")
                    else:
                        print(f"Error from ElevenLabs API: {response.text}" if response else "Error during text-to-speech conversion.")
                else:
                    print("Error generating description or no description returned.")
                    await websocket.send_text("Error generating description or no description returned.")
            else:
                print("No image data received, sending error message to client.")
                await websocket.send_text("No image data received.")

        print("WebSocket connection closed.")
    except Exception as e:
        print(f"Error during WebSocket communication: {e}")
    finally:
        await websocket.close()