import os
import anthropic

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

async def generate_description(image_data, selected_voice_name):
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
        return message.content[0].text if message and message.content else None
    except Exception as e:
        print(f"Error generating description: {e}")
        return None
