import os
import asyncio
from anthropic import AsyncAnthropic

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

async def generate_description(image_data, selected_voice_name, description_history):
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    try:
        system_prompt = f"You are {selected_voice_name} and you must describe the image you are given using your unique phrases in a humorous way in 15 words or less. Please use only raw text without any special formatting characters like asterisks. Your previous image descriptions will now be given, only use them as context, do not just repeat what is said: {' '.join(description_history)}"
        
        print("System prompt:", system_prompt)

        async with client.messages.stream(
            model="claude-3-haiku-20240307",
            max_tokens=100,
            temperature=1,
            system=system_prompt,
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
                            "text": f"As {selected_voice_name} describe this image in humorous way in 15 words or less"
                        }
                    ]
                }
            ]
        ) as stream:
            description = ""
            async for event in stream.text_stream:
                print(event)
                description += event
                yield event
    except Exception as e:
        print(f"Error generating description: {e}")
        yield "Error generating description."