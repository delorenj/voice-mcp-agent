#!/usr/bin/env python3
"""
System-wide STT daemon that captures audio and types transcribed text
"""
import asyncio
import logging
import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
import os

# Check if we can import pyautogui safely
PYAUTOGUI_AVAILABLE = False
try:
    # Try to set DISPLAY to a dummy value to avoid X11 connection errors
    if 'DISPLAY' not in os.environ:
        os.environ['DISPLAY'] = ':0'
    
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
    print("✅ pyautogui available for text typing")
except (ImportError, Exception) as e:
    PYAUTOGUI_AVAILABLE = False
    print(f"⚠️  pyautogui not available ({e}). Text will be printed to console instead of typed")
import threading
import queue
import time
from collections import deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemSTTDaemon:
    def __init__(self, model_size="base", sample_rate=16000, chunk_duration=3.0):
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.chunk_samples = int(sample_rate * chunk_duration)
        
        # Audio buffer
        self.audio_buffer = deque(maxlen=self.chunk_samples * 2)
        self.audio_queue = queue.Queue()
        
        # Control flags
        self.recording = False
        self.processing = False
        
        # Disable pyautogui failsafe if available
        if PYAUTOGUI_AVAILABLE:
            pyautogui.FAILSAFE = False
        
    def audio_callback(self, indata, frames, time, status):
        """Callback for audio input"""
        if status:
            logger.warning(f"Audio status: {status}")
        
        # Convert to mono and add to buffer
        audio_data = indata[:, 0] if indata.ndim > 1 else indata
        self.audio_buffer.extend(audio_data)
        
        # If we have enough audio, queue it for processing
        if len(self.audio_buffer) >= self.chunk_samples:
            chunk = np.array(list(self.audio_buffer)[-self.chunk_samples:])
            if not self.audio_queue.full():
                self.audio_queue.put(chunk.copy())
    
    def transcribe_audio(self, audio_chunk):
        """Transcribe audio chunk using Whisper"""
        try:
            segments, info = self.model.transcribe(
                audio_chunk,
                language="en",
                vad_filter=True,
                word_timestamps=False
            )
            
            text = " ".join(segment.text for segment in segments).strip()
            return text
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""
    
    def type_text(self, text):
        """Type transcribed text into active application"""
        if text and len(text.strip()) > 2:  # Only type meaningful text
            logger.info(f"Typing: {text}")
            if PYAUTOGUI_AVAILABLE:
                pyautogui.typewrite(text + " ")
            else:
                print(f"[Transcribed]: {text}")
    
    def process_audio_worker(self):
        """Worker thread for processing audio chunks"""
        while self.processing:
            try:
                # Get audio chunk with timeout
                audio_chunk = self.audio_queue.get(timeout=1.0)
                
                # Transcribe
                text = self.transcribe_audio(audio_chunk)
                
                # Type if we got text
                if text:
                    self.type_text(text)
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Processing error: {e}")
    
    def start(self):
        """Start the STT daemon"""
        logger.info("Starting system STT daemon...")
        logger.info("Press Ctrl+C to stop")
        
        self.recording = True
        self.processing = True
        
        # Start processing thread
        process_thread = threading.Thread(target=self.process_audio_worker, daemon=True)
        process_thread.start()
        
        # Start audio stream
        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            callback=self.audio_callback,
            blocksize=1024,
            dtype=np.float32
        ):
            logger.info("STT daemon running... Speak to transcribe!")
            try:
                while self.recording:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                logger.info("Stopping STT daemon...")
                self.recording = False
                self.processing = False

if __name__ == "__main__":
    daemon = SystemSTTDaemon()
    daemon.start()
