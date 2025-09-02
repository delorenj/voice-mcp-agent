"""
Custom Whisper STT implementation for self-hosted speech-to-text
using faster-whisper for optimal performance on big-chungus
"""

import asyncio
import logging
import os
import tempfile
import numpy as np
from typing import AsyncIterator
from livekit.agents import stt, utils
from livekit import rtc

try:
    from faster_whisper import WhisperModel
except ImportError:
    try:
        import whisper
        WhisperModel = None  # Fallback to openai-whisper
    except ImportError:
        raise ImportError("Please install either faster-whisper or openai-whisper: pip install faster-whisper")

logger = logging.getLogger(__name__)

class CustomWhisperSTT(stt.STT):
    """Custom Whisper STT implementation using faster-whisper or openai-whisper."""
    
    def __init__(
        self, 
        model_size: str = "base",
        language: str = "en",
        device: str = "cpu",
        compute_type: str = "int8"
    ):
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=False,  # Whisper is not streaming
                interim_results=False,
            )
        )
        self._model_size = model_size
        self._language = language
        self._device = device
        self._compute_type = compute_type
        self._model = None
        
    async def _ensure_model_loaded(self):
        """Load the Whisper model if not already loaded."""
        if self._model is None:
            logger.info(f"Loading Whisper model: {self._model_size}")
            if WhisperModel:
                # Use faster-whisper (recommended)
                self._model = WhisperModel(
                    self._model_size,
                    device=self._device,
                    compute_type=self._compute_type
                )
                self._use_faster_whisper = True
            else:
                # Fallback to openai-whisper
                import whisper
                self._model = whisper.load_model(self._model_size)
                self._use_faster_whisper = False
            logger.info(f"Whisper model loaded successfully")
    
    async def _recognize_impl(
        self,
        buffer: utils.AudioBuffer,
        *,
        language: str | None = None,
    ) -> stt.SpeechEvent:
        """Recognize speech from audio buffer."""
        await self._ensure_model_loaded()
        
        # Convert audio buffer to numpy array
        audio_data = utils.merge_frames(buffer)
        
        # Convert to float32 numpy array (required by Whisper)
        if isinstance(audio_data, rtc.AudioFrame):
            # Extract audio data from LiveKit AudioFrame
            samples = np.frombuffer(audio_data.data, dtype=np.int16).astype(np.float32)
            samples = samples / 32768.0  # Normalize to [-1, 1]
        else:
            samples = np.array(audio_data, dtype=np.float32)
            
        # Ensure mono audio (Whisper expects mono)
        if len(samples.shape) > 1:
            samples = samples.mean(axis=1)
        
        # Run transcription in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        
        try:
            if self._use_faster_whisper:
                # faster-whisper implementation
                segments, info = await loop.run_in_executor(
                    None,
                    lambda: self._model.transcribe(
                        samples,
                        language=language or self._language,
                        vad_filter=True,  # Voice activity detection
                        word_timestamps=False
                    )
                )
                text = " ".join(segment.text for segment in segments).strip()
            else:
                # openai-whisper implementation  
                result = await loop.run_in_executor(
                    None,
                    lambda: self._model.transcribe(
                        samples,
                        language=language or self._language
                    )
                )
                text = result["text"].strip()
            
            logger.debug(f"Whisper transcription: '{text}'")
            
            # Return speech event
            return stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[
                    stt.SpeechData(
                        language=language or self._language,
                        text=text,
                        confidence=0.9  # Whisper doesn't provide confidence scores
                    )
                ]
            )
            
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            # Return empty result on error
            return stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[
                    stt.SpeechData(
                        language=language or self._language,
                        text="",
                        confidence=0.0
                    )
                ]
            )

    async def aclose(self):
        """Cleanup resources."""
        # Whisper models don't need explicit cleanup
        self._model = None