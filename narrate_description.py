from fastapi import APIRouter, WebSocket
import json
from generate_description import generate_description
from convert_text_to_speech import convert_text_to_speech
import re
import asyncio

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
                description_accumulator = ""
                punctuation_pattern = re.compile(r"[.!?]")

                async for description_chunk in generate_description(image_data, selected_voice_name):
                    if description_chunk:
                        # Accumulate the chunk, ensuring not to break on single punctuation marks
                        if not punctuation_pattern.fullmatch(description_chunk.strip()):
                            description_accumulator += description_chunk
                        else:
                            description_accumulator += " " + description_chunk

                        # Send each text chunk to the frontend
                        await websocket.send_text(json.dumps({"type": "text_chunk", "data": description_chunk, "pictureCount": data_json.get('pictureCount')}))

                        # If the chunk ends with punctuation, convert and stream it
                        if punctuation_pattern.search(description_chunk):
                            audio_chunks = convert_text_to_speech(description_accumulator.strip(), selected_voice_id)
                            await asyncio.gather(*[websocket.send_bytes(chunk) async for chunk in audio_chunks])
                            description_accumulator = ""

                # If there is any remaining text after the loop, send it for conversion too
                if description_accumulator:
                    audio_chunks = convert_text_to_speech(description_accumulator.strip(), selected_voice_id)
                    await asyncio.gather(*[websocket.send_bytes(chunk) async for chunk in audio_chunks])

                print("Finished processing image data.")
            else:
                print("No image data received, sending error message to client.")
                await websocket.send_text("No image data received.")

        print("WebSocket connection closed.")
    except Exception as e:
        print(f"Error during WebSocket communication: {e}")
    finally:
        await websocket.close()