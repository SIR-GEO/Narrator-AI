from fastapi import APIRouter, WebSocket
import json
from generate_description import generate_description
from convert_text_to_speech import convert_text_to_speech

router = APIRouter()

@router.websocket_route("/narrate")
async def websocket_narrate(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection accepted.")
    full_description = ""
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
                # Reset full_description for each new image data received
                full_description = ""
                # Use a generator function to stream text chunks
                async for description_chunk in generate_description(image_data, selected_voice_name):
                    if description_chunk:
                        # Accumulate each text chunk into the full description
                        full_description += description_chunk
                        # Send each text chunk to the frontend
                        await websocket.send_text(json.dumps({"type": "text_chunk", "data": description_chunk}))
                # After all chunks are sent and the full description is accumulated, proceed with text-to-speech conversion
                if full_description:
                    response = await convert_text_to_speech(full_description, selected_voice_id)
                    if response and response.status_code == 200:
                        # Then, send the audio chunks
                        async for chunk in response.aiter_bytes():
                            await websocket.send_bytes(chunk)
                        print("Received audio from text-to-speech service, sent to client.")
                    else:
                        print(f"Error from text-to-speech API: {response.text}" if response else "Error during text-to-speech conversion.")
                else:
                    print("No description generated.")
            else:
                print("No image data received, sending error message to client.")
                await websocket.send_text("No image data received.")

        print("WebSocket connection closed.")
    except Exception as e:
        print(f"Error during WebSocket communication: {e}")
    finally:
        await websocket.close()