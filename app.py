import os
import io
import base64
import tempfile
import asyncio
from dotenv import load_dotenv
from PIL import Image
import gradio as gr

from convert_text_to_speech import (
    convert_text_to_speech,
    preload_all_embeddings,
    warm_up_tts,
    get_tts_model,
    VOICE_DISPLAY_NAMES,
)
from generate_description import generate_description

load_dotenv()

MOCK_VOICE_LABELS = {
    "David Attenborough": "D. Attenborough 🌍",
    "James May": "J. May 🔧",
    "John Cleese": "J. Cleese 🐍",
    "Michael Caine": "M. Caine 🎩",
    "Morgan Freeman": "M. Freeman 🎤",
    "Joanna Lumley": "J. Lumley 💄",
    "Judi Dench": "J. Dench 🎭",
    "Stephen Fry": "S. Fry 📚",
}

VOICE_OPTIONS = [MOCK_VOICE_LABELS[name] for name in VOICE_DISPLAY_NAMES]
VOICE_LABEL_TO_NAME = {label: name for name, label in MOCK_VOICE_LABELS.items()}


def _image_to_base64(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=90)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


async def _generate_text_and_audio(image: Image.Image, voice_label: str, politeness_level: int):
    if image is None:
        return "Please upload an image.", None

    voice_name = VOICE_LABEL_TO_NAME.get(voice_label, VOICE_DISPLAY_NAMES[0])
    image_b64 = _image_to_base64(image)

    description = ""
    async for chunk in generate_description(image_b64, voice_name, [], politeness_level):
        if chunk:
            description += chunk

    if not description.strip():
        return "No description generated.", None

    audio_bytes = b""
    async for chunk in convert_text_to_speech(description.strip(), voice_name):
        audio_bytes += chunk

    if not audio_bytes:
        return description.strip(), None

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp.write(audio_bytes)
    tmp.flush()
    tmp.close()

    return description.strip(), tmp.name


async def generate_narration(image: Image.Image, voice_label: str, politeness_level: int):
    return await _generate_text_and_audio(image, voice_label, politeness_level)


def warm_up():
    get_tts_model()
    preload_all_embeddings()
    warm_up_tts()

def _is_kaggle():
    return os.getenv("KAGGLE_KERNEL_RUN_TYPE") is not None

def _is_colab():
    return os.getenv("COLAB_GPU") is not None or os.getenv("COLAB_JUPYTER") is not None

def launch_app():
    warm_up()
    if _is_kaggle() or _is_colab():
        return demo.queue().launch(share=True, debug=False)
    return demo.queue().launch(server_name="0.0.0.0", server_port=7860)


with gr.Blocks(title="AI Image Narrator") as demo:
    gr.Markdown("AI Image Narrator")

    with gr.Row():
        image_input = gr.Image(type="pil", label="Upload Image")
        with gr.Column():
            voice_input = gr.Dropdown(
                choices=VOICE_OPTIONS,
                value=VOICE_OPTIONS[0],
                label="Voice",
            )
            politeness_input = gr.Slider(1, 10, value=5, step=1, label="Personality Level")
            generate_btn = gr.Button("Generate Narration")

    description_output = gr.Textbox(label="Description")
    audio_output = gr.Audio(label="Narration", type="filepath")

    generate_btn.click(
        fn=generate_narration,
        inputs=[image_input, voice_input, politeness_input],
        outputs=[description_output, audio_output],
    )


if __name__ == "__main__":
    launch_app()
