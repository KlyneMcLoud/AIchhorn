from qtpy.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QTextEdit,
    QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QComboBox,
    QCheckBox, QLineEdit, QStatusBar
)
from qtpy.QtGui import QIntValidator
from qtpy.QtCore import QTimer, Signal, QObject
import sys
import threading
import time
import pyperclip
import keyboard
import platform
import os
import re
from urllib.parse import urlparse
import urllib.request

from whisper_x.transcriber import Transcriber
from whisper_x.audio_recorder import AudioRecorder
from youtube_transcript_api import YouTubeTranscriptApi

# Bei Windows für Signalton
if platform.system() == "Windows":
    import winsound

class Communicator(QObject):
    status_update = Signal(str)
    output_update = Signal(str)
    timer_update = Signal(str)

class FLUIDster(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FLUIDster GUI (Qt Edition)")

        # Default-Projektverzeichnis und Output-Ordner
        script_dir = os.path.dirname(os.path.abspath(__file__))
        default_output = os.path.join(script_dir, "_output", "transcripts")
        os.makedirs(default_output, exist_ok=True)

        # Core-Komponenten
        self.transcriber = Transcriber()
        self.recorder = AudioRecorder()
        self.yt_api = YouTubeTranscriptApi()
        self.signals = Communicator()

        # Widgets
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("z.B. http://... oder C:/Pfad/Datei.mp3")
        self.output_input = QLineEdit(default_output)
        self.output_input.setPlaceholderText(default_output)

        self.model_selector = QComboBox()
        self.model_selector.addItems(["tiny", "base", "small", "medium", "large"])
        self.model_selector.setCurrentText("base")

        self.auto_stop = QCheckBox("Auto-Stopp bei Stille")
        self.auto_stop.setChecked(True)
        self.rec_length = QLineEdit("15")
        self.rec_length.setValidator(QIntValidator(1, 9999))
        self.rec_length.setFixedWidth(50)
        self.rec_length.setEnabled(False)
        self.rec_length_label = QLabel("Sekunden")

        self.transcribe_file_btn = QPushButton("📥 Transkribiere Datei/YouTube")
        self.transcribe_file_btn.setToolTip("Lädt und transkribiert Datei oder YouTube-Video")
        self.record_btn = QPushButton("🎤 Aufnahme starten")
        self.record_btn.setToolTip("Startet Aufnahme (Hotkey Strg+Shift+C)")
        self.stop_btn = QPushButton("🛑 Aufnahme stoppen")
        self.stop_btn.setToolTip("Stoppt Aufnahme manuell")

        self.status_bar = QStatusBar()
        self.timer_label = QLabel("Dauer: 0.0 s")
        self.gpu_label = QLabel("GPU: ...")
        self.status_bar.addWidget(self.timer_label)
        self.status_bar.addWidget(self.gpu_label)

        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)

        # Signals verbinden
        self._connect_signals()

        # Layouts
        self._build_interface()
        self._update_gpu_status()
        self._setup_global_hotkey()

    def _connect_signals(self):
        sig = self.signals
        sig.status_update.connect(self._update_status)
        sig.output_update.connect(self.output_box.setPlainText)
        sig.timer_update.connect(self._update_timer_label)
        self.model_selector.currentTextChanged.connect(self._on_model_change)
        self.auto_stop.stateChanged.connect(self._toggle_rec_length)
        self.transcribe_file_btn.clicked.connect(self._transcribe_file_thread)
        self.record_btn.clicked.connect(self._start_recording_thread)
        self.stop_btn.clicked.connect(self._stop_recording)

    def _build_interface(self):
        main_layout = QVBoxLayout(self)

        # Quelle & Ziel
        form = QFormLayout()
        form.addRow(QLabel("Quelle (Datei/URL/YouTube):"), self.file_input)
        form.addRow(QLabel("Zielordner für Transkripte:"), self.output_input)
        main_layout.addLayout(form)

        # Modell & Aufnahme Einstellungen
        settings_group = QGroupBox("Einstellungen")
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(QLabel("Whisper-Modell:")); settings_layout.addWidget(self.model_selector)
        settings_layout.addStretch(1)
        settings_layout.addWidget(self.auto_stop)
        settings_layout.addWidget(self.rec_length); settings_layout.addWidget(self.rec_length_label)
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        # Aktionen
        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.transcribe_file_btn)
        actions_layout.addWidget(self.record_btn)
        actions_layout.addWidget(self.stop_btn)
        actions_layout.addStretch(1)
        main_layout.addLayout(actions_layout)

        # Status & Ausgabe
        main_layout.addWidget(self.status_bar)
        main_layout.addWidget(self.output_box)
        self.setLayout(main_layout)

    def _setup_global_hotkey(self):
        try:
            keyboard.add_hotkey("ctrl+shift+c", self._start_recording_thread)
        except Exception as e:
            print(f"⚠️ Hotkey konnte nicht registriert werden: {e}")

    def _start_recording_thread(self):
        threading.Thread(target=self._record_and_transcribe, daemon=True).start()

    def _record_and_transcribe(self):
        start = time.time()
        def update_timer():
            while not self.recorder._stop_event.is_set():
                self.signals.timer_update.emit(f"Dauer: {time.time()-start:.1f} s")
                time.sleep(0.2)
        threading.Thread(target=update_timer, daemon=True).start()
        self.signals.status_update.emit("🎙️ Aufnahme läuft...")
        try:
            path = (self.recorder.record_until_silence()
                    if self.auto_stop.isChecked()
                    else self.recorder.record_fixed_duration(int(self.rec_length.text())))
            self.signals.status_update.emit("🧠 Transkribiere...")
            text = self.transcriber.transcribe(path)
            pyperclip.copy(text)
            self.signals.output_update.emit(text)
            self.signals.status_update.emit("✔ Fertig")
        except Exception as e:
            self.signals.status_update.emit(f"❌ Fehler: {e}")

    def _stop_recording(self):
        self.recorder.stop()
        self.signals.status_update.emit("🛑 Aufnahme gestoppt")

    def _on_model_change(self, name):
        self.signals.status_update.emit(f"📦 Lade Modell {name}...")
        QApplication.processEvents()
        self.transcriber.change_model(name)
        self.signals.status_update.emit(f"✅ Modell '{name}' geladen")

    def _toggle_rec_length(self):
        self.rec_length.setEnabled(not self.auto_stop.isChecked())

    def _update_timer_label(self, text):
        self.timer_label.setText(text)

    def _update_status(self, text):
        self.status_bar.showMessage(text, 5000)

    def _beep(self, freq=700, dur=100):
        if platform.system() == "Windows":
            try: winsound.Beep(freq, dur)
            except: pass

    def _update_gpu_status(self):
        try: txt = self.transcriber.get_gpu_usage_text()
        except Exception as e: txt = f"Fehler: {e}"
        self.gpu_label.setText("GPU: " + txt.replace("\n"," | "))
        QTimer.singleShot(3000, self._update_gpu_status)

    def _transcribe_file_thread(self):
        threading.Thread(target=self._transcribe_file, daemon=True).start()

    def _transcribe_file(self):
        src = self.file_input.text().strip()
        if not src:
            return self.signals.status_update.emit("❌ Bitte Quelle eingeben")
        out_dir = self.output_input.text().strip() or os.path.join(os.path.dirname(__file__), "_output", "transcripts")
        os.makedirs(out_dir, exist_ok=True)
        yt = re.match(r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]{11})", src)
        try:
            if yt:
                vid = yt.group(1)
                self.signals.status_update.emit("🔄 Lade YouTube-Transcript...")
                fetched = self.yt_api.fetch(vid)
                text = "\n".join(s.text for s in fetched)
                path = os.path.join(out_dir, f"{vid}.md")
            else:
                self.signals.status_update.emit("🔄 Lade/lese Datei...")
                p = urlparse(src)
                local = src if p.scheme not in ('http','https') else os.path.join('tmp/', os.path.basename(p.path))
                if p.scheme in ('http','https'): urllib.request.urlretrieve(src, local)
                text = self.transcriber.transcribe(local)
                fname = os.path.splitext(os.path.basename(local))[0]
                path = os.path.join(out_dir, f"{fname}.md")
            with open(path, 'w', encoding='utf-8') as f: f.write(text)
            self.signals.output_update.emit(text)
            self.signals.status_update.emit(f"✔ Gespeichert: {path}")
        except Exception as e:
            self.signals.status_update.emit(f"❌ Fehler: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FLUIDster()
    window.show()
    sys.exit(app.exec_())
