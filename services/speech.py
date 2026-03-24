import io
import os
import tempfile

try:
    import azure.cognitiveservices.speech as speechsdk
    SPEECH_SDK_AVAILABLE = True
except ImportError:
    SPEECH_SDK_AVAILABLE = False

from config import AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, LANGUAGE_CONFIG


def transcribe_audio(audio_bytes: bytes) -> str:
    """Transcribe WAV audio bytes to text using Azure Speech Service.

    Returns the recognised text, or an empty string if no speech was detected.
    Raises RuntimeError on SDK errors.
    """
    if not SPEECH_SDK_AVAILABLE:
        raise RuntimeError("Install azure-cognitiveservices-speech to use voice input.")

    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION
    )
    speech_config.speech_recognition_language = "en-US"

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        audio_config = speechsdk.AudioConfig(filename=tmp_path)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, audio_config=audio_config
        )
        result = recognizer.recognize_once_async().get()
        # Release SDK objects so the file handle is freed on Windows before unlink
        del recognizer
        del audio_config

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return result.text
        if result.reason == speechsdk.ResultReason.NoMatch:
            return ""
        cancellation = result.cancellation_details
        raise RuntimeError(
            f"Speech recognition failed: {result.reason}. "
            f"{cancellation.error_details if cancellation else ''}"
        )
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass  # Windows may still hold the handle briefly; temp-dir cleanup handles it


def synthesize_speech(text: str, language: str = "English") -> io.BytesIO:
    """Synthesize text to a WAV audio stream using the Azure Speech Service.

    Selects the Neural voice appropriate for the requested language.
    Returns a seeked BytesIO containing raw WAV PCM data.
    """
    if not SPEECH_SDK_AVAILABLE:
        raise RuntimeError("Install azure-cognitiveservices-speech to use voice output.")

    lang_cfg = LANGUAGE_CONFIG.get(language, LANGUAGE_CONFIG["English"])

    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION
    )
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
    )
    speech_config.speech_synthesis_voice_name = lang_cfg["voice"]

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=None
    )
    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        audio_stream = io.BytesIO(result.audio_data)
        audio_stream.seek(0)
        return audio_stream

    cancellation = result.cancellation_details
    raise RuntimeError(
        f"Speech synthesis failed: {result.reason}. "
        f"{cancellation.error_details if cancellation else ''}"
    )
