from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
from generate_description import generate_description
from convert_text_to_speech import convert_text_to_speech, get_voice_statuses, get_voice_asset_status, is_tts_ready
import re
import asyncio
import time

router = APIRouter()

description_history = []

@router.websocket_route("/narrate")
async def websocket_narrate(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection accepted.")
    print("connection open")
    try:
        await websocket.send_text(json.dumps({
            "type": "voice_status",
            "data": get_voice_statuses()
        }))
        await websocket.send_text(json.dumps({
            "type": "server_ready",
            "ready": is_tts_ready()
        }))
        await websocket.send_text(json.dumps({
            "type": "status",
            "message": "Ready for a new image.",
            "detail": "All voices have been checked for availability."
        }))
    except Exception:
        pass
    
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
                selected_voice_name = data_json.get('voiceName')
                selected_voice_label = data_json.get('voiceLabel', selected_voice_name)
                politeness_level = int(data_json.get('politenessLevel', 5))
                
                if not image_data:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "data": "No image data received."
                    }))
                    continue

                print(f"Image data received, sending to {selected_voice_name} model for analysis with politeness level {politeness_level}.")
                await websocket.send_text(json.dumps({
                    "type": "status",
                    "message": "Analysing image...",
                    "detail": "Working on the description."
                }))
                
                # Collect full description first (Claude is fast anyway)
                full_description = ""
                async for description_chunk in generate_description(image_data, selected_voice_name, description_history, politeness_level):
                    if description_chunk:
                        full_description += description_chunk
                        await websocket.send_text(json.dumps({
                            "type": "text_chunk", 
                            "data": description_chunk, 
                            "pictureCount": data_json.get('pictureCount'), 
                            "voiceName": selected_voice_name,
                            "voiceLabel": selected_voice_label
                        }))
                
                # Generate audio for complete description (smoother, single audio file)
                if full_description.strip():
                    try:
                        voice_status = get_voice_asset_status(selected_voice_name)
                        if voice_status == "missing":
                            await websocket.send_text(json.dumps({
                                "type": "status",
                                "message": "Voice samples missing.",
                                "detail": "Using default voice for this request."
                            }))

                        start_time = time.time()

                        async def progress_updates():
                            while True:
                                elapsed = int(time.time() - start_time)
                                await websocket.send_text(json.dumps({
                                    "type": "status",
                                    "message": "Generating voice...",
                                    "detail": f"Elapsed: {elapsed}s (free tier can take 2–3 mins)"
                                }))
                                await asyncio.sleep(1)

                        progress_task = asyncio.create_task(progress_updates())
                        try:
                            audio_chunks = convert_text_to_speech(full_description.strip(), selected_voice_name)
                            async for chunk in audio_chunks:
                                await websocket.send_bytes(chunk)
                        finally:
                            progress_task.cancel()
                            try:
                                await progress_task
                            except asyncio.CancelledError:
                                pass
                        await websocket.send_text(json.dumps({
                            "type": "status",
                            "message": "Audio ready.",
                            "detail": "Playing now."
                        }))
                        description_history.append(full_description.strip())
                    except Exception as e:
                        print(f"Error processing audio: {e}")
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "data": "Error processing audio"
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