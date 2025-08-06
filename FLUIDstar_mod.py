# Verbesserte, modularisierte Version von FLUIDster
# Enthält:
# - Split-Transkription langer Audiodateien
# - Fortschrittsanzeige & Restzeitschätzung
# - Scrollbares Log (max. 3 Zeilen)
# - Modularer Aufbau zur Whisper-Modellwahl

from qtpy.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QTextEdit,
    QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QComboBox,
    QCheckBox, QLineEdit, QStatusBar, QProgressBar
)
from qtpy.QtGui import QIntValidator
from qtpy.QtCore import QTimer, Signal, QObject
import sys
import threading
import time
import os
import re
import platform
import pyperclip
from urllib.parse import urlparse
import urllib.request
from whisper_x.transcriber_module import ModularTranscriber

class Communicator(QObject):
    status_update = Signal(str)
    output_update = Signal(str)
    timer_update = Signal(str)
    progress_update = Signal(int)

class FLUIDster(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FLUIDster Modular")
        self.transcriber = ModularTranscriber()
        self.signals = Communicator()

        # GUI-Komponenten
        self.file_input = QLineEdit()
        self.output_box = QTextEdit()
        self.model_selector = QComboBox()
        self.status_bar = QStatusBar()
        self.timer_label = QLabel("Dauer: 0.0 s")
        self.gpu_label = QLabel("GPU: ...")
        self.progress_bar = QProgressBar()

        self._setup_ui()
        self._connect_signals()
        self._update_gpu_status()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.addRow("Audiodatei/URL:", self.file_input)
        layout.addLayout(form)

        self.model_selector.addItems(["tiny", "base", "small", "medium", "large"])
        form.addRow("Modell:", self.model_selector)

        self.transcribe_btn = QPushButton("Transkribieren")
        layout.addWidget(self.transcribe_btn)

        layout.addWidget(self.progress_bar)
        layout.addWidget(self.output_box)

        self.status_bar.addWidget(self.timer_label)
        self.status_bar.addWidget(self.gpu_label)
        layout.addWidget(self.status_bar)

    def _connect_signals(self):
        self.transcribe_btn.clicked.connect(self._start_transcription)
        self.model_selector.currentTextChanged.connect(self._change_model)
        self.signals.status_update.connect(self._update_status)
        self.signals.output_update.connect(self._append_output)
        self.signals.timer_update.connect(self._update_timer_label)
        self.signals.progress_update.connect(self.progress_bar.setValue)

    def _start_transcription(self):
        threading.Thread(target=self._run_transcription, daemon=True).start()

    def _run_transcription(self):
        path = self.file_input.text().strip()
        if not path:
            return self.signals.status_update.emit("❌ Keine Datei angegeben")

        self.signals.status_update.emit("🔍 Prüfe Datei...")
        try:
            text = self.transcriber.transcribe_adaptive(
                path,
                progress_callback=lambda p: self.signals.progress_update.emit(p),
                status_callback=lambda s: self.signals.status_update.emit(s)
            )
            pyperclip.copy(text)
            self.signals.output_update.emit(text)
            self.signals.status_update.emit("✔ Transkript kopiert")
        except Exception as e:
            self.signals.status_update.emit(f"❌ Fehler: {e}")

    def _change_model(self, model):
        self.signals.status_update.emit(f"📦 Lade Modell {model}...")
        self.transcriber.change_model(model)
        self.signals.status_update.emit(f"✅ Modell '{model}' geladen")

    def _update_timer_label(self, text):
        self.timer_label.setText(text)

    def _update_status(self, text):
        self.status_bar.showMessage(text, 5000)

    def _append_output(self, text):
        lines = self.output_box.toPlainText().splitlines()[-2:]
        lines.append(text)
        self.output_box.setPlainText("\n".join(lines))

    def _update_gpu_status(self):
        try:
            txt = self.transcriber.get_gpu_usage_text()
        except Exception as e:
            txt = f"Fehler: {e}"
        self.gpu_label.setText("GPU: " + txt.replace("\n", " | "))
        QTimer.singleShot(3000, self._update_gpu_status)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = FLUIDster()
    win.show()
    sys.exit(app.exec_())
