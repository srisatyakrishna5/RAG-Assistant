"""
services/speech.py — Voice input (Speech-to-Text) and voice output (Text-to-Speech).

This module wraps the **Azure Cognitive Services Speech SDK** to provide two
capabilities:

1. **Speech-to-Text (STT)** via :func:`transcribe_audio` — Users can record
   their question through the browser microphone.  The WAV bytes are written
   to a temporary file and sent to Azure Speech for recognition.

2. **Text-to-Speech (TTS)** via :func:`synthesize_speech` — After an answer
   is generated, a condensed spoken version is synthesised using an Azure
   Neural voice and returned as a WAV audio stream for the browser player.

The module handles the optional nature of the SDK gracefully:  if
``azure-cognitiveservices-speech`` is not installed, ``SPEECH_SDK_AVAILABLE``
is set to ``False`` and the UI disables all voice features rather than
crashing.  This allows the app to run in environments that cannot install the
native Speech SDK binary.

Neural voice selection is driven by ``LANGUAGE_CONFIG`` in :mod:`config` so
that TTS output matches the user's chosen output language.
"""

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
    """Transcribe WAV audio bytes to text using the Azure Speech Service.

    Writes the audio bytes to a temporary ``.wav`` file on disk (the Azure
    Speech SDK requires a file path rather than an in-memory buffer), creates
    a ``SpeechRecognizer`` configured for English (``en-US``), and calls
    ``recognize_once_async()`` which blocks until the first complete utterance
    is detected or the stream ends.

    The temporary file is always deleted in the ``finally`` block, even if
    recognition fails.  On Windows the SDK may hold a file handle briefly
    after the recognizer is destroyed, so the recognizer and audio config
    objects are explicitly deleted before attempting ``os.unlink``.

    Args:
        audio_bytes (bytes): Raw WAV audio data as captured by Streamlit's
            ``st.audio_input`` widget.  The bytes are written directly to disk
            without re-encoding, so the format must be WAV PCM.

    Returns:
        str: The recognised sentence/utterance as a plain string.
            Returns an empty string (``""``) if the speech service detected no
            intelligible speech in the audio (``NoMatch`` result).

    Raises:
        RuntimeError: If the Azure Cognitive Services Speech SDK is not
            installed (``SPEECH_SDK_AVAILABLE`` is ``False``).
        RuntimeError: If the speech recognition service returns an error
            (e.g., cancelled due to network failure or authentication error).
            The error details from the SDK cancellation object are included
            in the message.

    Example:
        >>> with open("question.wav", "rb") as f:
        ...     text = transcribe_audio(f.read())
        >>> text
        'What is the main conclusion of the report?'
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
    """Synthesise text into a WAV audio stream using Azure Neural TTS.

    Looks up the Azure Neural voice name for the target language from
    ``LANGUAGE_CONFIG`` and creates a ``SpeechSynthesizer`` wired to an
    in-memory output (``audio_config=None``) rather than a speaker device.
    The synthesizer generates 24 kHz / 16-bit mono PCM WAV audio, which is
    supported natively by Streamlit's ``st.audio`` widget.

    The output format ``Riff24Khz16BitMonoPcm`` is chosen for broad browser
    compatibility — it is a standard WAV container that all modern browsers
    can play without transcoding.

    Args:
        text (str): The text to be spoken aloud.  This is typically the
            output of :func:`~services.llm.summarize_for_speech` — a short,
            formatting-free spoken paragraph.  Passing markdown-heavy text
            may result in the TTS engine reading out symbols verbatim.
        language (str): Target language display name as defined in
            ``LANGUAGE_CONFIG`` (e.g., ``"English"``, ``"Hindi"``,
            ``"French"``, ``"Telugu"``).  Determines which Neural voice is
            used.  Defaults to ``"English"`` (``en-US-JennyNeural``).

    Returns:
        io.BytesIO: A seeked (position 0) in-memory byte stream containing
            raw WAV PCM audio data.  Pass directly to ``st.audio()``.

    Raises:
        RuntimeError: If the Azure Cognitive Services Speech SDK is not
            installed (``SPEECH_SDK_AVAILABLE`` is ``False``).
        RuntimeError: If the speech synthesis service fails (e.g., network
            error or unsupported language/voice).  The SDK cancellation error
            details are included in the message.

    Example:
        >>> audio_stream = synthesize_speech("Hello world", language="Hindi")
        >>> type(audio_stream)
        <class '_io.BytesIO'>
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


def synthesize_podcast(
    segments: list[dict], language: str = "English"
) -> tuple[io.BytesIO, list[dict]]:
    """Synthesise a podcast script into WAV audio with word-level timing data.

    Uses SSML to insert natural pauses between segments and subscribes to the
    Azure Speech SDK's ``synthesis_word_boundary`` event to capture the exact
    start time and duration of every word.  The timing data enables the UI to
    highlight transcript text in sync with audio playback.

    Args:
        segments (list[dict]): Ordered podcast segments as returned by
            :func:`~services.llm.generate_podcast_script`.  Each dict must
            contain a ``text`` key with the spoken paragraph.
        language (str): Target language display name from ``LANGUAGE_CONFIG``.
            Determines the Neural voice used for synthesis.

    Returns:
        tuple[io.BytesIO, list[dict]]: A two-element tuple:
            - **audio** — Seeked ``BytesIO`` WAV stream ready for playback.
            - **timing** — List of word-boundary dicts, each containing:
              ``word`` (str), ``offset_ms`` (float), ``duration_ms`` (float),
              and ``segment_index`` (int, 0-based).
    """
    if not SPEECH_SDK_AVAILABLE:
        raise RuntimeError("Install azure-cognitiveservices-speech for podcast generation.")

    lang_cfg = LANGUAGE_CONFIG.get(language, LANGUAGE_CONFIG["English"])

    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY, region=AZURE_SPEECH_REGION
    )
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
    )

    voice_name = lang_cfg["voice"]
    speech_locale = lang_cfg["speech_locale"]

    # Build SSML with pauses between segments
    ssml_parts = [
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{speech_locale}">'
        f'<voice name="{voice_name}">'
    ]
    for seg in segments:
        text = seg.get("text", "")
        # Escape XML special characters
        text = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )
        ssml_parts.append(f"{text}")
        ssml_parts.append('<break time="750ms"/>')
    ssml_parts.append("</voice></speak>")
    ssml = "".join(ssml_parts)

    # Collect word boundary events for timing
    timing_data: list[dict] = []
    # Build a mapping from character offset → segment index.
    # We'll track cumulative offset as SSML text is spoken.
    segment_texts = [seg.get("text", "") for seg in segments]

    def _on_word_boundary(evt):
        timing_data.append({
            "word": evt.text,
            "offset_ms": evt.audio_offset / 10_000,  # 100-ns ticks → ms
            "duration_ms": evt.duration.total_seconds() * 1000,
        })

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=None
    )
    synthesizer.synthesis_word_boundary.connect(_on_word_boundary)

    result = synthesizer.speak_ssml_async(ssml).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        audio_stream = io.BytesIO(result.audio_data)
        audio_stream.seek(0)

        # Map each word to its segment by matching words to segment texts
        _assign_segments(timing_data, segment_texts)

        return audio_stream, timing_data

    cancellation = result.cancellation_details
    raise RuntimeError(
        f"Podcast synthesis failed: {result.reason}. "
        f"{cancellation.error_details if cancellation else ''}"
    )


def _assign_segments(timing_data: list[dict], segment_texts: list[str]) -> None:
    """Assign a segment_index to each word in timing_data by matching sequentially."""
    seg_idx = 0
    seg_word_lists = []
    for text in segment_texts:
        words = text.split()
        seg_word_lists.append(words)

    seg_word_pos = 0
    for entry in timing_data:
        if seg_idx < len(seg_word_lists):
            entry["segment_index"] = seg_idx
            seg_word_pos += 1
            if seg_word_pos >= len(seg_word_lists[seg_idx]):
                seg_idx += 1
                seg_word_pos = 0
        else:
            entry["segment_index"] = len(segment_texts) - 1
