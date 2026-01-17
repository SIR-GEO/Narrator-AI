import os
import asyncio
from anthropic import AsyncAnthropic

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

def get_politeness_prompt(politeness_level):
    prompts = {
        1: "Be extremely formal and sophisticated, using the most refined and elegant language possible.",
        2: "Be very proper and courteous, offering sincere compliments with graceful language.",
        3: "Be warmly professional, using polite and encouraging words.",
        4: "Be friendly and positive, maintaining an upbeat and welcoming tone.",
        5: "Be conversational and natural, like chatting with a friend.",
        6: "Be casual and laid-back, using everyday language.",
        7: "Be playful and fun, adding light jokes to the description.",
        8: "Be mildly sarcastic, with gentle teasing and witty observations.",
        9: "Be cheekily critical, using clever wordplay and humorous jabs.",
        10: "Be hilariously snarky, with maximum sass but keeping it playful.",
    }
    
    return prompts.get(politeness_level, "Be casual and straightforward, with a balanced tone.")

async def generate_description(image_data, selected_voice_name, description_history, politeness_level=5):
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    try:
        politeness_instruction = get_politeness_prompt(politeness_level)
        system_prompt = f"""You are {selected_voice_name} and you must describe the image you are given in 15 words or less. {politeness_instruction}
        Please use only raw text without any special formatting characters like asterisks."""
        
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
                            "text": f"As {selected_voice_name}, describe this image in your assigned tone in 15 words or less"
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