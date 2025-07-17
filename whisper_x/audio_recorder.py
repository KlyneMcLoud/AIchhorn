import sounddevice as sd
import numpy as np
import tempfile
import scipy.io.wavfile as wav
import threading

class AudioRecorder:
    def __init__(self, sample_rate=16000, channels=1, dtype='int16'):
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self.chunk_duration = 0.2
        self.recording = []
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def record_fixed_duration(self, duration_sec=15):
        self._stop_event.clear()
        self.recording = []
        print(f"🎤 Starte Aufnahme für {duration_sec} Sekunden...")
        data = sd.rec(int(duration_sec * self.sample_rate),
                      samplerate=self.sample_rate,
                      channels=self.channels,
                      dtype=self.dtype)
        sd.wait()
        self.recording.append(data.copy())
        return self._save_to_tempfile()

    def record_until_silence(self, silence_threshold=250, silence_duration=3):
        self._stop_event.clear()
        self.recording = []
        chunk_size = int(self.sample_rate * self.chunk_duration)
        max_silent_chunks = int(silence_duration / self.chunk_duration)
        silent_chunks = 0
        buffer = []

        def callback(indata, frames, time_info, status):
            nonlocal silent_chunks
            if self._stop_event.is_set():
                raise sd.CallbackStop()

            volume = np.abs(indata).mean()
            buffer.append(indata.copy())
            if volume < silence_threshold:
                silent_chunks += 1
            else:
                silent_chunks = 0
            if silent_chunks >= max_silent_chunks:
                print("🤫 Stille erkannt – stoppe...")
                self._stop_event.set() # statt raise sd.CallbackStop()

        print("🎤 Starte Aufnahme bis Stille erkannt oder manuell gestoppt wird...")
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                callback=callback,
                blocksize=chunk_size
            ):
                while not self._stop_event.is_set():
                    sd.sleep(100)
        except Exception as e:
            print("⚠️ Aufnahme abgebrochen:", e)

        self.recording = buffer
        return self._save_to_tempfile()

    def _save_to_tempfile(self):
        if not self.recording:
            raise ValueError("Keine Daten vorhanden")
        audio_data = np.concatenate(self.recording, axis=0)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            wav.write(f.name, self.sample_rate, audio_data)
            print(f"💾 Gespeichert als temporäre Datei: {f.name}")
            return f.name
