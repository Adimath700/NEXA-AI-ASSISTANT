"""
NEXA Voice Engine - reconstructed compatibility module.

This version deliberately avoids PyAudio because newer Python versions
may not have a compatible PyAudio wheel. It uses sounddevice for microphone
capture and SpeechRecognition for speech-to-text, while pyttsx3/SAPI5
handles Windows text-to-speech.
"""

import threading
from datetime import datetime
from io import BytesIO
import wave

import pyttsx3
import sounddevice as sd
import speech_recognition as sr


def get_time() -> str:
    return datetime.now().strftime("%H:%M:%S")


class VoiceEngine:
    def __init__(self, language: str = "en-IN"):
        self.language = language
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 0.8
        self.recognizer.non_speaking_duration = 0.3
        self.recognizer.dynamic_energy_threshold = True

        self.sample_rate = 16000
        self.channels = 1
        self.record_seconds = 5

        self._stop_event = threading.Event()
        self._speak_lock = threading.Lock()

        try:
            self.tts = pyttsx3.init("sapi5")
        except Exception:
            self.tts = pyttsx3.init()

        self.tts.setProperty("rate", 175)
        self.tts.setProperty("volume", 1.0)

    def speak(self, text: str) -> None:
        if not text:
            return

        print(f"NEXA: {text}")

        with self._speak_lock:
            try:
                self.tts.say(str(text))
                self.tts.runAndWait()
            except Exception as exc:
                print(f"[Voice/TTS] {exc}")

    def _record_wav(self) -> bytes:
        """Record microphone audio and return it as WAV bytes."""
        print("Listening...")

        audio = sd.rec(
            int(self.record_seconds * self.sample_rate),
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
        )
        sd.wait()

        buffer = BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)  # int16
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio.tobytes())

        return buffer.getvalue()

    def listen_once(self) -> str:
        try:
            wav_bytes = self._record_wav()

            audio = sr.AudioData(
                wav_bytes,
                self.sample_rate,
                2,
            )

            print("Recognizing...")

            text = self.recognizer.recognize_google(
                audio,
                language=self.language,
            ).strip()

            if text:
                print(f"You: {text}")
                return text.lower()

        except sr.UnknownValueError:
            print("[Voice] I could not understand the audio.")
        except sr.RequestError as exc:
            print(f"[Voice] Speech recognition service error: {exc}")
        except Exception as exc:
            print(f"[Voice] Microphone/recognition error: {exc}")

        return ""

    def listen_continuously(self, callback) -> None:
        while not self._stop_event.is_set():
            command = self.listen_once()

            if command and not self._stop_event.is_set():
                try:
                    callback(command)
                except Exception as exc:
                    print(f"[Voice] Callback error: {exc}")

    def stop(self) -> None:
        self._stop_event.set()
