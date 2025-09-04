#!/usr/bin/env python3
"""
Mac STT - Run this on your Mac, not on big-chungus
"""
import speech_recognition as sr
import pyautogui
import keyboard
import time

def listen_and_type():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎤 Listening... (press space when done)")
        audio = r.listen(source, timeout=10)
    
    try:
        text = r.recognize_whisper(audio)
        print(f"💬 Typing: {text}")
        pyautogui.typewrite(text)
    except:
        print("❌ Could not understand")

print("Press 's' to start recording, Ctrl+C to quit")
keyboard.add_hotkey('s', listen_and_type)
keyboard.wait('ctrl+c')
