from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
from generate_description import generate_description
from convert_text_to_speech import convert_text_to_speech
import re
import asyncio

router = APIRouter()

description_history = []

@router.websocket_route("/narrate")
async def websocket_narrate(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection accepted.")
    print("connection open")
    
    try:
        while True:
            try:
                data = await websocket.receive_text()
                if data == "close":
                    print("Closing WebSocket connection.")
                    await websocket.close(code=1000)
                    break

                data_json = json.loads(data)
                image_data = data_json.get('image')
                selected_voice_id = data_json.get('voiceId')
                selected_voice_name = data_json.get('voiceName')
                politeness_level = int(data_json.get('politenessLevel', 5))
                
                if not image_data:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "data": "No image data received."
                    }))
                    continue

                print(f"Image data received, sending to {selected_voice_name} model for analysis with politeness level {politeness_level}.")
                description_accumulator = ""
                punctuation_pattern = re.compile(r"[*]")
                
                async for description_chunk in generate_description(image_data, selected_voice_name, description_history, politeness_level):
                    if description_chunk:
                        if not punctuation_pattern.fullmatch(description_chunk.strip()):
                            description_accumulator += description_chunk
                        else:
                            description_accumulator += " " + description_chunk

                        await websocket.send_text(json.dumps({
                            "type": "text_chunk", 
                            "data": description_chunk, 
                            "pictureCount": data_json.get('pictureCount'), 
                            "voiceName": selected_voice_name
                        }))

                        if punctuation_pattern.search(description_chunk):
                            try:
                                audio_chunks = convert_text_to_speech(description_accumulator.strip(), selected_voice_id)
                                async for chunk in audio_chunks:
                                    await websocket.send_bytes(chunk)
                                description_history.append(description_accumulator.strip())
                                description_accumulator = ""
                            except Exception as e:
                                print(f"Error processing audio: {e}")
                                await websocket.send_text(json.dumps({
                                    "type": "error",
                                    "data": "Error processing audio"
                                }))

                if description_accumulator:
                    try:
                        audio_chunks = convert_text_to_speech(description_accumulator.strip(), selected_voice_id)
                        async for chunk in audio_chunks:
                            await websocket.send_bytes(chunk)
                        description_history.append(description_accumulator.strip())
                    except Exception as e:
                        print(f"Error processing final audio: {e}")
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "data": "Error processing final audio"
                        }))

                print("Finished processing image data.")

            except WebSocketDisconnect:
                print("Client disconnected")
                break
            except Exception as e:
                print(f"Error processing message: {e}")
                try:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "data": "Error processing message"
                    }))
                except:
                    break

    except Exception as e:
        print(f"Error during WebSocket communication: {e}")
    finally:
        print("connection closed")
        try:
            await websocket.close(code=1000)
        except:
            pass