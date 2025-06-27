from qtpy.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QTextEdit,
    QVBoxLayout, QHBoxLayout, QComboBox, QCheckBox, QLineEdit
)
from qtpy.QtCore import QTimer, Signal, QObject
from qtpy.QtGui import QIntValidator
import sys
import threading
from whisper_x.transcriber import Transcriber
from whisper_x.audio_recorder import AudioRecorder
import time

class Communicator(QObject):
    status_update = Signal(str)
    output_update = Signal(str)
    timer_update = Signal(str)

class FLUIDster(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FLUIDster GUI (Qt Edition)")

        self.transcriber = Transcriber()
        self.recorder = AudioRecorder()

        self.signals = Communicator()
        self.signals.status_update.connect(self._update_status)
        self.signals.output_update.connect(self.output_box_set_text)

        self.auto_stop = QCheckBox("Stille -> Auto-Stopp")
        self.auto_stop.setChecked(True)
        self.auto_stop.stateChanged.connect(self._toggle_rec_length)

        self.rec_length = QLineEdit("15")
        self.rec_length.setMaxLength(4)
        self.rec_length.setValidator(QIntValidator(1, 9999))
        self.rec_length.setPlaceholderText("Sek.")
        self.rec_length.setFixedWidth(50)
        self.rec_length.setEnabled(False)

        self.model_selector = QComboBox()
        self.model_selector.addItems(["tiny", "base", "small", "medium", "large"])
        self.model_selector.setCurrentText("base")
        self.model_selector.currentTextChanged.connect(self._on_model_change)

        self.status_label = QLabel("Bereit")
        self.gpu_label = QLabel("GPU: wird geladen...")
        self.output_box = QTextEdit()
        self.output_box.setReadOnly(True)

        self.record_btn = QPushButton("🎤 Aufnahme starten")
        self.record_btn.clicked.connect(self._start_recording_thread)

        self.stop_btn = QPushButton("🛑 Aufnahme stoppen")
        self.stop_btn.clicked.connect(self._stop_recording)

        self.timer_label = QLabel("Dauer: 0.0 s")
        self.signals.timer_update.connect(self._update_timer_label)

        self._build_interface()
        self._update_gpu_status()

    def _build_interface(self):
        layout = QVBoxLayout()

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Whisper-Modell:"))
        row1.addWidget(self.model_selector)

        row2 = QHBoxLayout()
        row2.addWidget(self.auto_stop)
        row2.addWidget(QLabel("...oder"))
        row2.addWidget(self.rec_length)
        row2.addWidget(QLabel("s"))        

        row3 = QHBoxLayout()
        row3.addWidget(self.record_btn)
        row3.addWidget(self.stop_btn)

        layout.addLayout(row1)
        layout.addLayout(row2)
        layout.addLayout(row3)
        layout.addWidget(self.status_label)
        layout.addWidget(self.timer_label)
        layout.addWidget(self.gpu_label)
        layout.addWidget(self.output_box)

        self.setLayout(layout)

    def _update_timer_label(self, text):
        self.timer_label.setText(text)

    def _toggle_rec_length(self):
        self.rec_length.setEnabled(not self.auto_stop.isChecked())

    def _on_model_change(self, name):
        self.status_label.setText(f"📦 Lade Modell: {name}...")
        QApplication.processEvents()
        self.transcriber.change_model(name)
        self.status_label.setText(f"✅ Modell '{name}' geladen")

    def _start_recording_thread(self):
        threading.Thread(target=self._record_and_transcribe, daemon=True).start()


    def _record_and_transcribe(self):
        start_time = time.time()
        def update_timer():
            while not self.recorder._stop_event.is_set():
                elapsed = time.time() - start_time
                self.signals.timer_update.emit(f"Dauer: {elapsed:.1f} s")
                time.sleep(0.2)

        timer_thread = threading.Thread(target=update_timer, daemon=True)
        timer_thread.start()
        self.signals.status_update.emit("🎙️ Aufnahme läuft...")


        try:
            if self.auto_stop.isChecked():
                path = self.recorder.record_until_silence()
            else:
                max_rec = int(self.rec_length.text() or "15")
                path = self.recorder.record_fixed_duration(max_rec)
            self.signals.status_update.emit("🧠 Transkribiere...")
            text = self.transcriber.transcribe(path)
            self.signals.status_update.emit("✔ Transkribiert")
            self.signals.output_update.emit(text)
        except Exception as e:
            self.signals.status_update.emit(f"❌ Fehler: {str(e)}")

    def _stop_recording(self):
        self.recorder.stop()
        self.status_label.setText("🛑 Aufnahme wird gestoppt...")

    def _update_gpu_status(self):
        self.gpu_label.setText("GPU: " + self.transcriber.get_gpu_usage_text().replace("\n", " | "))
        QTimer.singleShot(3000, self._update_gpu_status)

    def _update_status(self, text):
        self.status_label.setText(text)

    def output_box_set_text(self, text):
        self.output_box.setPlainText(text)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FLUIDster()
    window.show()
    sys.exit(app.exec_())
