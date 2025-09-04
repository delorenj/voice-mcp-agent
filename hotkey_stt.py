#!/usr/bin/env python3
"""
Hotkey-activated STT - Press and hold a key to record and transcribe
"""
import asyncio
import logging
import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
import pyautogui
import keyboard
import threading
import time
from collections import deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HotkeySTT:
    def __init__(self, hotkey="ctrl+space", model_size="base", sample_rate=16000):
        self.hotkey = hotkey
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.sample_rate = sample_rate
        
        # Audio recording
        self.recording = False
        self.audio_data = []
        
        # Disable pyautogui failsafe
        pyautogui.FAILSAFE = False
        
    def audio_callback(self, indata, frames, time, status):
        """Callback for audio recording"""
        if self.recording:
            # Convert to mono
            audio_chunk = indata[:, 0] if indata.ndim > 1 else indata
            self.audio_data.extend(audio_chunk)
    
    def start_recording(self):
        """Start recording audio"""
        logger.info("🎤 Recording started...")
        self.recording = True
        self.audio_data = []
    
    def stop_recording(self):
        """Stop recording and transcribe"""
        if not self.recording:
            return
            
        self.recording = False
        logger.info("🛑 Recording stopped, transcribing...")
        
        if len(self.audio_data) < self.sample_rate * 0.5:  # Less than 0.5 seconds
            logger.info("Recording too short, ignoring")
            return
        
        # Convert to numpy array
        audio_array = np.array(self.audio_data, dtype=np.float32)
        
        # Transcribe
        try:
            segments, info = self.model.transcribe(
                audio_array,
                language="en",
                vad_filter=True,
                word_timestamps=False
            )
            
            text = " ".join(segment.text for segment in segments).strip()
            
            if text and len(text.strip()) > 1:
                logger.info(f"💬 Transcribed: {text}")
                pyautogui.typewrite(text)
            else:
                logger.info("No speech detected")
                
        except Exception as e:
            logger.error(f"Transcription error: {e}")
    
    def start(self):
        """Start the hotkey STT system"""
        logger.info(f"Starting hotkey STT with key: {self.hotkey}")
        logger.info("Hold the hotkey and speak, release to transcribe")
        logger.info("Press Ctrl+C to exit")
        
        # Set up hotkey handlers
        keyboard.on_press_key(self.hotkey.split('+')[-1], lambda _: self.start_recording())
        keyboard.on_release_key(self.hotkey.split('+')[-1], lambda _: self.stop_recording())
        
        # Start audio stream
        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            callback=self.audio_callback,
            blocksize=1024,
            dtype=np.float32
        ):
            try:
                keyboard.wait('ctrl+c')
            except KeyboardInterrupt:
                logger.info("Exiting...")

if __name__ == "__main__":
    # Use Ctrl+Space as hotkey (change as needed)
    stt = HotkeySTT(hotkey="space")  # Just space key for simplicity
    stt.start()
