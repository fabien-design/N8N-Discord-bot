"""
Audio transcription module using Google Speech Recognition (free).
Handles downloading, converting, and transcribing audio files.
"""

import os
import tempfile
import asyncio
import logging
import aiohttp
import speech_recognition as sr
from pydub import AudioSegment

logger = logging.getLogger("discord_bot")


async def download_audio(audio_url: str) -> str:
    """
    Download audio file from URL and save to temporary file.

    Args:
        audio_url: URL of the audio file to download

    Returns:
        Path to the temporary audio file
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(audio_url) as response:
            if response.status == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_file:
                    temp_file.write(await response.read())
                    return temp_file.name
    return None


def convert_ogg_to_wav(ogg_path: str) -> str:
    """
    Convert OGG audio file to WAV format.

    Args:
        ogg_path: Path to the OGG file

    Returns:
        Path to the converted WAV file
    """
    wav_path = ogg_path.replace('.ogg', '.wav')
    audio = AudioSegment.from_ogg(ogg_path)
    audio.export(wav_path, format="wav")
    return wav_path


def transcribe_wav(wav_path: str, language: str = 'fr-FR') -> str:
    """
    Transcribe WAV audio file to text using Google Speech Recognition.

    Args:
        wav_path: Path to the WAV file
        language: Language code (default: 'fr-FR')

    Returns:
        Transcribed text or None if failed
    """
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio_data = recognizer.record(source)
        try:
            # Try with specified language first
            return recognizer.recognize_google(audio_data, language=language)
        except:
            # Fallback to English if specified language fails
            if language != 'en-US':
                return recognizer.recognize_google(audio_data, language='en-US')
            raise


async def transcribe_audio_from_url(audio_url: str) -> str:
    """
    Complete pipeline: download, convert, and transcribe audio from URL.

    Args:
        audio_url: URL of the audio file

    Returns:
        Transcribed text or None if any step fails
    """
    temp_ogg_path = None
    temp_wav_path = None

    try:
        # Download audio
        logger.info(f"Downloading audio from {audio_url}")
        temp_ogg_path = await download_audio(audio_url)
        if not temp_ogg_path:
            logger.error("Failed to download audio")
            return None

        # Convert to WAV
        logger.info("Converting OGG to WAV")
        temp_wav_path = await asyncio.get_event_loop().run_in_executor(
            None, convert_ogg_to_wav, temp_ogg_path
        )

        # Transcribe
        logger.info("Transcribing audio")
        transcript = await asyncio.get_event_loop().run_in_executor(
            None, transcribe_wav, temp_wav_path, 'fr-FR'
        )

        logger.info(f"Transcription successful: {transcript}")
        return transcript

    except Exception as e:
        logger.error(f"Error during transcription: {e}")
        return None

    finally:
        # Clean up temporary files
        if temp_ogg_path and os.path.exists(temp_ogg_path):
            os.unlink(temp_ogg_path)
        if temp_wav_path and os.path.exists(temp_wav_path):
            os.unlink(temp_wav_path)
