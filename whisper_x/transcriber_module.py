import whisper
import torch
import os
import time
from pydub import AudioSegment

class ModularTranscriber:
    def __init__(self, model_name="base", language="de"):
        self.language = language
        self.model_name = model_name
        self.model_cache = {}
        self.model = self._load_model(model_name)

    def _load_model(self, name):
        if name not in self.model_cache:
            print(f"⏳ Lade Modell: {name}...")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model_cache[name] = whisper.load_model(name, device)
            print(f"✅ Modell '{name}' über {device} geladen.")
        return self.model_cache[name]

    def change_model(self, name):
        if name != self.model_name:
            self.model_name = name
            self.model = self._load_model(name)

    def transcribe_adaptive(self, audio_path, chunk_minutes=30, progress_callback=None, status_callback=None):
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Datei nicht gefunden: {audio_path}")

        audio = AudioSegment.from_file(audio_path)
        duration_ms = len(audio)
        chunk_len = chunk_minutes * 60 * 1000

        if duration_ms <= chunk_len:
            if status_callback:
                status_callback("🔍 Transkribiere gesamte Datei (unter Chunkgröße)...")
            result = self.model.transcribe(audio_path, language=self.language)
            return result["text"]

        chunks = [audio[i:i+chunk_len] for i in range(0, duration_ms, chunk_len)]
        texts = []
        start = time.time()

        for i, chunk in enumerate(chunks):
            temp_file = f"_chunk_{i:03d}.wav"
            chunk.export(temp_file, format="wav")
            if status_callback:
                status_callback(f"🧩 Transkribiere Chunk {i+1}/{len(chunks)}")
            result = self.model.transcribe(temp_file, language=self.language)
            texts.append(f"### Chunk {i+1}\n" + result["text"])
            os.remove(temp_file)

            # Fortschritt berechnen
            if progress_callback:
                progress_callback(int(((i+1)/len(chunks)) * 100))

            # ETA schätzen
            elapsed = time.time() - start
            remaining = (elapsed / (i+1)) * (len(chunks) - (i+1))
            if status_callback:
                status_callback(f"⏱️ Geschätzt verbleibend: {remaining/60:.1f} min")

        return "\n\n".join(texts)

    def get_gpu_usage_text(self):
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1024**2
            reserved = torch.cuda.memory_reserved() / 1024**2
            return f"Belegt: {allocated:.2f} MB\nReserviert: {reserved:.2f} MB"
        else:
            return "Keine GPU verfügbar"
