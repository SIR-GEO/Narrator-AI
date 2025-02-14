### Available to play with for free: https://huggingface.co/spaces/Mr-Geo/ai-narrator

# Narrator-AI

The AI Image Narrator is an interactive web application that captures images from a user's webcam, analyses them, and generates a humorous description in the voice of a selected celebrity inspired voice. The description is then converted to speech, providing an engaging and unique experience. This document outlines the system's components, setup, and usage.

The aim is to create a real-time interface between streaming the text description and streaming the text to speech as the text is generated.

## System Overview

The system comprises a front-end web interface and a back-end server. The front-end captures images and handles user interactions, while the back-end processes images and text, generating descriptions and converting them to speech using external APIs.

### Front-end Components

- **Webcam Feed**: Utilises the user's webcam to capture images.
- **Voice Selection**: Allows users to select a celebrity voice for the narration.
- **Narrate Button**: Initiates the capture and analysis of the current webcam image.

### Back-end Components

- **WebSocket Server**: Facilitates real-time communication between the front-end and back-end.
- **Image Description Generation**: Analyses images and generates descriptions in a humorous style, tailored to the selected celebrity voice.
- **Text-to-Speech Conversion**: Converts the generated descriptions to audio using the selected voice.

## Technologies Used

- **Front-end**: HTML, CSS, JavaScript
- **Back-end**: Python, FastAPI, WebSocket
- **External APIs**: ElevenLabs for text-to-speech conversion, Anthropic for image description generation

## Setup and Installation

1. **Clone the Repository**: Clone the project to your local machine.
2. **Install Dependencies**:
   - Python dependencies: Run `pip install fastapi uvicorn httpx elevenlabs-client anthropic`.
   - Ensure you have Node.js installed for front-end dependencies.
3. **Set Environment Variables**: Define the following environment variables:
   - `ELEVENLABS_API_KEY`: Your API key for ElevenLabs.
   - `ANTHROPIC_API_KEY`: Your API key for Anthropic.
4. **Start the Back-end Server**: Navigate to the project directory and run `uvicorn main:app --reload` to start the FastAPI server.
5. **Access the Web Interface**: Open your browser and go to `http://localhost:8000` to view the application.

## Usage

1. **Select a Voice**: Click on one of the celebrity voice buttons to select a voice for the narration.
2. **Capture an Image**: Click the "Narrate" button to capture an image from your webcam.
3. **Receive Narration**: Wait for the system to analyse the image, generate a description, and convert it to speech. The description will be displayed on the screen, and the audio will play automatically.

