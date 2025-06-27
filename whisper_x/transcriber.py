import whisper
import torch
import os

class Transcriber:
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

    def transcribe(self, audio_path):
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Datei nicht gefunden: {audio_path}")
        print(f"🧠 Transkribiere: {audio_path}")
        result = self.model.transcribe(audio_path, language=self.language)
        return result["text"]

    def get_gpu_usage_text(self):
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1024**2
            reserved = torch.cuda.memory_reserved() / 1024**2
            return f"Belegt: {allocated:.2f} MB\nReserviert: {reserved:.2f} MB"
        else:
            return "Keine GPU verfügbar"
