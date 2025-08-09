# FLUIDster – Responsive GUI v2 (komplett)
# ===============================================================
# Änderungen gegenüber vorheriger Version
# 1. Alle temporären Dateien werden im projektlokalen Unterordner `tmp/` gespeichert.
# 2. StatusBar‑Layout: ETA (links) + GPU‑Info (rechts) liegen nebeneinander ohne Überlappung.
# 3. Keine Features entfernt – Buttons, Modellwahl, Threads bleiben erhalten.

from __future__ import annotations

import os
import re
import sys
import time
import math
import tempfile
import platform
import urllib.request
from urllib.parse import urlparse
from typing import Optional

from qtpy.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QTextEdit,
    QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QCheckBox, QLineEdit, QStatusBar
)
from qtpy.QtCore import Signal, QObject, QThread
from qtpy.QtGui import QIntValidator

from pydub import AudioSegment
from youtube_transcript_api import YouTubeTranscriptApi

from whisper_x.transcriber import Transcriber  # lokale Klasse
from whisper_x.audio_recorder import AudioRecorder

try:
    import torch
except ImportError:
    torch = None  # type: ignore

if platform.system() == "Windows":
    import winsound

# ---------------------------------------------------------------------------
# Projektpfade & temporäres Verzeichnis
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = os.path.join(BASE_DIR, "tmp")
os.makedirs(TMP_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Utility‑Funktionen
# ---------------------------------------------------------------------------

def split_audio(path: str, max_sec: int = 3600) -> list[str]:
    """Splittet Audiodatei *path* in ≤ *max_sec*-Sekunden-WAV‑Chunks im `tmp/`-Ordner."""
    audio = AudioSegment.from_file(path)
    ms_total = len(audio)
    ms_chunk = max_sec * 1000
    out_paths: list[str] = []
    for start in range(0, ms_total, ms_chunk):
        end = min(start + ms_chunk, ms_total)
        chunk = audio[start:end]
        tmp = tempfile.NamedTemporaryFile(delete=False, dir=TMP_DIR, suffix=".wav")
        chunk.export(tmp.name, format="wav")
        out_paths.append(tmp.name)
    return out_paths


def gpu_summary() -> str:
    if torch is None or not torch.cuda.is_available():
        return "GPU: n/a"
    idx = torch.cuda.current_device()
    props = torch.cuda.get_device_properties(idx)
    total = props.total_memory // (1024**2)
    reserved = torch.cuda.memory_reserved(idx) // (1024**2)
    allocated = torch.cuda.memory_allocated(idx) // (1024**2)
    return f"GPU: {allocated}/{reserved}/{total} MiB"

# ---------------------------------------------------------------------------
# Qt‑Signal‑Bus
# ---------------------------------------------------------------------------

class Bus(QObject):
    status       = Signal(str)
    log          = Signal(str)
    timer        = Signal(str)
    gpu          = Signal(str)
    transcript   = Signal(str)
    record_ready = Signal(str)  # WAV‑Pfad nach Aufnahme fertig

# ---------------------------------------------------------------------------
# Worker‑Threads
# ---------------------------------------------------------------------------

class TranscribeWorker(QThread):
    """Führt lange Transkriptionsaufgaben in eigenem Thread aus."""

    def __init__(self, src: str, out_dir: str, whisper: Transcriber,
                 yt_api: YouTubeTranscriptApi, bus: Bus):
        super().__init__()
        self.src, self.out_dir = src.strip(), out_dir
        self.whisper, self.yt_api, self.bus = whisper, yt_api, bus
        self.max_chunk = 3600  # s

    # --------------- Helper ---------------
    def _emit_gpu(self):
        self.bus.gpu.emit(gpu_summary())

    def _finalize(self, text: str, out_path: str):
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fp:
            fp.write(text)
        self.bus.transcript.emit(text)
        self.bus.status.emit(f"✔ Gespeichert: {out_path}")
        self._emit_gpu()
        if platform.system() == "Windows":
            winsound.MessageBeep()

    # --------------- run ---------------
    def run(self):
        try:
            yt_match = re.match(r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]{11})", self.src)
            if yt_match:
                self._from_youtube(yt_match.group(1))
            else:
                self._from_audio_file()
        except Exception as exc:
            self.bus.status.emit(f"❌ Fehler: {exc}")

    # --------------- YouTube ---------------
    def _from_youtube(self, vid: str):
        self.bus.status.emit("🔄 Lade YouTube‑Transcript…")
        transcript = None
        for langs in (None, ["de"], ["en"]):
            try:
                transcript = (self.yt_api.fetch(vid) if langs is None else self.yt_api.fetch(vid, languages=langs))
                break
            except Exception:
                continue
        if transcript is None:
            raise RuntimeError("Kein Transcript verfügbar")
        text = "\n".join(x.text for x in transcript)
        self._finalize(text, os.path.join(self.out_dir, f"{vid}.md"))

    # --------------- Lokale / entfernte Audiodatei ---------------
    def _from_audio_file(self):
        self.bus.status.emit("🔄 Lade/lese Datei…")
        p = urlparse(self.src)
        local = self.src
        if p.scheme in ("http", "https"):
            local = os.path.join(TMP_DIR, os.path.basename(p.path))
            urllib.request.urlretrieve(self.src, local)
        segments = split_audio(local, self.max_chunk)
        total = len(segments)
        start = time.time()
        parts: list[str] = []
        for idx, seg in enumerate(segments, 1):
            self.bus.log.emit(f"🧠 Segment {idx}/{total}")
            seg_text = self.whisper.transcribe(seg)
            parts.append(seg_text.strip())
            elapsed = time.time() - start
            eta = elapsed / idx * (total - idx)
            self.bus.timer.emit(f"ETA: {eta:.1f}s")
            self._emit_gpu()
        result = "\n".join(parts)
        name = os.path.splitext(os.path.basename(local))[0]
        self._finalize(result, os.path.join(self.out_dir, f"{name}.md"))

class RecordWorker(QThread):
    """Führt Aufnahme in eigenem Thread durch."""
    def __init__(self, recorder: AudioRecorder, auto_stop: bool, duration: int, bus: Bus):
        super().__init__()
        self.recorder, self.auto_stop, self.duration, self.bus = recorder, auto_stop, duration, bus

    def run(self):
        try:
            if self.auto_stop:
                wav = self.recorder.record_until_silence()
            else:
                wav = self.recorder.record_fixed_duration(self.duration)
            self.bus.record_ready.emit(wav)
        except Exception as exc:
            self.bus.status.emit(f"❌ Aufnahme‑Fehler: {exc}")

# ---------------------------------------------------------------------------
# Haupt‑Widget
# ---------------------------------------------------------------------------

class FLUIDster(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FLUIDster")
        self.default_out = os.path.join(BASE_DIR, "_output", "transcripts")
        os.makedirs(self.default_out, exist_ok=True)

        # Kernobjekte
        self.transcriber = Transcriber()
        self.yt_api = YouTubeTranscriptApi()
        self.recorder = AudioRecorder()
        self.bus = Bus()
        self.t_worker: Optional[TranscribeWorker] = None
        self.r_worker: Optional[RecordWorker] = None

        # UI
        self._init_widgets()
        self._build_layout()
        self._connect_signals()
        self._load_model(self.model_sel.currentText())
        self.bus.gpu.emit(gpu_summary())

    # ---------- Widgets ----------
    def _init_widgets(self):
        self.src_edit = QLineEdit(); self.src_edit.setPlaceholderText("URL oder Dateipfad")
        self.out_edit = QLineEdit(self.default_out)
        self.model_sel = QComboBox(); self.model_sel.addItems(["tiny", "base", "small", "medium", "large"])
        self.auto_chk = QCheckBox("Auto‑Stopp bei Stille"); self.auto_chk.setChecked(True)
        self.dur_edit = QLineEdit("15"); self.dur_edit.setValidator(QIntValidator(1, 9999)); self.dur_edit.setFixedWidth(60)
        self.trans_btn = QPushButton("Transkribieren")
        self.rec_btn = QPushButton("Aufnahme starten")
        self.stop_btn = QPushButton("Aufnahme stoppen")
        self.log_box = QTextEdit(); self.log_box.setReadOnly(True); self.log_box.setFixedHeight(60)
        self.text_box = QTextEdit(); self.text_box.setReadOnly(True)
        self.status = QStatusBar(); self.eta_lbl = QLabel("ETA: --"); self.gpu_lbl = QLabel("GPU: --")
        self.status.addWidget(self.eta_lbl)
        self.status.addPermanentWidget(self.gpu_lbl)

    def _build_layout(self):
        v = QVBoxLayout(); form = QFormLayout()
        form.addRow("Quelle:", self.src_edit)
        form.addRow("Ausgabe:", self.out_edit)
        form.addRow("Modell:", self.model_sel)
        rec_row = QHBoxLayout(); rec_row.addWidget(self.auto_chk); rec_row.addWidget(self.dur_edit); rec_row.addWidget(QLabel("s"))
        form.addRow("Aufnahme:", rec_row)
        btn_row = QHBoxLayout(); btn_row.addWidget(self.trans_btn); btn_row.addWidget(self.rec_btn); btn_row.addWidget(self.stop_btn)
        v.addLayout(form); v.addLayout(btn_row)
        v.addWidget(QLabel("Log:")); v.addWidget(self.log_box)
        v.addWidget(QLabel("Transkript:")); v.addWidget(self.text_box)
        v.addWidget(self.status)
        self.setLayout(v)

    # ---------- Signalbindung ----------
    def _connect_signals(self):
        self.trans_btn.clicked.connect(self._start_transcription)
        self.rec_btn.clicked.connect(self._start_recording)
        self.stop_btn.clicked.connect(self.recorder.stop)
        self.model_sel.currentTextChanged.connect(self._load_model)
        # Bus -> UI
        self.bus.status.connect(self.status.showMessage)
        self.bus.log.connect(self._update_log)
        self.bus.timer.connect(self.eta_lbl.setText)
        self.bus.gpu.connect(self.gpu_lbl.setText)
        self.bus.transcript.connect(self.text_box.setPlainText)
        self.bus.record_ready.connect(self._record_finished)

    # ---------- Slots ----------
    def _update_log(self, txt: str):
        self.log_box.append(txt)
        self.log_box.setPlainText("\n".join(self.log_box.toPlainText().splitlines()[-3:]))

    def _load_model(self, name: str):
        self.bus.status.emit(f"⏳ Lade Modell '{name}'…")
        QApplication.processEvents()
        self.transcriber.change_model(name)
        self.bus.status.emit(f"✅ Modell '{name}' bereit")
        self.bus.gpu.emit(gpu_summary())

    # ---------- Actions ----------
    def _start_transcription(self):
        src = self.src_edit.text().strip()
        if not src:
            self.status.showMessage("❌ Quelle fehlt")
            return
        out_dir = self.out_edit.text().strip() or self.default_out
        self.t_worker = TranscribeWorker(src, out_dir, self.transcriber, self.yt_api, self.bus)
        self.t_worker.start()

    def _start_recording(self):
        auto = self.auto_chk.isChecked(); dur = int(self.dur_edit.text() or "15")
        self.r_worker = RecordWorker(self.recorder, auto, dur, self.bus)
        self.r_worker.start()
        self.bus.status.emit("🔴 Aufnahme läuft…")

    def _record_finished(self, wav_path: str):
        self.src_edit.setText(wav_path)
        self.bus.status.emit("🎤 Aufnahme fertig – starte Transkription…")
        self._start_transcription()

# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = FLUIDster()
    w.show()
    sys.exit(app.exec_())
