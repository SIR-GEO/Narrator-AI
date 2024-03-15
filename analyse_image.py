from fastapi import WebSocket, APIRouter, Request
from starlette.websockets import WebSocketState
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
import os
import anthropic


router = APIRouter()

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

# Initialise the Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)



@router.post("/analyse-image")
async def analyse_image(request: Request):
    body = await request.json()
    imageData = body['imageData']  # This should be the base64 encoded image data

    try:
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
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
                                "data": imageData  # Use the base64 encoded image data here
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
        return {"description": message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyse image: {str(e)}")